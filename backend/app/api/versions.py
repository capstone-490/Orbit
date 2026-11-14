from enum import StrEnum


class APIVersion(StrEnum):
    V1 = "v1"
    V2 = "v2"


def api_prefix(version: APIVersion) -> str:
    return f"/api/{version.value}"
