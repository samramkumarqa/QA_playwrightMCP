"""End to end over real MCP (stdio), the way IntelliJ's AI plugin talks to the server:
a test fails because of a wrong locator -> diagnose -> inspect the page -> propose -> apply -> green."""

import asyncio
import os
import sys

from conftest import ROOT, needs_node
from mcp import Client
from mcp.client.stdio import StdioServerParameters


def _server(project_dir):
    return StdioServerParameters(command=sys.executable, args=["-m", "pwmcp.server"], cwd=str(ROOT),
                                 env={"PW_PROJECT_DIR": str(project_dir),
                                      **{k: v for k, v in os.environ.items() if k.startswith("PLAYWRIGHT_")}})


def _text(result) -> str:
    return "\n".join(getattr(c, "text", "") for c in result.content)


async def _call(client, name, **args):
    r = await client.call_tool(name, args, read_timeout_seconds=600)
    return r.is_error if hasattr(r, "is_error") else r.isError, _text(r)


def test_server_lists_tools_and_prompt(bare_project):
    async def go():
        async with Client(_server(bare_project)) as c:
            tools = {t.name: t for t in (await c.list_tools()).tools}
            prompts = [p.name for p in (await c.list_prompts()).prompts]
            err, text = await _call(c, "run_tests")  # downloaded project: not installed, no .env
            return tools, prompts, err, text

    tools, prompts, err, text = asyncio.run(go())
    assert set(tools) == {"run_tests", "get_failure_details", "inspect_page", "find_elements", "read_file",
                          "list_project_files", "propose_fix", "apply_fix", "undo_fix", "list_fixes"}
    assert tools["apply_fix"].annotations.destructive_hint is True
    assert tools["get_failure_details"].annotations.read_only_hint is True
    assert prompts == ["fix_failing_test"]
    assert err and "npm install" in text and "cp .env.example .env" in text


@needs_node
def test_fix_a_broken_locator_end_to_end(project_dir):
    repo = project_dir / "object-repository" / "CartPage.json"
    repo.write_text(repo.read_text().replace('"value": "checkout"', '"value": "checkout-btn"'))

    async def go():
        log = {}
        async with Client(_server(project_dir)) as c:
            log["run1"] = await _call(c, "run_tests", grep="TC-004")
            log["details"] = await _call(c, "get_failure_details", test="TC-004")
            log["inspect"] = await _call(c, "inspect_page", url_path="/cart.html")
            log["found"] = await _call(c, "find_elements", query="checkout button")
            log["propose"] = await _call(
                c, "propose_fix", file="object-repository/CartPage.json",
                old_text='"value": "checkout-btn"', new_text='"value": "checkout"',
                reason="The Checkout button's test id is 'checkout', not 'checkout-btn'.")
            log["untouched"] = repo.read_text()
            fix_id = log["propose"][1].split("Proposed fix ")[1].split()[0]
            log["apply"] = await _call(c, "apply_fix", fix_id=fix_id)
            log["run2"] = await _call(c, "run_tests", grep="TC-004")
            log["fixes"] = await _call(c, "list_fixes")
        return log

    log = asyncio.run(go())
    err, run1 = log["run1"]
    assert not err and "[FAIL] FR-03 › TC-004" in run1
    details = log["details"][1]
    assert "waiting for getByTestId('checkout-btn')" in details
    assert "cartPage.checkoutButton -> getByTestId('checkout-btn')  [object-repository/CartPage.json]" in details
    assert 'button "Checkout"' in details  # page snapshot at the moment of failure
    assert "getByTestId('checkout')  [button, unique]  Checkout" in log["inspect"][1]
    assert "cartPage.checkoutButton" in log["found"][1]
    assert '-      "value": "checkout-btn",' in log["propose"][1] and "nothing written yet" in log["propose"][1]
    assert '"checkout-btn"' in log["untouched"]  # proposing never writes
    assert not log["apply"][0]
    assert '"value": "checkout"' in repo.read_text()
    assert "1 passed" in log["run2"][1]
    assert "[applied]" in log["fixes"][1]
