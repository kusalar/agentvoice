import json
import os
import sys

import pytest

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from db import init_db, lookup_caller_in_db, save_caller_in_db


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure DB is initialized before tests."""
    init_db()


def test_sqlite_db_seed_records():
    """Step 1 & 2: Verify SQLite DB initializes with seed caller records and expected schema."""
    ramesh = lookup_caller_in_db("Ramesh")
    assert ramesh is not None
    assert ramesh["user_id"] == "ramesh_01"
    assert ramesh["name"] == "Ramesh"
    assert ramesh["language_preference"] == "Hindi"
    assert "past_orders" in ramesh["facts"]
    assert "last_interaction" in ramesh

    priya = lookup_caller_in_db("Priya")
    assert priya is not None
    assert priya["user_id"] == "priya_02"
    assert priya["name"] == "Priya"
    assert priya["language_preference"] == "English"
    assert "past_orders" in priya["facts"]


def test_consent_enforcement_refusal():
    """Step 5: Verify data saving is rejected when user consent is NOT granted."""
    result = save_caller_in_db(
        user_id="test_user_01",
        name="TestUser",
        language_preference="English",
        fact_key="preferred_slot",
        fact_value="Morning 10 AM",
        has_user_consent=False,  # User said NO
    )
    assert result["success"] is False
    assert "NOT saved" in result["message"]

    # Verify nothing was created in DB
    record = lookup_caller_in_db("TestUser")
    assert record is None


def test_consent_granted_saving():
    """Step 2 & 5: Verify data saving succeeds when user consent IS granted."""
    result = save_caller_in_db(
        user_id="ramesh_01",
        name="Ramesh",
        language_preference="Hindi",
        fact_key="delivery_slot",
        fact_value="Evening 6 PM",
        has_user_consent=True,  # User said YES
    )
    assert result["success"] is True

    record = lookup_caller_in_db("Ramesh")
    assert record is not None
    assert record["facts"]["delivery_slot"] == "Evening 6 PM"
