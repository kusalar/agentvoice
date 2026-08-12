"""
escalations.py — Human escalation request DB layer for Local Commerce Assistant.

Handles:
  - Creating escalation tickets (with deduplication within 24 h)
  - PII sanitization before storage
  - Urgency classification
  - Status transitions: open → in_progress → resolved
  - Outbound callback when a ticket is resolved (hooks into dial.py)
"""

import json
import logging
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("escalations")

# ---------------------------------------------------------------------------
# DB path (same data/ directory as caller_memory.db)
# ---------------------------------------------------------------------------
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
ESC_DB_PATH = os.path.join(DB_DIR, "escalations.db")

# ---------------------------------------------------------------------------
# Urgency levels
# ---------------------------------------------------------------------------
URGENCY_LEVELS = ("low", "medium", "high", "emergency")
ISSUE_TYPES = ("payment_refund", "order_complaint", "other")

# ---------------------------------------------------------------------------
# PII patterns to scrub before storing
# ---------------------------------------------------------------------------
_PII_PATTERNS = [
    # 16-digit card numbers (with optional spaces/dashes)
    (re.compile(r"\b(\d[ -]?){15}\d\b"), "[CARD_REDACTED]"),
    # OTP: "OTP is 123456", "otp: 4321", "one-time-password 887766"
    (re.compile(r"\b(otp|one[- ]?time[- ]?password)\s*(?:is\s*)?[:\-]?\s*\d{4,8}\b", re.IGNORECASE), "[OTP_REDACTED]"),
    # Standalone 4–8 digit PIN/OTP after keyword
    (re.compile(r"\b(pin|passcode|password|code)\s*(?:is\s*)?[:\-]?\s*\d{4,8}\b", re.IGNORECASE), "[PIN_REDACTED]"),
    # Bank account numbers: 9–18 digits
    (re.compile(r"\baccount\s*(?:number|no\.?)?\s*[:\-]?\s*\d{9,18}\b", re.IGNORECASE), "[ACCT_REDACTED]"),
    # UPI IDs
    (re.compile(r"\b[\w.\-]+@[\w.\-]+\b"), "[UPI_REDACTED]"),  # catches "name@upi" style
    # CVV
    (re.compile(r"\bcvv\s*[:\-]?\s*\d{3,4}\b", re.IGNORECASE), "[CVV_REDACTED]"),
]


def _sanitize_pii(text: str) -> str:
    """Remove sensitive patterns from text before storage."""
    if not text:
        return text
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def _gen_ref_id() -> str:
    """Generate ESC-YYYYMMDD-XXXX format reference ID."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = random.randint(1000, 9999)
    return f"ESC-{today}-{suffix}"


# ---------------------------------------------------------------------------
# DB connection + init
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(ESC_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_escalations_db() -> None:
    """Create escalations table if it does not exist."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS escalations (
            ref_id              TEXT PRIMARY KEY,
            caller_name         TEXT NOT NULL,
            caller_user_id      TEXT,
            caller_language     TEXT NOT NULL DEFAULT 'English',
            preferred_follow_up TEXT NOT NULL DEFAULT 'call',
            issue_type          TEXT NOT NULL,
            what_happened       TEXT NOT NULL,
            what_agent_checked  TEXT NOT NULL DEFAULT '',
            urgency             TEXT NOT NULL DEFAULT 'medium',
            status              TEXT NOT NULL DEFAULT 'open',
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL,
            resolved_at         TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    logger.info("Escalations DB initialized.")


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------

def find_open_duplicate(caller_name: str, issue_type: str) -> dict[str, Any] | None:
    """
    Return an existing open/in-progress ticket for the same caller + issue_type
    created within the last 24 hours, or None if no duplicate exists.
    """
    init_escalations_db()
    conn = _get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cursor.execute(
        """
        SELECT * FROM escalations
        WHERE LOWER(caller_name) LIKE LOWER(?)
          AND issue_type = ?
          AND status != 'resolved'
          AND created_at > ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (f"%{caller_name.strip()}%", issue_type, cutoff),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def create_escalation(
    caller_name: str,
    issue_type: str,
    what_happened: str,
    what_agent_checked: str,
    urgency: str,
    caller_language: str,
    preferred_follow_up: str,
    caller_user_id: str = "",
) -> dict[str, Any]:
    """
    Create a new escalation ticket, or update an existing open one (deduplication).
    PII is sanitized from text fields before saving.

    Returns a dict with:
        ref_id, status, created_at, is_duplicate
    """
    init_escalations_db()

    # Sanitize free-text fields
    safe_happened = _sanitize_pii(what_happened)
    safe_checked = _sanitize_pii(what_agent_checked)
    clean_name = caller_name.strip() or "Unknown Caller"
    clean_lang = caller_language.strip() or "English"
    clean_follow_up = preferred_follow_up.strip() or "call"
    clean_urgency = urgency.lower() if urgency.lower() in URGENCY_LEVELS else "medium"
    clean_issue = issue_type if issue_type in ISSUE_TYPES else "other"

    now = datetime.now(timezone.utc).isoformat()

    # Check for duplicate
    existing = find_open_duplicate(clean_name, clean_issue)
    if existing:
        logger.info(
            f"Duplicate escalation found for '{clean_name}' / '{clean_issue}' — "
            f"updating ref_id={existing['ref_id']}"
        )
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE escalations
            SET what_happened = ?,
                what_agent_checked = ?,
                urgency = ?,
                updated_at = ?
            WHERE ref_id = ?
            """,
            (safe_happened, safe_checked, clean_urgency, now, existing["ref_id"]),
        )
        conn.commit()
        conn.close()
        return {
            "ref_id": existing["ref_id"],
            "status": existing["status"],
            "created_at": existing["created_at"],
            "is_duplicate": True,
            "message": (
                f"An existing ticket ({existing['ref_id']}) was already open for this issue. "
                "It has been updated with the latest details."
            ),
        }

    # New ticket
    ref_id = _gen_ref_id()
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO escalations
            (ref_id, caller_name, caller_user_id, caller_language, preferred_follow_up,
             issue_type, what_happened, what_agent_checked, urgency, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
        """,
        (
            ref_id, clean_name, caller_user_id, clean_lang, clean_follow_up,
            clean_issue, safe_happened, safe_checked, clean_urgency, now, now,
        ),
    )
    conn.commit()
    conn.close()

    logger.info(f"New escalation created: ref_id={ref_id}, caller='{clean_name}', urgency={clean_urgency}")
    return {
        "ref_id": ref_id,
        "status": "open",
        "created_at": now,
        "is_duplicate": False,
        "message": f"Escalation ticket {ref_id} created successfully.",
    }


def get_escalation(ref_id: str) -> dict[str, Any] | None:
    """Fetch a single escalation by ref_id."""
    init_escalations_db()
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escalations WHERE ref_id = ?", (ref_id.upper(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def list_escalations(status_filter: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch all escalations, optionally filtered by status.
    status_filter: None | 'open' | 'in_progress' | 'resolved'
    """
    init_escalations_db()
    conn = _get_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute(
            "SELECT * FROM escalations WHERE status = ? ORDER BY created_at DESC",
            (status_filter,),
        )
    else:
        cursor.execute("SELECT * FROM escalations ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_escalation_status(ref_id: str, new_status: str) -> dict[str, Any]:
    """
    Transition an escalation to a new status.
    Valid transitions: open → in_progress → resolved
    """
    valid_statuses = ("open", "in_progress", "resolved")
    if new_status not in valid_statuses:
        return {"success": False, "message": f"Invalid status '{new_status}'."}

    init_escalations_db()
    conn = _get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    resolved_at = now if new_status == "resolved" else None
    cursor.execute(
        """
        UPDATE escalations
        SET status = ?, updated_at = ?, resolved_at = COALESCE(?, resolved_at)
        WHERE ref_id = ?
        """,
        (new_status, now, resolved_at, ref_id.upper()),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected == 0:
        return {"success": False, "message": f"No ticket found with ref_id '{ref_id}'."}

    logger.info(f"Escalation {ref_id} status updated to '{new_status}'.")
    return {"success": True, "ref_id": ref_id, "status": new_status, "updated_at": now}


# ---------------------------------------------------------------------------
# Summary builder (for agent verbal reply)
# ---------------------------------------------------------------------------

def build_caller_summary(ref_id: str) -> str:
    """
    Build a clean verbal summary string to read to the caller after ticket creation.
    No PII is included.
    """
    ticket = get_escalation(ref_id)
    if not ticket:
        return f"Ticket {ref_id} has been logged. A human agent will follow up with you."

    urgency_phrases = {
        "emergency": "as an emergency and will be reviewed immediately",
        "high": "as high priority and will be reviewed very soon",
        "medium": "and will be reviewed within a few hours",
        "low": "and will be reviewed within 1 business day",
    }
    urgency_note = urgency_phrases.get(ticket["urgency"], "and will be reviewed shortly")

    follow_up_map = {
        "call": "phone call",
        "email": "email",
        "sms": "text message",
        "whatsapp": "WhatsApp message",
    }
    follow_up = follow_up_map.get(ticket["preferred_follow_up"], "follow-up")

    return (
        f"Your support request has been logged with reference number {ref_id}. "
        f"It has been marked {urgency_note}. "
        f"A human agent will reach out to you via {follow_up}. "
        f"You can check the status any time by asking me 'What is the status of {ref_id}?'"
    )
