from __future__ import annotations
from datetime import datetime
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.cluster import Cluster

class Pod(db.Model):
    __tablename__ = "pods"

    __table_args__ = (
        UniqueConstraint(
            "cluster_id",
            "namespace",
            "name",
            name="uq_pod_cluster_namespace_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id"),
        nullable=False,
        index=True,
    )

    cluster: Mapped["Cluster"] = relationship(
        back_populates="pods"
    )

    namespace: Mapped[str] = mapped_column(
        db.String(255),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        db.String(255),
        nullable=False,
    )

    status: Mapped[str | None] = mapped_column(
        db.String(50)
    )

    node_name: Mapped[str | None] = mapped_column(
        db.String(255)
    )

    pod_ip: Mapped[str | None] = mapped_column(
        db.String(50)
    )

    restart_count: Mapped[int] = mapped_column(
        default=0
    )

    owner_kind: Mapped[str | None] = mapped_column(
        db.String(50)
    )

    owner_name: Mapped[str | None] = mapped_column(
        db.String(255)
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow
    )

    def __init__(
        self,
        cluster_id: int,
        namespace: str,
        name: str,
        status: str | None = None,
        node_name: str | None = None,
        pod_ip: str | None = None,
        restart_count: int = 0,
        owner_kind: str | None = None,
        owner_name: str | None = None,
    ) -> None:
        self.name = name
        self.cluster_id = cluster_id
        self.namespace = namespace
        self.status = status
        self.node_name = node_name
        self.pod_ip = pod_ip
        self.restart_count = restart_count
        self.owner_kind = owner_kind
        self.owner_name = owner_name


    def __repr__(self) -> str:
        return (
            f"<Pod {self.namespace}/{self.name}>"
        )