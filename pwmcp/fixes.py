"""Propose -> (human approves) -> apply code changes, with backups and undo.

propose_fix never writes. apply_fix writes only a fix that was proposed, and only if the file
hasn't changed since; the original is backed up so undo_fix can restore it.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from .project import Project, ProjectError

EDITABLE = {".js", ".ts", ".mjs", ".cjs", ".json"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _pending_dir(project: Project) -> Path:
    d = project.state_dir / "pending"
    d.mkdir(exist_ok=True)
    return d


def _check_syntax(path: Path, new_text: str) -> None:
    if path.suffix == ".json":
        try:
            json.loads(new_text)
        except json.JSONDecodeError as e:
            raise ProjectError(f"The change would make {path.name} invalid JSON: {e}")
    elif path.suffix in {".js", ".cjs", ".mjs"} and shutil.which("node"):
        tmp = path.with_name(f".pwmcp-check-{uuid.uuid4().hex[:6]}{path.suffix}")
        tmp.write_text(new_text, encoding="utf-8")
        try:
            r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True, timeout=30)
        finally:
            tmp.unlink(missing_ok=True)
        if r.returncode:
            msg = r.stderr.replace(str(tmp), path.name).strip().splitlines()
            raise ProjectError("The change would break the JavaScript syntax:\n" + "\n".join(msg[:8]))


def propose_fix(project: Project, file: str, old_text: str, new_text: str, reason: str) -> dict:
    path = project.path(file)
    if path.suffix not in EDITABLE:
        raise ProjectError(f"Only {', '.join(sorted(EDITABLE))} files can be changed.")
    if old_text == new_text:
        raise ProjectError("old_text and new_text are the same.")
    current = path.read_text(encoding="utf-8")
    count = current.count(old_text) if old_text else 0
    if count == 0:
        raise ProjectError(
            f"old_text was not found in {file}. Copy it exactly from the file (read_file), "
            "including indentation, without line numbers."
        )
    if count > 1:
        raise ProjectError(f"old_text occurs {count} times in {file}: include more surrounding lines so it is unique.")
    updated = current.replace(old_text, new_text, 1)
    _check_syntax(path, updated)
    rel = project.rel(path)
    diff = "".join(difflib.unified_diff(
        current.splitlines(keepends=True), updated.splitlines(keepends=True), f"a/{rel}", f"b/{rel}", n=2))
    fix = {
        "id": uuid.uuid4().hex[:8], "file": rel, "reason": reason.strip(), "diff": diff,
        "old_text": old_text, "new_text": new_text, "base_sha": _sha(current), "created": time.time(),
        "status": "pending",
    }
    (_pending_dir(project) / f"{fix['id']}.json").write_text(json.dumps(fix, indent=1))
    return fix


def _load(project: Project, fix_id: str) -> tuple[Path, dict]:
    f = _pending_dir(project) / f"{fix_id.strip()}.json"
    if not f.exists():
        raise ProjectError(f"No proposed fix with id {fix_id!r}. Call list_fixes to see them.")
    return f, json.loads(f.read_text())


def apply_fix(project: Project, fix_id: str) -> dict:
    f, fix = _load(project, fix_id)
    if fix["status"] == "applied":
        raise ProjectError(f"Fix {fix_id} is already applied.")
    path = project.path(fix["file"])
    current = path.read_text(encoding="utf-8")
    if _sha(current) != fix["base_sha"]:
        raise ProjectError(
            f"{fix['file']} changed after this fix was proposed (edited in the IDE?). Propose the fix again."
        )
    backups = project.state_dir / "backups"
    backups.mkdir(exist_ok=True)
    (backups / f"{fix_id}{path.suffix}").write_text(current, encoding="utf-8")
    updated = current.replace(fix["old_text"], fix["new_text"], 1)
    path.write_text(updated, encoding="utf-8")
    fix.update(status="applied", applied=time.time(), applied_sha=_sha(updated))
    f.write_text(json.dumps(fix, indent=1))
    return fix


def undo_fix(project: Project, fix_id: str) -> dict:
    f, fix = _load(project, fix_id)
    if fix["status"] != "applied":
        raise ProjectError(f"Fix {fix_id} isn't applied, so there is nothing to undo.")
    path = project.path(fix["file"])
    if _sha(path.read_text(encoding="utf-8")) != fix.get("applied_sha"):
        raise ProjectError(f"{fix['file']} changed after the fix was applied; undo it in the IDE instead.")
    backup = project.state_dir / "backups" / f"{fix_id}{path.suffix}"
    path.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
    fix["status"] = "undone"
    f.write_text(json.dumps(fix, indent=1))
    return fix


def list_fixes(project: Project) -> list[dict]:
    out = []
    for f in sorted(_pending_dir(project).glob("*.json"), key=lambda p: p.stat().st_mtime):
        fx = json.loads(f.read_text())
        out.append({k: fx[k] for k in ("id", "file", "status", "reason")})
    return out
