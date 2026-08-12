"""
demo_seed.py — Seeds realistic escalation tickets into the DB for demo/recording.

Run before recording the video:
    uv run python demo_seed.py

Run to clear demo data afterwards:
    uv run python demo_seed.py --clear
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from escalations import (
    init_escalations_db,
    create_escalation,
    update_escalation_status,
    ESC_DB_PATH,
)

def clear_demo_data():
    """Remove all tickets from the DB."""
    conn = sqlite3.connect(ESC_DB_PATH)
    conn.execute("DELETE FROM escalations")
    conn.commit()
    conn.close()
    print("Demo data cleared.")

def seed_demo_data():
    """Insert 3 realistic pre-existing tickets so the dashboard looks active."""
    init_escalations_db()

    # Ticket 1 — Already resolved (Ramesh, honey double charge)
    r1 = create_escalation(
        caller_name="Ramesh",
        issue_type="payment_refund",
        what_happened="Caller reported being charged twice for a 5kg Organic Wildflower Honey order. Amount: approx Rs 900.",
        what_agent_checked="Checked caller profile in DB (Ramesh, ramesh_01). Confirmed past order history shows honey purchase.",
        urgency="high",
        caller_language="Hindi",
        preferred_follow_up="call",
        caller_user_id="ramesh_01",
    )
    update_escalation_status(r1["ref_id"], "resolved")
    print(f"  Created (resolved): {r1['ref_id']} — Ramesh, payment dispute")

    # Ticket 2 — In progress (Priya, damaged sourdough bread)
    r2 = create_escalation(
        caller_name="Priya",
        issue_type="order_complaint",
        what_happened="Caller received a damaged Handcrafted Sourdough Bread. Package arrived crushed and product was unusable.",
        what_agent_checked="Checked live catalogue: Sourdough Bread listed as 'Baked Fresh Daily' from Artisan Local Bakery. No stock issue found.",
        urgency="high",
        caller_language="English",
        preferred_follow_up="email",
        caller_user_id="priya_02",
    )
    update_escalation_status(r2["ref_id"], "in_progress")
    print(f"  Created (in_progress): {r2['ref_id']} — Priya, damaged order")

    # Ticket 3 — Open (new caller, refund not received)
    r3 = create_escalation(
        caller_name="Arjun",
        issue_type="payment_refund",
        what_happened="Caller says they cancelled an order 3 days ago but the refund of Rs 580 has not appeared in their account yet.",
        what_agent_checked="No caller profile found in DB. Catalogue checked for Artisanal Roasted Coffee Beans (cancelled item).",
        urgency="medium",
        caller_language="English",
        preferred_follow_up="sms",
    )
    print(f"  Created (open):       {r3['ref_id']} — Arjun, pending refund")

    # --- Adjust timestamps to be different and realistic ---
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    conn = sqlite3.connect(ESC_DB_PATH)
    
    # Ticket 1 (resolved): Created 2 days ago, updated 1.5 days ago, resolved 2 hours ago
    conn.execute(
        "UPDATE escalations SET created_at=?, updated_at=?, resolved_at=? WHERE ref_id=?",
        (
            (now - timedelta(days=2)).isoformat(),
            (now - timedelta(hours=2)).isoformat(), # The last update was when it was resolved
            (now - timedelta(hours=2)).isoformat(),
            r1["ref_id"]
        )
    )

    # Ticket 2 (in_progress): Created 1 day ago, updated 4 hours ago
    conn.execute(
        "UPDATE escalations SET created_at=?, updated_at=? WHERE ref_id=?",
        (
            (now - timedelta(days=1)).isoformat(),
            (now - timedelta(hours=4)).isoformat(),
            r2["ref_id"]
        )
    )

    # Ticket 3 (open): Created 1 hour ago
    conn.execute(
        "UPDATE escalations SET created_at=?, updated_at=? WHERE ref_id=?",
        (
            (now - timedelta(hours=1)).isoformat(),
            (now - timedelta(hours=1)).isoformat(),
            r3["ref_id"]
        )
    )
    conn.commit()
    conn.close()

    print(f"\nDB path: {ESC_DB_PATH}")
    print("\nDashboard is ready! Open http://localhost:3000/escalations")
    return r3["ref_id"]  # Return the OPEN ticket — this is the one we'll 'create' live in the demo


if __name__ == "__main__":
    if "--clear" in sys.argv:
        clear_demo_data()
    else:
        print("Seeding demo escalation tickets...")
        live_ref = seed_demo_data()
        print(f"\nFor the live demo, the OPEN ticket to show is: {live_ref}")
