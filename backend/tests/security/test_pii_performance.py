import statistics
import time

from app.core.security.redactor import redact_data


def test_pii_redaction_performance():
    client = {
        "name": "Sarah Johnson",
        "email": "sarah@example.com",
        "phone": "514-555-0198",
        "sin": "123-456-789",
        "notes": [
            "Contact sarah@example.com",
            "Follow-up scheduled for Monday",
        ],
    }

    # Warm up before measuring
    for _ in range(100):
        redact_data(client)

    durations = []

    # Measure 1000 individual redaction operations
    for _ in range(1000):
        start = time.perf_counter()
        result = redact_data(client)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result["email"] == "[REDACTED]"
        durations.append(elapsed_ms)

    average = statistics.mean(durations)
    median = statistics.median(durations)
    p95 = sorted(durations)[949]

    print(f"\nAverage: {average:.4f} ms")
    print(f"Median:  {median:.4f} ms")
    print(f"P95:     {p95:.4f} ms")

    assert p95 < 5, f"P95 latency exceeded 5 ms: {p95:.4f} ms"
