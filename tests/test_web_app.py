"""Guards for the move from the Gradio page to the web app in web/ (spec 0025).

The web app is a separate process, so it cannot read ``Settings`` the way the
Gradio page did. ``GET /config`` hands it the two values it needs; these tests
pin that endpoint, the removal of everything Gradio left behind, and the one
nginx setting that decides which side of the proxy gives up first.
"""

import re
import tomllib
from pathlib import Path

import pytest
from annotated_types import Le
from fastapi.testclient import TestClient

from api.main import ALLOWED_ORIGINS, app
from core.config import Settings, settings

_REPO_ROOT = Path(__file__).resolve().parents[1]
_NGINX_CONF = _REPO_ROOT / "web" / "nginx.conf"


def _chat_timeout_upper_bound() -> float:
    """The ``le`` bound Settings puts on chat_timeout, read from the field itself."""
    bounds = [m.le for m in Settings.model_fields["chat_timeout"].metadata if isinstance(m, Le)]
    assert bounds, "chat_timeout has no upper bound in Settings"
    return float(bounds[0])


def test_config_exposes_what_the_page_needs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Values other than the defaults, so a hardcoded response cannot pass."""
    monkeypatch.setattr(settings, "hallucination_threshold", 0.37)
    monkeypatch.setattr(settings, "chat_timeout", 123.0)

    response = TestClient(app).get("/config")

    assert response.status_code == 200
    assert response.json() == {"hallucination_threshold": 0.37, "chat_timeout": 123.0}


def test_gradio_is_gone() -> None:
    """Pillow came in only through Gradio, so it must leave the lock with it."""
    lock = (_REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    for package in ("gradio", "pillow"):
        assert f'name = "{package}"' not in lock, f"uv.lock still resolves {package}"

    assert not list((_REPO_ROOT / "ui").glob("**/*.py")), "ui/ still holds Python modules"

    pyproject = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tool = pyproject["tool"]
    assert "ui*" not in tool["setuptools"]["packages"]["find"]["include"]
    assert "ui" not in tool["coverage"]["run"]["source"]
    assert "--cov=ui" not in tool["pytest"]["ini_options"]["addopts"]
    assert not any(dep.startswith("gradio") for dep in pyproject["project"]["dependencies"])


def test_cors_names_no_gradio_origin() -> None:
    """The web app is same-origin behind its proxy; the Gradio port has no caller left."""
    assert not [origin for origin in ALLOWED_ORIGINS if origin.endswith(":7860")]


def test_the_proxy_outwaits_the_page() -> None:
    """The page enforces CHAT_TIMEOUT itself, so nginx must never cut the request first.

    A proxy timeout below the page's would turn a slow answer into a 504 the page
    did not choose, at a moment the operator configured to be still waiting.
    """
    conf = _NGINX_CONF.read_text(encoding="utf-8")
    match = re.search(r"proxy_read_timeout\s+(\d+)s?\s*;", conf)
    assert match, "web/nginx.conf sets no proxy_read_timeout"
    assert int(match.group(1)) >= _chat_timeout_upper_bound()
