import os

os.environ.setdefault("DB_NAME", "orbit_test")
os.environ.setdefault("DB_USER", "orbit_user")
os.environ.setdefault("DB_PASSWORD", "orbit_password")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "6105")
os.environ.setdefault(
    "ORBIT_ANONYMIZATION_SECRET",
    "test-only-anonymization-secret-with-32-chars",
)
