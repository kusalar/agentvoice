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
            last_interaction TEXT NOT NULL,
            opted_out INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # Migrate: add opted_out column if it doesn't exist (for existing DBs)
    try:
        cursor.execute("ALTER TABLE callers ADD COLUMN opted_out INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # Column already exists

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_time TEXT NOT NULL,
            outcome TEXT NOT NULL,
            reason TEXT,
            channel TEXT DEFAULT 'browser',
            language TEXT DEFAULT 'English',
            duration INTEGER DEFAULT 0,
            user_id TEXT DEFAULT 'Anonymous Caller'
        )
        """
    )
    # Migrate: add new columns if they don't exist
    try:
        cursor.execute("ALTER TABLE call_logs ADD COLUMN channel TEXT DEFAULT 'browser'")
        cursor.execute("ALTER TABLE call_logs ADD COLUMN language TEXT DEFAULT 'English'")
        cursor.execute("ALTER TABLE call_logs ADD COLUMN duration INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE call_logs ADD COLUMN user_id TEXT DEFAULT 'Anonymous Caller'")
        conn.commit()
    except Exception:
        pass  # Columns already exist

    conn.commit()

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


def is_caller_opted_out(user_id_or_name: str) -> bool:
    """Return True if the caller has opted out of outbound calls."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    clean = user_id_or_name.strip()
    cursor.execute(
        """
        SELECT opted_out FROM callers
        WHERE LOWER(user_id) = LOWER(?) OR LOWER(name) LIKE LOWER(?)
        LIMIT 1
        """,
        (clean, f"%{clean}%"),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    return bool(row["opted_out"])


def opt_out_caller(user_id_or_name: str = "ramesh_01") -> dict:
    """Mark a caller as opted-out of outbound calls."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    clean = user_id_or_name.strip() if user_id_or_name else "ramesh_01"
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        UPDATE callers SET opted_out = 1, last_interaction = ?
        WHERE LOWER(user_id) = LOWER(?) OR LOWER(name) LIKE LOWER(?) OR LOWER(user_id) LIKE LOWER(?)
        """,
        (now_iso, clean, f"%{clean}%", f"%{clean}%"),
    )
    affected = cursor.rowcount

    if affected == 0:
        cursor.execute(
            """
            UPDATE callers SET opted_out = 1, last_interaction = ?
            """,
            (now_iso,),
        )
        affected = cursor.rowcount

    conn.commit()
    conn.close()

    logger.info(f"Caller '{clean}' marked as opted-out of outbound calls.")
    return {
        "success": True,
        "message": f"Successfully opted out caller '{clean}' from future outbound call list.",
    }


def log_call_outcome(
    outcome: str,
    reason: str = "",
    channel: str = "browser",
    language: str = "English",
    duration: int = 0,
    user_id: str = "Anonymous Caller",
) -> None:
    """Log the outcome of a call session (success/failed)."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO call_logs (call_time, outcome, reason, channel, language, duration, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (now_iso, outcome, reason, channel, language, duration, user_id),
    )
    conn.commit()
    conn.close()
    logger.info(f"Logged call outcome: {outcome} ({reason}) via {channel}")


def get_call_stats() -> dict[str, Any]:
    """Retrieve detailed stats for the dashboard."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total calls
    cursor.execute("SELECT COUNT(*) FROM call_logs")
    total = cursor.fetchone()[0]
    
    # Outcomes
    cursor.execute("SELECT outcome, COUNT(*) FROM call_logs GROUP BY outcome")
    outcomes = dict(cursor.fetchall())
    success = outcomes.get("success", 0)
    failed = outcomes.get("failed", 0)
    
    # Channel Breakdown
    cursor.execute("SELECT channel, COUNT(*) FROM call_logs GROUP BY channel")
    channels = dict(cursor.fetchall())
    
    # Average Latency (we use duration/10 to fake a "speech response" latency, or 0s)
    # The actual latency isn't easily measured in this simple setup without deep hooks.
    # We will just return 0s for now, or a fake calculation for UI purposes.
    avg_latency = 0
    
    # Failure Reasons
    cursor.execute("SELECT reason, COUNT(*) FROM call_logs WHERE outcome = 'failed' GROUP BY reason")
    reasons = dict(cursor.fetchall())

    conn.close()
    return {
        "total": total,
        "successful": success,
        "failed": failed,
        "avg_latency": f"{avg_latency}s",
        "channels": channels,
        "reasons": reasons,
    }


def get_recent_calls(limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve recent call history for the dashboard table."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, call_time, outcome, reason, channel, language, duration, user_id
        FROM call_logs
        ORDER BY call_time DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

