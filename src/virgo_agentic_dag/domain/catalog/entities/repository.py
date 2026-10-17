from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from virgo_agentic_dag.domain.catalog.checkout_kind_enum import CheckoutKindEnum
from virgo_agentic_dag.domain.catalog.checkout_state_enum import CheckoutStateEnum
from virgo_agentic_dag.domain.catalog.entities.catalog_entity_base import (
    CatalogEntityBase,
)
from virgo_agentic_dag.domain.catalog.repository_provider_enum import (
    RepositoryProviderEnum,
)


class Repository(CatalogEntityBase):
    """Persist repository identity and checkout registration metadata."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    _provider_type = Enum(
        RepositoryProviderEnum,
        values_callable=list,
        native_enum=False,
        create_constraint=True,
        name="repository_provider",
    )
    provider: Mapped[RepositoryProviderEnum] = mapped_column(
        _provider_type, nullable=False
    )
    host: Mapped[str] = mapped_column(Text, nullable=False)
    provider_repository_id: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    web_url: Mapped[str] = mapped_column(Text, nullable=False)
    default_branch: Mapped[str | None] = mapped_column(Text, nullable=True)
    _checkout_kind_type = Enum(
        CheckoutKindEnum,
        values_callable=list,
        native_enum=False,
        create_constraint=True,
        name="repository_checkout_kind",
    )
    checkout_kind: Mapped[CheckoutKindEnum] = mapped_column(
        _checkout_kind_type, nullable=False
    )
    checkout_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    remote_name: Mapped[str] = mapped_column(Text, nullable=False)
    _checkout_state_type = Enum(
        CheckoutStateEnum,
        values_callable=list,
        native_enum=False,
        create_constraint=True,
        name="repository_checkout_state",
    )
    checkout_state: Mapped[CheckoutStateEnum] = mapped_column(
        _checkout_state_type, nullable=False
    )
    _timestamp_type = DateTime(timezone=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        _timestamp_type, nullable=True
    )
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(_timestamp_type, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(_timestamp_type, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(_timestamp_type, nullable=True)

    _identity_constraint = UniqueConstraint(
        "provider", "host", "provider_repository_id", name="uq_repositories_identity"
    )
    __table_args__ = (_identity_constraint,)
