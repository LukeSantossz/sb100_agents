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


def test_compose_qdrant_storage_is_a_named_volume_not_a_host_bind():
    """Qdrant storage must be a named volume, never a host bind mount.

    A Windows/OneDrive host bind mount is exposed to the container as FUSE in WSL2 and stalls
    Qdrant's mmap I/O, hanging vector search and container shutdown (ADR-0014).
    """
    env = _env_without_secret()
    env["JWT_SECRET_KEY"] = VALID_SECRET
    result = _run_compose_config(env, "infra")
    assert result.returncode == 0, result.stderr
    rendered = json.loads(result.stdout)
    storage_mounts = [
        volume
        for volume in rendered["services"]["qdrant"]["volumes"]
        if volume.get("target") == "/qdrant/storage"
    ]
    assert storage_mounts, "no volume mounted at /qdrant/storage"
    assert all(mount.get("type") == "volume" for mount in storage_mounts), storage_mounts
    assert not any(mount.get("type") == "bind" for mount in storage_mounts), storage_mounts


def test_compose_config_fails_when_jwt_secret_unset():
    """Compose config fails fast with the :? message when the secret is unset."""
    # Both profiles are activated so the only reason config can fail is the
    # missing secret: api depends_on qdrant (infra profile), so "--profile app"
    # alone would fail with an unrelated "undefined service qdrant" error.
    env = _env_without_secret()
    result = _run_compose_config(env, "infra", "app", as_json=False)
    assert result.returncode != 0
    assert "JWT_SECRET_KEY must be set" in result.stderr


# --------------- .env forwarding to the containers (issue #215) ---------------
#
# Rendered in a temporary project directory rather than the repository root, so
# the assertions depend on a .env this test wrote and never on the developer's.


def _render_in_project(project_dir: Path, dotenv: str | None) -> dict:
    """Copy the compose file into ``project_dir``, optionally add a .env, render it.

    ``--project-directory`` is what ``env_file`` paths resolve against, so this
    isolates the service's env_file the same way ``--env-file /dev/null``
    isolates interpolation.
    """
    (project_dir / "docker-compose.yml").write_text(
        COMPOSE_FILE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    if dotenv is not None:
        (project_dir / ".env").write_text(dotenv, encoding="utf-8")

    env = _env_without_secret()
    env["JWT_SECRET_KEY"] = VALID_SECRET
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--project-directory",
            str(project_dir),
            "-f",
            str(project_dir / "docker-compose.yml"),
            "--profile",
            "infra",
            "--profile",
            "app",
            "config",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_dotenv_values_reach_the_api_container(tmp_path: Path):
    """Operator settings in .env must reach the container, not stop at the host.

    Before env_file was added, only five variables were forwarded and everything
    else fell back to its Settings default inside the container: verification
    scored a constant 0.5 and AGENT_ENABLED could not be turned on.
    """
    rendered = _render_in_project(
        tmp_path,
        "VERIFICATION_PROVIDER=ollama\nOLLAMA_TIMEOUT=540\nAGENT_ENABLED=true\n",
    )
    api_environment = rendered["services"]["api"]["environment"]
    assert api_environment.get("VERIFICATION_PROVIDER") == "ollama"
    assert api_environment.get("OLLAMA_TIMEOUT") == "540"
    assert api_environment.get("AGENT_ENABLED") == "true"


def test_container_network_settings_win_over_the_dotenv(tmp_path: Path):
    """QDRANT_URL is a container fact, not an operator setting.

    ``.env`` says localhost because that is right for a native run. Inside the
    compose network Qdrant is a service name, so ``environment`` must override
    it; forwarding .env must not break that.
    """
    rendered = _render_in_project(tmp_path, "QDRANT_URL=http://localhost:6333\n")
    assert rendered["services"]["api"]["environment"]["QDRANT_URL"] == "http://qdrant:6333"


def test_config_succeeds_without_a_dotenv(tmp_path: Path):
    """A clean clone has no .env, because it is gitignored, and must still render.

    This is why the env_file entry is ``required: false``: without it compose
    refuses to start over a file the repository never ships.
    """
    rendered = _render_in_project(tmp_path, dotenv=None)
    api_environment = rendered["services"]["api"]["environment"]
    assert set(api_environment) == {"QDRANT_URL", "OLLAMA_HOST", "JWT_SECRET_KEY"}, api_environment


def test_dotenv_values_reach_the_gradio_container(tmp_path: Path):
    """The UI reads CHAT_TIMEOUT from Settings, so it needs the same forwarding."""
    rendered = _render_in_project(tmp_path, "CHAT_TIMEOUT=900\n")
    assert rendered["services"]["gradio"]["environment"].get("CHAT_TIMEOUT") == "900"
