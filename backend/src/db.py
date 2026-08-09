import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("db")

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "caller_memory.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize SQLite database table and populate seed callers if empty."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS callers (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            language_preference TEXT,
            facts TEXT NOT NULL,
            last_interaction TEXT NOT NULL
        )
        """
    )

    # Check if table is empty
    cursor.execute("SELECT COUNT(*) FROM callers")
    count = cursor.fetchone()[0]

    if count == 0:
        logger.info("Seeding database with sample caller profiles...")
        sample_callers = [
            (
                "ramesh_01",
                "Ramesh",
                "Hindi",
                json.dumps(
                    {
                        "past_orders": "5kg Organic Wildflower Honey, 2 Sourdough Breads",
                        "usual_quantities": "5kg Honey",
                        "preferred_delivery_slot": "Morning 9 AM - 11 AM",
                        "favorite_vendor": "Local Apiary Farms",
                    }
                ),
                "2026-08-01T10:00:00Z",
            ),
            (
                "priya_02",
                "Priya",
                "English",
                json.dumps(
                    {
                        "past_orders": "Handcrafted Sourdough Bread, Artisanal Coffee",
                        "usual_quantities": "1 loaf",
                        "preferred_delivery_slot": "Evening 5 PM - 7 PM",
                        "favorite_vendor": "Artisan Local Bakery",
                    }
                ),
                "2026-08-05T16:30:00Z",
            ),
        ]
        cursor.executemany(
            """
            INSERT INTO callers (user_id, name, language_preference, facts, last_interaction)
            VALUES (?, ?, ?, ?, ?)
            """,
            sample_callers,
        )
        conn.commit()
    conn.close()


def lookup_caller_in_db(user_id_or_name: str) -> dict[str, Any] | None:
    """Find caller by user_id or name (case-insensitive)."""
    if not user_id_or_name or not user_id_or_name.strip():
        return None

    clean_str = user_id_or_name.strip()
    # Ignore generic placeholders
    if clean_str.lower() in ("user", "caller", "unknown", "none", "null", "me", "someone"):
        return None

    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    query_param = f"%{clean_str}%"

    cursor.execute(
        """
        SELECT user_id, name, language_preference, facts, last_interaction
        FROM callers
        WHERE LOWER(user_id) = LOWER(?) OR LOWER(name) LIKE LOWER(?)
        ORDER BY last_interaction DESC
        LIMIT 1
        """,
        (clean_str, query_param),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    try:
        facts_dict = json.loads(row["facts"])
    except Exception:
        facts_dict = {}

    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "language_preference": row["language_preference"] or "English",
        "facts": facts_dict,
        "last_interaction": row["last_interaction"],
    }


def save_caller_in_db(
    user_id: str,
    name: str,
    language_preference: str | None = None,
    fact_key: str | None = None,
    fact_value: str | None = None,
    has_user_consent: bool = False,
) -> dict[str, Any]:
    """
    Save or update caller data in database.
    CRITICAL: Refuses to save if has_user_consent is False.
    """
    if not has_user_consent:
        logger.warning(f"Refusing to save data for '{name}' because user consent was NOT granted.")
        return {
            "success": False,
            "message": "Data NOT saved. Explicit user consent was not granted.",
        }

    clean_name = name.strip() if name else "Guest Caller"
    clean_user_id = user_id.strip() if user_id else ""
    if not clean_user_id or clean_user_id.lower() in ("user", "caller", "unknown", "none", "null"):
        clean_user_id = f"{clean_name.lower().replace(' ', '_')}_id"

    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    existing = lookup_caller_in_db(clean_user_id) or lookup_caller_in_db(clean_name)
    now_iso = datetime.now(timezone.utc).isoformat()

    if existing:
        final_user_id = existing["user_id"]
        final_name = clean_name if clean_name != "Guest Caller" else existing["name"]
        final_lang = language_preference or existing["language_preference"]
        facts_dict = existing["facts"]
        if fact_key and fact_value:
            facts_dict[fact_key] = fact_value

        cursor.execute(
            """
            UPDATE callers
            SET name = ?, language_preference = ?, facts = ?, last_interaction = ?
            WHERE user_id = ?
            """,
            (final_name, final_lang, json.dumps(facts_dict), now_iso, final_user_id),
        )
    else:
        final_user_id = clean_user_id
        final_name = clean_name
        final_lang = language_preference or "English"
        facts_dict = {}
        if fact_key and fact_value:
            facts_dict[fact_key] = fact_value

        cursor.execute(
            """
            INSERT INTO callers (user_id, name, language_preference, facts, last_interaction)
            VALUES (?, ?, ?, ?, ?)
            """,
            (final_user_id, final_name, final_lang, json.dumps(facts_dict), now_iso),
        )

    conn.commit()
    conn.close()

    updated_record = lookup_caller_in_db(final_user_id)
    return {
        "success": True,
        "message": f"Successfully saved caller memory for {final_name}.",
        "record": updated_record,
    }
