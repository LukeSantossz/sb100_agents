"""Infra-dependent tests for docker-compose.yml secret wiring (issue #91).

These shell out to ``docker compose config`` to assert the rendered
configuration; they never start containers. They are skipped when the Docker
Compose CLI is unavailable (category B in SPEC.md), so the suite stays green on
minimal CI images without Docker.

Isolation: every invocation passes ``--env-file /dev/null`` so the result
depends only on the environment dict built here, never on a developer's local
``./.env``.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"

# Any string interpolates; >= 32 chars mirrors the real secret that core.config
# validates at container startup.
VALID_SECRET = "compose-test-jwt-secret-key-32-chars-min"


def _compose_cli_available() -> bool:
    """True when the ``docker compose`` CLI can be invoked."""
    if shutil.which("docker") is None:
        return False
    probe = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        text=True,
    )
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(
    not _compose_cli_available(),
    reason="docker compose CLI unavailable (infra-dependent, SPEC category B)",
)


def _env_without_secret() -> dict[str, str]:
    """Process environment with JWT_SECRET_KEY removed, PATH preserved.

    PATH must survive so the subprocess can still resolve the docker binary.
    """
    return {key: value for key, value in os.environ.items() if key != "JWT_SECRET_KEY"}


def _run_compose_config(
    env: dict[str, str], *profiles: str, as_json: bool = True
) -> subprocess.CompletedProcess:
    """Run ``docker compose config`` against the project compose file.

    ``--env-file /dev/null`` isolates the result from any local ``./.env``.
    """
    command = ["docker", "compose", "--env-file", os.devnull, "-f", str(COMPOSE_FILE)]
    for profile in profiles:
        command += ["--profile", profile]
    command += ["config"]
    if as_json:
        command += ["--format", "json"]
    return subprocess.run(command, capture_output=True, text=True, env=env)


def _service_environment(result: subprocess.CompletedProcess, service: str) -> dict:
    """Parse rendered config and return one service's environment mapping."""
    assert result.returncode == 0, result.stderr
    rendered = json.loads(result.stdout)
    return rendered["services"][service]["environment"]


def test_compose_config_api_environment_contains_jwt_secret():
    """The api service carries JWT_SECRET_KEY when the secret is set."""
    env = _env_without_secret()
    env["JWT_SECRET_KEY"] = VALID_SECRET
    result = _run_compose_config(env, "infra", "app")
    api_environment = _service_environment(result, "api")
    assert api_environment.get("JWT_SECRET_KEY") == VALID_SECRET


def test_compose_config_gradio_environment_contains_jwt_secret():
    """The gradio service carries JWT_SECRET_KEY when the secret is set."""
    env = _env_without_secret()
    env["JWT_SECRET_KEY"] = VALID_SECRET
    result = _run_compose_config(env, "infra", "app")
    gradio_environment = _service_environment(result, "gradio")
    assert gradio_environment.get("JWT_SECRET_KEY") == VALID_SECRET


def test_compose_config_fails_when_jwt_secret_unset():
    """Compose config fails fast with the :? message when the secret is unset."""
    # Both profiles are activated so the only reason config can fail is the
    # missing secret: api depends_on qdrant (infra profile), so "--profile app"
    # alone would fail with an unrelated "undefined service qdrant" error.
    env = _env_without_secret()
    result = _run_compose_config(env, "infra", "app", as_json=False)
    assert result.returncode != 0
    assert "JWT_SECRET_KEY must be set" in result.stderr
