"""Mints the token an agent session is resumed by."""

from __future__ import annotations

import uuid


def create_session_token() -> str:
    """Return a token for an agent session that does not exist yet."""
    return str(uuid.uuid4())
