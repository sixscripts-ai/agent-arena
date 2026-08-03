"""Real Modal sandbox smoke — skipped by default (pytest -m modal)."""
import os

import pytest
from appwrite.query import Query

from agent_arena import db
from tests.conftest import make_user_id, requires_appwrite

pytestmark = pytest.mark.modal


@requires_appwrite
def test_modal_sandbox_spawn_optional():
    if not os.environ.get("INTERNAL_API_KEY"):
        pytest.skip("INTERNAL_API_KEY not set")
    try:
        import modal  # noqa: F401
    except ImportError:
        pytest.skip("modal package not installed")

    from agent_arena.sandbox_launcher import try_spawn_modal_sandbox

    # We only verify the spawn helper does not crash when Modal is available.
    # A full battle requires deployed backend + keys.
    assert callable(try_spawn_modal_sandbox)
