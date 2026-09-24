"""The memory file of a dag."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class MemoryResponse(ApiBaseModel):
    """Represents the memory file of a dag."""

    content: str = Field(
        description="The text of the memory file, empty when the file does not exist."
    )
    updated_at: datetime | None = Field(
        description=(
            "The modification time of the memory file, null when the file does not "
            "exist."
        )
    )
