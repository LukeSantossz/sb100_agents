"""Guards on the project's pytest configuration.

Ensures the `requires_infra` marker stays registered: CI selects the suite with
`-m "not requires_infra"`, so an unregistered marker would silently change which
tests run (and warn on any `@pytest.mark.requires_infra` usage). See #104.
"""

import pytest


def test_requires_infra_marker_is_registered(pytestconfig: pytest.Config) -> None:
    """The `requires_infra` marker is declared in the pytest configuration."""
    markers = pytestconfig.getini("markers")
    assert any(marker.startswith("requires_infra:") for marker in markers), (
        "register a 'requires_infra' marker in [tool.pytest.ini_options] markers"
    )
