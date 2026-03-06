"""Sample API module for discovery tests."""


def get_user(user_id: int) -> dict[str, int]:
    """Return a fake user payload."""

    return {"id": user_id}


def create_user(payload: dict[str, str]) -> dict[str, str]:
    return payload
