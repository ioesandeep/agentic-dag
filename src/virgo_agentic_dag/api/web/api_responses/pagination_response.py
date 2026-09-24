"""A response model for collection pagination."""

from __future__ import annotations

from pydantic import Field
from virgo_agentic_dag.api.web.api_requests.api_base_model import ApiBaseModel


class PaginationResponse(ApiBaseModel):
    """A collection pagination response."""

    next_cursor: int | None = Field(
        description="The cursor for the next page of older items, or null on the last page."
    )
    per_page: int = Field(description="The page size from the request.")
