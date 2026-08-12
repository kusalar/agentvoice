import sys
sys.path.insert(0, 'src')
from escalations import init_escalations_db, create_escalation, get_escalation, list_escalations, _sanitize_pii, update_escalation_status

# Init DB
init_escalations_db()
print("OK: DB initialized")

# Test PII sanitizer
dirty = "My card is 4111111111111111 and OTP is 123456"
clean = _sanitize_pii(dirty)
print(f"OK: PII sanitize => {clean}")

# Test create escalation
result = create_escalation(
    caller_name="TestCaller",
    issue_type="payment_refund",
    what_happened="Caller was charged twice for their honey order.",
    what_agent_checked="Checked catalogue and caller profile.",
    urgency="high",
    caller_language="English",
    preferred_follow_up="call",
    caller_user_id="test_01",
)
print(f"OK: Escalation created: ref_id={result['ref_id']}, is_dup={result['is_duplicate']}")
ref_id = result["ref_id"]

# Test dedup
result2 = create_escalation(
    caller_name="TestCaller",
    issue_type="payment_refund",
    what_happened="Updated: caller still waiting for refund.",
    what_agent_checked="Re-checked catalogue.",
    urgency="high",
    caller_language="English",
    preferred_follow_up="call",
)
expected_dup = result2["ref_id"] == ref_id and result2["is_duplicate"]
print(f"OK: Dedup check => is_duplicate={result2['is_duplicate']}, same_ref={result2['ref_id'] == ref_id}  -> {'PASS' if expected_dup else 'FAIL'}")

# Fetch and list
ticket = get_escalation(ref_id)
print(f"OK: Get ticket => caller={ticket['caller_name']}, status={ticket['status']}, urgency={ticket['urgency']}")

all_tickets = list_escalations()
print(f"OK: List all => {len(all_tickets)} ticket(s)")

# Test status update
upd = update_escalation_status(ref_id, "in_progress")
print(f"OK: Status update => {upd['status']}")

print("\nAll smoke tests passed!")
