"""Run Playwright tests and turn the JSON report into what an AI needs to diagnose a failure."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .project import Project, ProjectError

ANSI = re.compile(r"\x1b\[[0-9;]*m")
FRAME = re.compile(r"\(?((?:[A-Za-z]:)?[^\s()]+\.[cm]?[jt]s):(\d+):(\d+)\)?")
PAGE_MEMBER = re.compile(r"\b([a-z]\w*Page)\.(\w+)\b")
MAX_ERROR = 2500
MAX_SNAPSHOT = 6000


@dataclass
class TestOutcome:
    title: str
    file: str
    line: int
    status: str  # passed | failed | timedOut | skipped | flaky | interrupted
    duration_ms: int = 0
    error: str = ""
    error_file: str = ""
    error_line: int = 0
    frames: list[tuple[str, int]] = field(default_factory=list)
    error_context: str = ""
    screenshot: str = ""
    note: str = ""  # skip/fixme reason

    @property
    def id(self) -> str:
        return f"{self.file}:{self.line}"

    @property
    def failed(self) -> bool:
        return self.status in {"failed", "timedOut", "interrupted"}


def clean(text: str) -> str:
    return ANSI.sub("", text or "").strip()


# ------------------------------------------------------------- running

def run_tests(project: Project, spec: str = "", grep: str = "", headed: bool = False,
              timeout: int = 900) -> list[TestOutcome]:
    problems = project.setup_problems()
    if problems:
        raise ProjectError(" ".join(problems))
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise ProjectError("Node.js isn't installed or npx isn't on the PATH.")
    if spec:
        project.path(spec)  # validates the path
    report = project.state_dir / "last-run.json"
    report.unlink(missing_ok=True)
    cmd = [npx, "playwright", "test", *([spec] if spec else []), "--reporter=json"]
    if grep:
        cmd += ["-g", grep]
    if headed:
        cmd.append("--headed")
    env = {**os.environ, "PLAYWRIGHT_JSON_OUTPUT_FILE": str(report), "PLAYWRIGHT_JSON_OUTPUT_NAME": str(report),
           "FORCE_COLOR": "0"}
    try:
        proc = subprocess.run(cmd, cwd=project.root, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ProjectError(f"The test run took longer than {timeout} s and was stopped.")
    if not report.exists():
        out = clean(proc.stdout + proc.stderr)
        raise ProjectError(f"Playwright didn't produce a report. Output:\n{out[-3000:]}")
    outcomes = parse_report(project, json.loads(report.read_text(encoding="utf-8")))
    if not outcomes:
        errors = json.loads(report.read_text(encoding="utf-8")).get("errors") or []
        msg = "; ".join(clean(e.get("message", "")) for e in errors)[:2000]
        raise ProjectError(f"No tests ran. {msg or 'Check the spec path or the -g filter.'}")
    (project.state_dir / "last-outcomes.json").write_text(json.dumps([asdict(o) for o in outcomes], indent=1))
    return outcomes


def last_outcomes(project: Project) -> list[TestOutcome]:
    f = project.root / ".pwmcp" / "last-outcomes.json"
    if not f.exists():
        raise ProjectError("No test run yet: call run_tests first.")
    return [TestOutcome(**{**o, "frames": [tuple(x) for x in o["frames"]]}) for o in json.loads(f.read_text())]


def parse_report(project: Project, report: dict) -> list[TestOutcome]:
    test_dir = Path(report.get("config", {}).get("rootDir") or project.root / "tests")
    out: list[TestOutcome] = []

    def walk(suite: dict, path: list[str]):
        title = suite.get("title", "")
        here = path + [title] if title and not title.endswith((".js", ".ts")) else path
        for spec in suite.get("specs", []):
            for t in spec.get("tests", []):
                out.append(_outcome(project, test_dir, here + [spec["title"]], spec, t))
        for child in suite.get("suites", []):
            walk(child, here)

    for s in report.get("suites", []):
        walk(s, [])
    return out


def _outcome(project, test_dir, titles, spec, t) -> TestOutcome:
    results = t.get("results") or [{}]
    r = results[-1]
    status = r.get("status", "skipped")
    if t.get("status") == "flaky":
        status = "flaky"
    file = project.rel(test_dir / spec["file"])
    o = TestOutcome(title=" › ".join(titles), file=file, line=spec.get("line", 0), status=status,
                    duration_ms=int(r.get("duration", 0)))
    notes = [a.get("description", "") for a in t.get("annotations", []) if a.get("type") in {"skip", "fixme"}]
    o.note = "; ".join(n for n in notes if n)
    if status in {"failed", "timedOut", "interrupted"}:
        errs = r.get("errors") or ([r["error"]] if r.get("error") else [])
        o.error = clean("\n\n".join(e.get("message", "") for e in errs))[:MAX_ERROR]
        stack = "\n".join(clean(e.get("stack", "") + "\n" + e.get("message", "")) for e in errs)
        o.frames = _project_frames(project, stack)
        loc = next((e["location"] for e in [r.get("error") or {}, *errs] if e.get("location")), {})
        if loc.get("file"):
            o.error_file, o.error_line = project.rel(loc["file"]), loc.get("line", 0)
        elif o.frames:
            o.error_file, o.error_line = o.frames[0]
        for a in r.get("attachments", []):
            if a.get("name") == "error-context" and a.get("path"):
                o.error_context = a["path"]
            elif a.get("name") == "screenshot" and a.get("path") and not o.screenshot:
                o.screenshot = project.rel(a["path"])
    return o


def _project_frames(project: Project, stack: str) -> list[tuple[str, int]]:
    frames = []
    for m in FRAME.finditer(stack):
        p = Path(m.group(1))
        if not p.is_absolute():
            p = project.root / p
        try:
            rel = p.resolve().relative_to(project.root).as_posix()
        except ValueError:
            continue
        if "node_modules" in rel:
            continue
        item = (rel, int(m.group(2)))
        if item not in frames:
            frames.append(item)
    return frames


# ------------------------------------------------------------- summaries for the AI

def summarize(outcomes: list[TestOutcome]) -> str:
    counts: dict[str, int] = {}
    for o in outcomes:
        counts[o.status] = counts.get(o.status, 0) + 1
    head = ", ".join(f"{n} {s}" for s, n in sorted(counts.items()))
    lines = [f"{len(outcomes)} tests: {head}"]
    for o in outcomes:
        mark = {"passed": "PASS", "skipped": "SKIP", "flaky": "FLAKY"}.get(o.status, "FAIL")
        line = f"[{mark}] {o.title}  ({o.id})"
        if o.failed:
            first = o.error.splitlines()[0] if o.error else o.status
            line += f"\n       {first}"
        elif o.note:
            line += f"  - {o.note}"
        lines.append(line)
    if any(o.failed for o in outcomes):
        lines.append("\nCall get_failure_details with a test title (e.g. its TC id) to see why one failed.")
    return "\n".join(lines)


def find_outcome(outcomes: list[TestOutcome], test: str) -> TestOutcome:
    failed = [o for o in outcomes if o.failed]
    if not test:
        if not failed:
            raise ProjectError("No failing tests in the last run.")
        return failed[0]
    for pool in (failed, outcomes):
        for o in pool:
            if test == o.id or test.lower() in o.title.lower():
                return o
    raise ProjectError(f"No test matching {test!r} in the last run.")


def failure_details(project: Project, o: TestOutcome) -> str:
    if not o.failed:
        return f"{o.title} did not fail (status: {o.status}{', ' + o.note if o.note else ''})."
    parts = [f"TEST: {o.title}", f"SPEC: {o.id}", f"STATUS: {o.status}", "", "ERROR:", o.error]

    spec_frame = next(((f, n) for f, n in o.frames if f == o.file), None) or (
        (o.error_file, o.error_line) if o.error_file == o.file else None)
    if spec_frame:
        f, n = spec_frame
        parts += ["", f"FAILING STEP in {f} (line {n} marked >>):", _excerpt(project, f, n, before=14, after=4)]
        code = _lines(project, f, n - 1, n)
        used = []
        for fixture, name in PAGE_MEMBER.findall(code):
            e = project.element(fixture, name)
            if e and e not in used:
                used.append(e)
        if used:
            parts += ["", "PAGE OBJECT ELEMENTS ON THOSE LINES (locators come from the object repository):"]
            parts += [f"- {fixture_use(e)} -> {_locator(e)}  [{e['file']}]" for e in used]
    other = [(f, n) for f, n in o.frames if f != o.file]
    if other:
        f, n = other[0]
        parts += ["", f"ALSO IN THE STACK: {f} line {n}:", _excerpt(project, f, n, before=3, after=2)]

    snap = page_snapshot(o.error_context)
    if snap:
        parts += ["", "PAGE AT THE MOMENT OF FAILURE (accessibility snapshot):", snap]
    hints = diagnose(o.error, snap)
    if hints:
        parts += ["", "HINTS:"] + [f"- {h}" for h in hints]
    if o.screenshot:
        parts += ["", f"Screenshot: {o.screenshot}"]
    return "\n".join(parts)


def fixture_use(e: dict) -> str:
    return f"{e['page'][:1].lower()}{e['page'][1:]}.{e['name']}"


def _locator(e: dict) -> str:
    s, v = e.get("strategy"), e.get("value", "")
    return {
        "testId": f"getByTestId('{v}')", "label": f"getByLabel('{v}')", "placeholder": f"getByPlaceholder('{v}')",
        "text": f"getByText('{v}')", "role": f"getByRole('{e.get('role', '')}', {{ name: '{v}' }})",
    }.get(s, f"locator('{v}')")


def _lines(project: Project, rel: str, start: int, end: int) -> str:
    try:
        lines = project.path(rel).read_text(encoding="utf-8").splitlines()
    except ProjectError:
        return ""
    return "\n".join(lines[max(0, start - 1):end])


def _excerpt(project: Project, rel: str, line: int, before: int, after: int) -> str:
    try:
        lines = project.path(rel).read_text(encoding="utf-8").splitlines()
    except ProjectError:
        return "(source not available)"
    lo, hi = max(1, line - before), min(len(lines), line + after)
    return "\n".join(f"{'>>' if i == line else '  '} {i:>4}  {lines[i - 1]}" for i in range(lo, hi + 1))


def page_snapshot(error_context: str) -> str:
    if not error_context or not Path(error_context).exists():
        return ""
    text = Path(error_context).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"#\s*Page snapshot\s*\n+```(?:yaml)?\n(.*?)```", text, re.S)
    snap = (m.group(1) if m else "").strip()
    if len(snap) > MAX_SNAPSHOT:
        snap = snap[:MAX_SNAPSHOT] + "\n… (truncated)"
    return snap


def diagnose(error: str, snapshot: str) -> list[str]:
    e, s = error.lower(), snapshot.lower()
    hints = []
    if "no login credentials" in e or "cannot find module 'dotenv'" in e:
        hints.append("Project setup problem, not a test bug: run `npm install` and create .env from .env.example.")
    if "executable doesn't exist" in e or "npx playwright install" in e:
        hints.append("Playwright's browser isn't installed: run `npx playwright install chromium` in the project.")
    if "didn't succeed: still on the login page" in e:
        hints.append("The app rejected the login. Check APP_USERNAME / APP_PASSWORD in .env (don't change the code).")
    if "strict mode violation" in e:
        m = re.search(r"resolved to (\d+) elements", error)
        n = m.group(1) if m else "several"
        hints.append(
            f"The locator matches {n} elements. Either the browser is still on a previous page (add "
            "`await <page>.waitForPage()` before the step) or the locator needs to be more specific."
        )
    waiting = re.search(r"waiting for (get\w+\(.*?\)|locator\(.*?\))", error)
    if waiting and ("timeout" in e or "not found" in e):
        hints.append(
            f"{waiting.group(1)} never appeared. Compare it with the page snapshot: if the element is there "
            "under another name/test id, fix the locator in the object repository JSON; if the page is a "
            "different one, a previous step went wrong. Call inspect_page to list the page's real locators."
        )
    if s and ('textbox "username"' in s or 'textbox "password"' in s) and "login" in s and "login" not in e:
        hints.append("The browser is on the login page at the moment of failure: the login probably didn't happen.")
    if "toHaveURL".lower() in e:
        hints.append("The URL assertion failed: check which page the previous step really leads to.")
    if "expected substring" in e or "expected string" in e:
        hints.append("The element exists but its text differs: check the expected value in test-data/TestData.xlsx.")
    return hints
