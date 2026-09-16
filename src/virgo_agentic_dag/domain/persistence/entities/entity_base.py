"""The one declarative base every persisted entity in this package maps through."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class EntityBase(DeclarativeBase):
    """The shared metadata root of every persisted table."""
