import os
import sys
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from db import init_db, is_caller_opted_out, opt_out_caller, lookup_caller_in_db
from agent import SYSTEM_PROMPT


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def test_outbound_prompt_contains_required_opening():
    """Step 4: Verify agent prompt contains 2-sentence opening instructions (who, why, opt-out)."""
    assert "Sentence 1 (Who & Why)" in SYSTEM_PROMPT
    assert "Sentence 2 (How to stop)" in SYSTEM_PROMPT
    assert "opt_out_user" in SYSTEM_PROMPT


def test_opt_out_database_functions():
    """Step 4: Verify opt-out function sets opted_out flag in database."""
    # Reset Ramesh's opted_out status for clean test run
    from db import get_connection
    conn = get_connection()
    conn.cursor().execute("UPDATE callers SET opted_out = 0 WHERE name = 'Ramesh'")
    conn.commit()
    conn.close()

    # Ensure caller exists
    ramesh = lookup_caller_in_db("Ramesh")
    assert ramesh is not None
    assert is_caller_opted_out("Ramesh") is False

    # Execute opt out
    res = opt_out_caller("Ramesh")
    assert res["success"] is True

    # Verify opted out flag is set
    assert is_caller_opted_out("Ramesh") is True
