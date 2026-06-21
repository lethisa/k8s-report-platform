import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.pod import Pod


class ClusterStatus(StrEnum):
    UNKNOWN = 'unknown'
    CONNECTED = 'connected'
    FAILED = 'failed'


class Cluster(db.Model):
    __tablename__ = 'clusters'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    pods: Mapped[list['Pod']] = relationship(
        back_populates='cluster',
        cascade='all, delete-orphan',
        lazy='select',
    )

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    environment: Mapped[str] = mapped_column(String(20), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    kubeconfig: Mapped[str] = mapped_column(Text, nullable=False)

    server: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ClusterStatus.UNKNOWN.value)

    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    def __init__(
        self,
        name: str,
        environment: str,
        kubeconfig: str,
        description: str | None = None,
        server: str | None = None,
        pods: list['Pod'] | None = None,
    ) -> None:
        self.name = name
        self.environment = environment
        self.kubeconfig = kubeconfig
        self.description = description
        self.server = server
        self.pods = pods or []

    def __repr__(self) -> str:
        return f'<Cluster {self.name}>'
