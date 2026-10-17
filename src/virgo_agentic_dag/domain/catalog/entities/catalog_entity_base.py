from sqlalchemy.orm import DeclarativeBase


class CatalogEntityBase(DeclarativeBase):
    """Define catalog tables independently of run tables."""
