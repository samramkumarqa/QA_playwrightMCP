"""Fast tests: project access, object repository search, diagnosis hints, and the fix workflow."""

import json

import pytest

from pwmcp import fixes, runner
from pwmcp.project import Project, ProjectError


def test_locate_requires_a_playwright_project(tmp_path, bare_project, monkeypatch):
    with pytest.raises(ProjectError, match="not a Playwright project"):
        Project.locate(str(tmp_path))
    monkeypatch.setenv("PW_PROJECT_DIR", str(bare_project))
    assert Project.locate().root == bare_project.resolve()


def test_paths_stay_inside_project_and_away_from_credentials(bare_project):
    p = Project.locate(str(bare_project))
    (bare_project / ".env").write_text("APP_PASSWORD=secret\n")
    for bad in ["../outside.js", ".env", "node_modules/x/index.js", "/etc/passwd"]:
        with pytest.raises(ProjectError):
            p.path(bad, must_exist=False)
    assert ".env" not in p.list_files()
    assert "tests/FR-01.spec.js" in p.list_files()


def test_setup_problems_name_the_fix(bare_project):
    problems = " ".join(Project.locate(str(bare_project)).setup_problems())
    assert "npm install" in problems and "cp .env.example .env" in problems


def test_find_elements_reuses_page_objects(bare_project):
    p = Project.locate(str(bare_project))
    hits = p.find_elements("cart button")
    assert hits[0]["use"] == "commonPage.shoppingCartLink"
    assert p.find_elements("checkout", page="Cart")[0]["use"] == "cartPage.checkoutButton"
    assert p.element("cartPage", "checkoutButton")["value"] == "checkout"


def test_read_file_numbers_lines(bare_project):
    out = Project.locate(str(bare_project)).read("object-repository/CartPage.json", 1, 3)
    assert out.splitlines()[1].startswith("2  ")


# ------------------------------------------------------------- fixes

def test_propose_writes_nothing_and_apply_needs_the_same_file(bare_project):
    p = Project.locate(str(bare_project))
    f = bare_project / "object-repository" / "CartPage.json"
    before = f.read_text()
    fx = fixes.propose_fix(p, "object-repository/CartPage.json", '"value": "checkout"', '"value": "checkout-2"',
                           "test id changed")
    assert f.read_text() == before
    assert '-      "value": "checkout",' in fx["diff"] and '+      "value": "checkout-2",' in fx["diff"]

    fixes.apply_fix(p, fx["id"])
    assert '"checkout-2"' in f.read_text()
    with pytest.raises(ProjectError, match="already applied"):
        fixes.apply_fix(p, fx["id"])
    fixes.undo_fix(p, fx["id"])
    assert f.read_text() == before
    assert [x["status"] for x in fixes.list_fixes(p)] == ["undone"]


def test_apply_refuses_when_file_was_edited_after_proposal(bare_project):
    p = Project.locate(str(bare_project))
    fx = fixes.propose_fix(p, "tests/FR-01.spec.js", 'getTestData("TC-001");', 'getTestData("TC-001"); // x', "r")
    spec = bare_project / "tests" / "FR-01.spec.js"
    spec.write_text(spec.read_text() + "\n// edited in IntelliJ\n")
    with pytest.raises(ProjectError, match="changed after this fix was proposed"):
        fixes.apply_fix(p, fx["id"])


@pytest.mark.parametrize("file,old,new,msg", [
    ("tests/FR-01.spec.js", "nothing like this", "x", "not found"),
    ("tests/FR-01.spec.js", "await", "await ", "occurs"),
    ("object-repository/CartPage.json", '"checkout"', '"checkout', "invalid JSON"),
    ("tests/FR-01.spec.js", 'getTestData("TC-001");', 'getTestData("TC-001";', "JavaScript syntax"),
    ("test-data/TestData.xlsx", "a", "b", "Only"),
    (".env.example", "BASE_URL", "X", "Only"),
])
def test_propose_rejects_bad_changes(bare_project, file, old, new, msg):
    with pytest.raises(ProjectError, match=msg):
        fixes.propose_fix(Project.locate(str(bare_project)), file, old, new, "r")


# ------------------------------------------------------------- diagnosis

def test_hints_cover_the_common_failures():
    strict = runner.diagnose("Error: strict mode violation: getByTestId('x') resolved to 6 elements", "")
    assert "6 elements" in strict[0] and "waitForPage" in strict[0]
    missing = runner.diagnose("Test timeout of 30000ms exceeded.\n  - waiting for getByTestId('checkout-btn')", "")
    assert "getByTestId('checkout-btn') never appeared" in missing[0]
    creds = runner.diagnose("Error: No login credentials: copy .env.example to .env", "")
    assert "npm install" in creds[0]
    on_login = runner.diagnose("Test timeout\n waiting for getByTestId('a')", '- textbox "Username"\n- button "Login"')
    assert any("login page" in h for h in on_login)


def test_parse_report_finds_spec_line_and_context(bare_project, tmp_path):
    p = Project.locate(str(bare_project))
    ctx = tmp_path / "error-context.md"
    ctx.write_text("# Page snapshot\n\n```yaml\n- button \"Checkout\" [ref=e9]\n```\n")
    spec = bare_project / "tests" / "FR-03.spec.js"
    report = {
        "config": {"rootDir": str(bare_project / "tests")},
        "suites": [{"title": "FR-03.spec.js", "file": "FR-03.spec.js", "specs": [], "suites": [{
            "title": "FR-03", "specs": [{"title": "TC-004: Verify checkout requires the first name", "file": "FR-03.spec.js",
                                       "line": 7, "tests": [{"status": "unexpected", "results": [{
                "status": "timedOut", "duration": 30000,
                "errors": [{"message": "Test timeout of 30000ms exceeded."},
                           {"message": f"Error: locator.click: Test timeout\n  - waiting for getByTestId('checkout-btn')\n"
                                       f"    at {spec}:20:35"}],
                "attachments": [{"name": "error-context", "path": str(ctx)}]}]}]}]}]}],
    }
    [o] = runner.parse_report(p, report)
    assert (o.file, o.line, o.status, o.frames) == ("tests/FR-03.spec.js", 7, "timedOut", [("tests/FR-03.spec.js", 20)])
    details = runner.failure_details(p, o)
    assert ">>   20      await cartPage.checkoutButton.click();" in details
    assert "cartPage.checkoutButton -> getByTestId('checkout')  [object-repository/CartPage.json]" in details
    assert 'button "Checkout"' in details
    assert runner.find_outcome([o], "TC-004") is o
    assert "1 timedOut" in runner.summarize([o])
    json.dumps(runner.summarize([o]))
