"""Python side of inspect_page: run inspect_page.js inside the user's project and format the result."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .project import Project, ProjectError

SCRIPT = Path(__file__).with_name("inspect_page.js")


def inspect_page(project: Project, url_path: str = "/", login: bool = True, timeout: int = 120) -> str:
    problems = project.setup_problems()
    if problems:
        raise ProjectError(" ".join(problems))
    node = shutil.which("node")
    if not node:
        raise ProjectError("Node.js isn't installed or not on the PATH.")
    try:
        r = subprocess.run([node, str(SCRIPT), url_path or "/", "1" if login else "0"], cwd=project.root,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ProjectError(f"Opening {url_path} took longer than {timeout} s.")
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        err = (r.stderr or r.stdout).strip()
        if "Executable doesn't exist" in err:
            raise ProjectError("Playwright's browser isn't installed: run `npx playwright install chromium` in the project.")
        raise ProjectError(f"Couldn't inspect the page: {err[-1500:]}")
    return format_inspection(data)


def format_inspection(data: dict) -> str:
    lines = [f"Page: {data.get('url', '?')}  (title: {data.get('title', '')})",
             f"Logged in first: {'yes' if data.get('loggedIn') else 'no'} · test id attribute: {data.get('testIdAttribute')}"]
    if data.get("requested") and data.get("url") and data["requested"].strip("/") not in data["url"]:
        lines.append(f"Note: asked for {data['requested']} but the app showed {data['url']} (redirect? not logged in?)")
    if data.get("error"):
        lines.append(f"Error while opening the page: {data['error']}")
    els = data.get("elements") or []
    if els:
        lines.append("")
        lines.append("Elements (locator · unique? · visible? · text/label):")
        for e in els:
            flags = ("unique" if e.get("unique") else f"{e.get('matches')} matches") + ("" if e.get("visible") else ", hidden")
            what = e.get("label") or e.get("text") or ""
            lines.append(f"- {e['locator']}  [{e['tag']}{'/' + e['type'] if e.get('type') else ''}, {flags}]  {what}")
    return "\n".join(lines)
