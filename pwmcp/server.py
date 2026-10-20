"""MCP server: lets the AI in your IDE run Playwright tests, diagnose failures and fix the code,
writing a change only after you approve it.

Run with:  python -m pwmcp.server        (stdio; the IDE starts it)
Project:   PW_PROJECT_DIR=/path/to/playwright-project  (or start it in that folder)
"""

from __future__ import annotations

import asyncio

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import fixes, inspector, runner
from .project import Project, ProjectError

INSTRUCTIONS = """\
Tools for a Playwright (JavaScript) Page Object Model project: tests in tests/*.spec.js, page
classes in pages/, locators in object-repository/<Page>.json, test data in test-data/TestData.xlsx.

To fix a failing test:
1. run_tests (optionally one spec file or a -g filter), then get_failure_details for the failing test.
2. Find the root cause. Use inspect_page to see the real locators on a page and find_elements to
   reuse existing page objects. Prefer fixing a wrong locator in object-repository/<Page>.json (one
   place) over editing specs. Setup problems (npm install, .env) are fixed by the user, not in code.
3. propose_fix with the smallest change. It does NOT write anything: show the user the diff and the
   reason, and ask whether to apply it.
4. Call apply_fix ONLY after the user explicitly says yes to that fix. Never apply a fix the user has
   not approved. Then run_tests again to confirm, and offer undo_fix if it made things worse.
Never read or print the .env file or credentials.
"""

mcp = MCPServer(name="playwright-fixer", title="Playwright Test Fixer", instructions=INSTRUCTIONS, version="1.0.0")

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def _project(project_dir: str) -> Project:
    try:
        return Project.locate(project_dir)
    except ProjectError as e:
        raise ToolError(str(e)) from e


async def _call(fn, *args, **kw):
    """Run blocking work in a thread; turn user-fixable problems into readable tool errors."""
    try:
        return await asyncio.to_thread(fn, *args, **kw)
    except ProjectError as e:
        raise ToolError(str(e)) from e


# ------------------------------------------------------------- tests

@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True))
async def run_tests(spec: str = "", grep: str = "", project_dir: str = "") -> str:
    """Run the Playwright tests and summarize the result.

    spec: one spec file, e.g. "tests/FR-01.spec.js" (empty = all). grep: only tests whose title
    matches, e.g. "TC-004". Returns pass/fail per test with the first line of each error.
    """
    p = _project(project_dir)
    outcomes = await _call(runner.run_tests, p, spec, grep)
    return runner.summarize(outcomes)


@mcp.tool(annotations=READ)
async def get_failure_details(test: str = "", project_dir: str = "") -> str:
    """Why a test failed in the last run: error, the failing spec lines, the page-object locators on
    those lines, the page's accessibility snapshot at the moment of failure, and hints.

    test: part of the test title (e.g. "TC-004") or "file:line"; empty = first failing test.
    """
    p = _project(project_dir)

    def work():
        return runner.failure_details(p, runner.find_outcome(runner.last_outcomes(p), test))

    return await _call(work)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True))
async def inspect_page(url_path: str = "/", login: bool = True, project_dir: str = "") -> str:
    """Open a page of the app in a headless browser (logging in first with the project's LoginPage
    and .env) and list its elements with working locators and whether each is unique.

    url_path: path relative to BASE_URL, e.g. "/cart.html".
    """
    p = _project(project_dir)
    return await _call(inspector.inspect_page, p, url_path, login)


# ------------------------------------------------------------- reading the project

@mcp.tool(annotations=READ)
async def find_elements(query: str, page: str = "", project_dir: str = "") -> str:
    """Search the object repository for existing page-object elements, e.g. "cart button" ->
    commonPage.shoppingCartLink. Use these instead of writing raw locators in specs."""
    p = _project(project_dir)
    hits = await _call(p.find_elements, query, page)
    if not hits:
        return f"No element matches {query!r}. Use inspect_page to see the live page."
    return "\n".join(
        f"- {h['use']}: {h.get('strategy')}={h.get('value')!r} ({h.get('kind')}, {h.get('description', '')}) [{h['file']}]"
        for h in hits
    )


@mcp.tool(annotations=READ)
async def read_file(path: str, start_line: int = 1, end_line: int = 0, project_dir: str = "") -> str:
    """Read a project file with line numbers (specs, pages, object-repository JSON, config).
    Leave out the line numbers when copying text into propose_fix."""
    p = _project(project_dir)
    return await _call(p.read, path, start_line, end_line)


@mcp.tool(annotations=READ)
async def list_project_files(project_dir: str = "") -> str:
    """List the project's files (without node_modules, reports and .env)."""
    p = _project(project_dir)
    files = await _call(p.list_files)
    problems = p.setup_problems()
    return "\n".join(files + ([""] + [f"Setup: {x}" for x in problems] if problems else []))


# ------------------------------------------------------------- fixing (human in the loop)

@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False))
async def propose_fix(file: str, old_text: str, new_text: str, reason: str, project_dir: str = "") -> str:
    """Prepare a code change WITHOUT writing it. Replaces old_text (copied exactly from the file,
    occurring once) with new_text. Checks JSON/JavaScript syntax. Returns a fix id and a diff:
    show both to the user and ask for approval before calling apply_fix."""
    p = _project(project_dir)
    fx = await _call(fixes.propose_fix, p, file, old_text, new_text, reason)
    return (
        f"Proposed fix {fx['id']} for {fx['file']} (nothing written yet).\n"
        f"Reason: {fx['reason']}\n\n```diff\n{fx['diff']}```\n\n"
        f"Ask the user to approve. Only after they say yes, call apply_fix with fix_id=\"{fx['id']}\"."
    )


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False,
                                      open_world_hint=False))
async def apply_fix(fix_id: str, project_dir: str = "") -> str:
    """Write a proposed fix to the file. ONLY call this after the user explicitly approved this
    fix id. The original is backed up (undo_fix restores it)."""
    p = _project(project_dir)
    fx = await _call(fixes.apply_fix, p, fix_id)
    return (f"Applied fix {fx['id']} to {fx['file']}. The IDE shows the change. "
            f"Run the test again to confirm; undo_fix(\"{fx['id']}\") reverts it.")


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False))
async def undo_fix(fix_id: str, project_dir: str = "") -> str:
    """Restore the file as it was before an applied fix."""
    p = _project(project_dir)
    fx = await _call(fixes.undo_fix, p, fix_id)
    return f"Undid fix {fx['id']}: {fx['file']} is back to its previous content."


@mcp.tool(annotations=READ)
async def list_fixes(project_dir: str = "") -> str:
    """Fixes proposed in this project and their status (pending / applied / undone)."""
    p = _project(project_dir)
    items = await _call(fixes.list_fixes, p)
    return "\n".join(f"- {f['id']} [{f['status']}] {f['file']}: {f['reason']}" for f in items) or "No fixes yet."


# ------------------------------------------------------------- prompt (slash command in the IDE)

@mcp.prompt(title="Fix a failing Playwright test")
def fix_failing_test(test: str = "") -> str:
    """Guided workflow: run, diagnose, propose a fix, apply after approval, re-run."""
    target = f'the test "{test}"' if test else "the failing tests"
    return (
        f"Fix {target} in my Playwright project using the playwright-fixer tools. "
        f"First run_tests{' with grep=' + repr(test) if test else ''}, then get_failure_details. "
        "Explain the root cause in two or three sentences. If it's a code problem, propose_fix the smallest "
        "change (prefer the object repository JSON for locators) and show me the diff. Wait for my approval "
        "before apply_fix, then run the test again and tell me the result."
    )


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
