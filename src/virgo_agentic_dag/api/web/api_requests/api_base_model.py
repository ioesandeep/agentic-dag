"""The base model of this api."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiBaseModel(BaseModel):
    """The camelCase wire format of this api."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
