import sys
sys.path.insert(0, 'src')
from escalations import _sanitize_pii

cases = [
    ("OTP is 123456", "[OTP_REDACTED]"),
    ("my otp: 4321", "[OTP_REDACTED]"),
    ("card 4111111111111111", "[CARD_REDACTED]"),
    ("pin is 9876", "[PIN_REDACTED]"),
    ("CVV: 123", "[CVV_REDACTED]"),
]
all_pass = True
for text, expected_token in cases:
    result = _sanitize_pii(text)
    ok = expected_token in result
    status = "PASS" if ok else "FAIL"
    print(f"  {status}: {repr(text)} => {repr(result)}")
    if not ok:
        all_pass = False

if all_pass:
    print("All PII tests passed!")
else:
    print("SOME TESTS FAILED!")
    sys.exit(1)
