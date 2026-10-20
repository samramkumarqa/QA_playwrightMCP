"""Access to the Playwright project the IDE has open: safe paths, files, and the object repository."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

# Files the AI may never read or change: credentials and installed/generated code.
BLOCKED_PARTS = {"node_modules", ".git", ".pwmcp"}
BLOCKED_NAMES = {".env"}


class ProjectError(Exception):
    """A problem the user (or the AI) can fix: the message says how."""


@dataclass
class Project:
    root: Path

    @classmethod
    def locate(cls, project_dir: str = "") -> "Project":
        """Explicit argument, then PW_PROJECT_DIR, then the current directory."""
        raw = project_dir or os.getenv("PW_PROJECT_DIR", "") or os.getcwd()
        root = Path(raw).expanduser().resolve()
        if not (root / "playwright.config.js").exists() and not (root / "playwright.config.ts").exists():
            raise ProjectError(
                f"{root} is not a Playwright project (no playwright.config.js). "
                "Set PW_PROJECT_DIR in the MCP server settings to your project folder."
            )
        return cls(root)

    # ------------------------------------------------------------- paths

    def path(self, rel: str, must_exist: bool = True) -> Path:
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ProjectError(f"{rel} is outside the project folder")
        parts = set(p.relative_to(self.root).parts)
        if parts & BLOCKED_PARTS or p.name in BLOCKED_NAMES:
            raise ProjectError(f"{rel} is off limits (credentials or installed packages)")
        if must_exist and not p.is_file():
            raise ProjectError(f"{rel} does not exist in the project")
        return p

    def rel(self, p: str | Path) -> str:
        p = Path(p)
        try:
            return p.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    @property
    def state_dir(self) -> Path:
        d = self.root / ".pwmcp"
        d.mkdir(exist_ok=True)
        gi = d / ".gitignore"
        if not gi.exists():
            gi.write_text("*\n")
        return d

    # ------------------------------------------------------------- files

    def read(self, rel: str, start: int = 1, end: int = 0) -> str:
        lines = self.path(rel).read_text(encoding="utf-8").splitlines()
        end = end or len(lines)
        start = max(1, start)
        width = len(str(end))
        return "\n".join(f"{i:>{width}}  {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1))

    def list_files(self) -> list[str]:
        out = []
        for p in sorted(self.root.rglob("*")):
            if p.is_file():
                rel = p.relative_to(self.root)
                if set(rel.parts) & (BLOCKED_PARTS | {"test-results", "playwright-report"}) or p.name in BLOCKED_NAMES:
                    continue
                out.append(rel.as_posix())
        return out

    def setup_problems(self) -> list[str]:
        """What stops `npx playwright test` from working: the two mistakes people actually hit."""
        problems = []
        if not (self.root / "node_modules" / "@playwright" / "test").exists():
            problems.append("Dependencies aren't installed: run `npm install` in the project folder.")
        if (self.root / ".env.example").exists() and not (self.root / ".env").exists():
            problems.append(
                "There is no .env file: run `cp .env.example .env` and fill in BASE_URL, "
                "APP_USERNAME and APP_PASSWORD."
            )
        return problems

    # ------------------------------------------------------------- object repository

    def repository(self) -> dict[str, dict]:
        """{PageName: {"url": ..., "elements": {name: {...}}}} from object-repository/*.json."""
        out = {}
        for f in sorted((self.root / "object-repository").glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            out[data.get("page", f.stem)] = data
        return out

    def find_elements(self, query: str, page: str = "", limit: int = 15) -> list[dict]:
        words = [w for w in re.split(r"[^a-z0-9]+", _split_camel(query).lower()) if w]
        hits = []
        for page_name, data in self.repository().items():
            if page and page.lower() not in page_name.lower():
                continue
            for name, e in data.get("elements", {}).items():
                hay = " ".join([_split_camel(name), e.get("value", ""), e.get("description", ""), e.get("kind", "")]).lower()
                score = sum(1 for w in words if w in hay)
                if score:
                    hits.append((score, page_name, name, e))
        hits.sort(key=lambda h: (-h[0], h[1], h[2]))
        return [
            {"use": f"{fixture_name(p)}.{n}", "page": p, "file": f"object-repository/{p}.json", **e}
            for _, p, n, e in hits[:limit]
        ]

    def element(self, fixture: str, name: str) -> dict | None:
        page = fixture[:1].upper() + fixture[1:]
        e = self.repository().get(page, {}).get("elements", {}).get(name)
        return {"page": page, "file": f"object-repository/{page}.json", "name": name, **e} if e else None


def fixture_name(page_class: str) -> str:
    return page_class[:1].lower() + page_class[1:]


def _split_camel(s: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
