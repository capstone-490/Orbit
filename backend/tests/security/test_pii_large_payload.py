import json
import statistics
import time

from app.core.security.redactor import redact_data


def test_large_payload_performance():
    # Step 1: Create a synthetic client record
    client = {
        "name": "Sarah Johnson",
        "email": "sarah@example.com",
        "phone": "514-555-0198",
        "sin": "123-456-789",
        "notes": "Contact sarah@example.com for follow-up.",
    }

    # Step 2: Generate a payload of at least 5 MiB
    target_bytes = 5 * 1024 * 1024

    # Calculate the size of one client record
    client_size = len(json.dumps(client).encode("utf-8"))

    # Estimate how many clients we need
    number_of_clients = (target_bytes // client_size) + 1

    # Generate all clients at once
    payload = {"clients": [client.copy() for _ in range(number_of_clients)]}

    # Measure the actual serialized payload size
    size_bytes = len(json.dumps(payload).encode("utf-8"))

    # Add more clients if necessary to reach 5 MiB
    while size_bytes < target_bytes:
        payload["clients"].append(client.copy())
        size_bytes = len(json.dumps(payload).encode("utf-8"))

    print("\n========== PAYLOAD INFORMATION ==========")
    print(f"Number of clients: {len(payload['clients'])}")
    print(f"Payload size: {size_bytes / (1024 * 1024):.2f} MiB")

    # Step 3: Warm up the redactor
    redact_data(payload)

    # Step 4: Measure performance over 10 runs
    durations_ms = []

    for _ in range(10):
        start = time.perf_counter()
        result = redact_data(payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        durations_ms.append(elapsed_ms)

        # Verify that the first and last clients were redacted
        assert result["clients"][0]["email"] == "[REDACTED]"
        assert result["clients"][0]["phone"] == "[REDACTED]"
        assert result["clients"][0]["sin"] == "[REDACTED]"

        assert result["clients"][-1]["email"] == "[REDACTED]"
        assert result["clients"][-1]["phone"] == "[REDACTED]"
        assert result["clients"][-1]["sin"] == "[REDACTED]"

        # Verify non-sensitive information is preserved
        assert result["clients"][0]["name"] == "Sarah Johnson"

    # Step 5: Calculate performance statistics
    average = statistics.mean(durations_ms)
    median = statistics.median(durations_ms)
    minimum = min(durations_ms)
    maximum = max(durations_ms)

    print("\n========== PERFORMANCE RESULTS ==========")
    print(f"Average: {average:.2f} ms")
    print(f"Median:  {median:.2f} ms")
    print(f"Minimum: {minimum:.2f} ms")
    print(f"Maximum: {maximum:.2f} ms")

    # Step 6: Verify the benchmark executed successfully
    assert len(durations_ms) == 10
    assert size_bytes >= target_bytes
