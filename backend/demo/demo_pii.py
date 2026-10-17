from pprint import pprint

from security.redactor import redact_data, redact_exception

# Synthetic client information
client = {
    "name": "Sarah Johnson",
    "email": "sarah.johnson@example.com",
    "phone": "514-555-0198",
    "sin": "123-456-789",
    "status": "Active",
    "meeting_notes": [
        "Client called from 416-555-0123",
        "Send follow-up to sarah@example.com",
        "Portfolio review scheduled for Monday",
    ],
}

print("\n========== ORIGINAL/SYNTHETIC DATA ==========")
pprint(client)

print("\n========== REDACTED DATA ==========")
pprint(redact_data(client))

print("\n========== ERROR REDACTION ==========")
try:
    raise ValueError("Failed to process sarah@example.com with SIN 123-456-789")
except ValueError as exc:
    print(redact_exception(exc))
