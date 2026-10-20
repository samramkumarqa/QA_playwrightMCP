import functools
import http.server
import os
import shutil
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FIXTURE = ROOT / "tests" / "fixtures" / "shop-project"
NODE = shutil.which("npm") is not None
needs_node = pytest.mark.skipif(not NODE, reason="node/npm not installed")


@pytest.fixture(scope="session")
def site_url():
    """Serve tests/site (a small practice shop) on a free local port."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "tests" / "site"))
    handler.log_message = lambda *a, **k: None
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture(scope="session")
def installed_modules(tmp_path_factory):
    """npm install the fixture project once; tests copy node_modules from here."""
    if not NODE:
        pytest.skip("npm not installed")
    d = tmp_path_factory.mktemp("npm")
    shutil.copy(FIXTURE / "package.json", d / "package.json")
    run = lambda c: subprocess.run(c, cwd=d, shell=True, capture_output=True, text=True, timeout=600)
    r = run("npm install --silent --no-audit --no-fund")
    assert r.returncode == 0, r.stderr
    pin = os.getenv("PW_TEST_VERSION")  # match the browser build installed on this machine
    if pin:
        assert run(f"npm install --silent --no-audit --no-fund -D @playwright/test@{pin}").returncode == 0
    return d / "node_modules"


@pytest.fixture
def bare_project(tmp_path):
    """The generated project exactly as downloaded: no node_modules, no .env."""
    dst = tmp_path / "shop-project"
    shutil.copytree(FIXTURE, dst)
    return dst


@pytest.fixture
def project_dir(bare_project, installed_modules, site_url):
    """Ready to run: dependencies linked and .env written for the practice shop."""
    (bare_project / "node_modules").symlink_to(installed_modules, target_is_directory=True)
    (bare_project / ".env").write_text(f"BASE_URL={site_url}/\nAPP_USERNAME=standard_user\nAPP_PASSWORD=secret_sauce\n")
    return bare_project
