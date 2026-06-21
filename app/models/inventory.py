from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class ClusterInventory(db.Model):
    __tablename__ = 'cluster_inventory'

    id: Mapped[int] = mapped_column(primary_key=True)

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey(
            'clusters.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    kubernetes_version: Mapped[str | None] = mapped_column(String(50))

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(
        self,
        cluster_id: str,
        kubernetes_version: str | None = None,
    ) -> None:
        self.cluster_id = cluster_id
        self.kubernetes_version = kubernetes_version


class NodeInventory(db.Model):
    __tablename__ = 'node_inventory'

    __table_args__ = (
        UniqueConstraint(
            'cluster_id',
            'node_name',
            name='uq_node_inventory_cluster_node',
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey(
            'clusters.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    node_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str | None] = mapped_column(String(50))

    os_image: Mapped[str | None] = mapped_column(String(255))

    kernel_version: Mapped[str | None] = mapped_column(String(255))

    container_runtime: Mapped[str | None] = mapped_column(String(255))

    cpu: Mapped[int | None] = mapped_column(Integer)

    memory: Mapped[str | None] = mapped_column(String(50))

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(
        self,
        cluster_id: str,
        node_name: str,
        role: str | None = None,
        os_image: str | None = None,
        kernel_version: str | None = None,
        container_runtime: str | None = None,
        cpu: int | None = None,
        memory: str | None = None,
    ) -> None:
        self.cluster_id = cluster_id
        self.node_name = node_name
        self.role = role
        self.os_image = os_image
        self.kernel_version = kernel_version
        self.container_runtime = container_runtime
        self.cpu = cpu
        self.memory = memory


class NamespaceInventory(db.Model):
    __tablename__ = 'namespace_inventory'

    __table_args__ = (
        UniqueConstraint(
            'cluster_id',
            'namespace',
            name='uq_namespace_inventory_cluster_namespace',
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey(
            'clusters.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str | None] = mapped_column(String(50))

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(
        self,
        cluster_id: str,
        namespace: str,
        status: str | None = None,
    ) -> None:
        self.cluster_id = cluster_id
        self.namespace = namespace
        self.status = status


class WorkloadInventory(db.Model):
    __tablename__ = 'workload_inventory'

    __table_args__ = (
        UniqueConstraint(
            'cluster_id',
            'namespace',
            'name',
            'workload_type',
            name='uq_workload_inventory',
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey(
            'clusters.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    workload_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    ready: Mapped[str | None] = mapped_column(
        String(50),
    )

    status: Mapped[str | None] = mapped_column(
        String(50),
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(
        self,
        cluster_id: str,
        namespace: str,
        name: str,
        workload_type: str,
        ready: str | None = None,
        status: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.cluster_id = cluster_id
        self.namespace = namespace
        self.name = name
        self.workload_type = workload_type
        self.ready = ready
        self.status = status
        self.created_at = created_at


class PodInventory(db.Model):
    __tablename__ = 'pod_inventory'

    __table_args__ = (
        UniqueConstraint(
            'cluster_id',
            'namespace',
            'pod_name',
            name='uq_pod_inventory',
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey(
            'clusters.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    pod_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    node_name: Mapped[str | None] = mapped_column(
        String(255),
    )

    phase: Mapped[str | None] = mapped_column(
        String(50),
    )

    pod_ip: Mapped[str | None] = mapped_column(
        String(50),
    )

    ready: Mapped[str | None] = mapped_column(
        String(50),
    )

    restart_count: Mapped[int | None] = mapped_column(
        Integer,
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(
        self,
        cluster_id: str,
        namespace: str,
        pod_name: str,
        node_name: str | None = None,
        phase: str | None = None,
        pod_ip: str | None = None,
        ready: str | None = None,
        restart_count: int | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.cluster_id = cluster_id
        self.namespace = namespace
        self.pod_name = pod_name
        self.node_name = node_name
        self.phase = phase
        self.pod_ip = pod_ip
        self.ready = ready
        self.restart_count = restart_count
        self.created_at = created_at


class ServiceInventory(db.Model):
    __tablename__ = 'service_inventory'

    __table_args__ = (
        UniqueConstraint(
            'cluster_id',
            'namespace',
            'service_name',
            name='uq_service_inventory',
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey(
            'clusters.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    service_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    service_type: Mapped[str | None] = mapped_column(
        String(50),
    )

    cluster_ip: Mapped[str | None] = mapped_column(
        String(100),
    )

    external_ip: Mapped[str | None] = mapped_column(
        String(255),
    )

    ports: Mapped[str | None] = mapped_column(
        String(255),
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(
        self,
        cluster_id: str,
        namespace: str,
        service_name: str,
        service_type: str | None = None,
        cluster_ip: str | None = None,
        external_ip: str | None = None,
        ports: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.cluster_id = cluster_id
        self.namespace = namespace
        self.service_name = service_name
        self.service_type = service_type
        self.cluster_ip = cluster_ip
        self.external_ip = external_ip
        self.ports = ports
        self.created_at = created_at


class IngressInventory(db.Model):
    __tablename__ = 'ingress_inventory'

    __table_args__ = (
        UniqueConstraint(
            'cluster_id',
            'namespace',
            'ingress_name',
            name='uq_ingress_inventory',
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey(
            'clusters.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    namespace: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    ingress_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    ingress_class: Mapped[str | None] = mapped_column(
        String(100),
    )

    host: Mapped[str | None] = mapped_column(
        String(255),
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
    )

    tls_enabled: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(
        self,
        cluster_id: str,
        namespace: str,
        ingress_name: str,
        ingress_class: str | None = None,
        host: str | None = None,
        address: str | None = None,
        tls_enabled: bool = False,
        created_at: datetime | None = None,
    ) -> None:
        self.cluster_id = cluster_id
        self.namespace = namespace
        self.ingress_name = ingress_name
        self.ingress_class = ingress_class
        self.host = host
        self.address = address
        self.tls_enabled = tls_enabled
        self.created_at = created_at


class StorageInventory(db.Model):
    __tablename__ = 'storage_inventory'

    __table_args__ = (
        UniqueConstraint(
            'cluster_id',
            'namespace',
            'name',
            'storage_type',
            name='uq_storage_inventory',
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    cluster_id: Mapped[str] = mapped_column(
        ForeignKey(
            'clusters.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )

    namespace: Mapped[str | None] = mapped_column(
        String(255),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    storage_class: Mapped[str | None] = mapped_column(
        String(255),
    )

    capacity: Mapped[str | None] = mapped_column(
        String(100),
    )

    status: Mapped[str | None] = mapped_column(
        String(50),
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(
        self,
        cluster_id: str,
        name: str,
        storage_type: str,
        namespace: str | None = None,
        storage_class: str | None = None,
        capacity: str | None = None,
        status: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.cluster_id = cluster_id
        self.namespace = namespace
        self.name = name
        self.storage_type = storage_type
        self.storage_class = storage_class
        self.capacity = capacity
        self.status = status
        self.created_at = created_at
