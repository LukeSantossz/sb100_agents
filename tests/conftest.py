"""Shared test suite configuration.

Sets required environment variables before ``core.config`` is imported (it
validates ``JWT_SECRET_KEY`` at startup). ``setdefault`` preserves externally
provided values (e.g. CI), applying the test value only when absent.
"""

import os

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-jwt-secret-key-for-tests-only-32-chars-minimum",
)
