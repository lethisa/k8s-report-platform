from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from kubernetes.client import AppsV1Api, CoreV1Api, NetworkingV1Api, StorageV1Api

from app.extensions import db
from app.inventory.service import (
    save_cluster_info,
    save_ingresses,
    save_namespaces,
    save_nodes,
    save_pods,
    save_services,
    save_storage_inventory,
    save_workloads,
)
from app.models import (
    ClusterInventory,
    IngressInventory,
    NamespaceInventory,
    NodeInventory,
    PodInventory,
    ServiceInventory,
    StorageInventory,
    WorkloadInventory,
)


@pytest.fixture(autouse=True)
def _use_app_context(app):
    pass


def _created_at() -> datetime:
    return datetime.now(UTC)


def _core_api():
    return cast(
        CoreV1Api,
        SimpleNamespace(),
    )


def _core_api_with_namespaces(namespaces):
    return cast(
        CoreV1Api,
        SimpleNamespace(
            list_namespace=lambda: SimpleNamespace(
                items=namespaces,
            ),
        ),
    )


def _apps_api():
    return cast(
        AppsV1Api,
        SimpleNamespace(),
    )


def _networking_api():
    return cast(
        NetworkingV1Api,
        SimpleNamespace(),
    )


def _storage_api():
    return cast(
        StorageV1Api,
        SimpleNamespace(),
    )


def _fake_node(
    *,
    name: str = 'worker-01',
    role_label: str | None = None,
    cpu: str = '4',
    memory: str = '8388608Ki',
    ready_status: str = 'True',
    ephemeral_storage: str = '104857600Ki',
    ephemeral_storage_allocatable: str = '94371840Ki',
):
    labels = {}

    if role_label:
        labels[f'node-role.kubernetes.io/{role_label}'] = ''

    return SimpleNamespace(
        metadata=SimpleNamespace(
            name=name,
            labels=labels,
        ),
        status=SimpleNamespace(
            node_info=SimpleNamespace(
                os_image='Ubuntu 22.04',
                kernel_version='6.1.0',
                container_runtime_version='containerd://1.7.0',
            ),
            capacity={
                'cpu': cpu,
                'memory': memory,
                'ephemeral-storage': ephemeral_storage,
            },
            allocatable={
                'ephemeral-storage': ephemeral_storage_allocatable,
            },
            conditions=[
                SimpleNamespace(
                    type='Ready',
                    status=ready_status,
                ),
            ],
        ),
    )


def _fake_namespace(
    *,
    name: str = 'default',
    status: str = 'Active',
):
    return SimpleNamespace(
        metadata=SimpleNamespace(
            name=name,
        ),
        status=SimpleNamespace(
            phase=status,
        ),
    )


def test_save_cluster_info_creates_cluster_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    monkeypatch.setattr(
        'app.inventory.service.get_cluster_version',
        lambda: 'v1.30.0',
    )

    save_cluster_info(cluster)

    db.session.commit()

    inventory = ClusterInventory.query.filter_by(
        cluster_id=cluster.id,
    ).first()

    assert inventory is not None
    assert inventory.kubernetes_version == 'v1.30.0'


def test_save_cluster_info_replaces_existing_cluster_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    existing = ClusterInventory()

    existing.cluster_id = cluster.id
    existing.kubernetes_version = 'v1.29.0'

    db.session.add(existing)
    db.session.commit()

    monkeypatch.setattr(
        'app.inventory.service.get_cluster_version',
        lambda: 'v1.30.0',
    )

    save_cluster_info(cluster)

    db.session.commit()

    inventories = ClusterInventory.query.filter_by(
        cluster_id=cluster.id,
    ).all()

    assert len(inventories) == 1
    assert inventories[0].kubernetes_version == 'v1.30.0'


def test_save_nodes_creates_node_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    monkeypatch.setattr(
        'app.inventory.service.get_nodes',
        lambda api: [
            _fake_node(
                name='worker-01',
                role_label=None,
                cpu='4',
                memory='8388608Ki',
                ready_status='True',
                ephemeral_storage='104857600Ki',
                ephemeral_storage_allocatable='94371840Ki',
            ),
            _fake_node(
                name='control-plane-01',
                role_label='control-plane',
                cpu='2',
                memory='4194304Ki',
                ready_status='False',
                ephemeral_storage='52428800Ki',
                ephemeral_storage_allocatable='47185920Ki',
            ),
        ],
    )

    save_nodes(
        cluster,
        api=_core_api(),
    )

    db.session.commit()

    nodes = (
        NodeInventory.query.filter_by(
            cluster_id=cluster.id,
        )
        .order_by(
            NodeInventory.node_name,
        )
        .all()
    )

    assert len(nodes) == 2

    control_plane = next(node for node in nodes if node.node_name == 'control-plane-01')

    worker = next(node for node in nodes if node.node_name == 'worker-01')

    assert worker.role == 'worker'
    assert worker.status == 'Ready'
    assert worker.cpu == 4
    assert worker.memory == '8388608Ki'
    assert worker.ephemeral_storage == '104857600Ki'
    assert worker.ephemeral_storage_allocatable == '94371840Ki'
    assert worker.os_image == 'Ubuntu 22.04'
    assert worker.container_runtime == 'containerd://1.7.0'

    assert control_plane.role == 'control-plane'
    assert control_plane.status == 'NotReady'
    assert control_plane.cpu == 2
    assert control_plane.ephemeral_storage == '52428800Ki'
    assert control_plane.ephemeral_storage_allocatable == '47185920Ki'


def test_save_nodes_handles_unknown_ready_condition(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    monkeypatch.setattr(
        'app.inventory.service.get_nodes',
        lambda api: [
            _fake_node(
                name='worker-unknown',
                ready_status='Unknown',
            ),
        ],
    )

    save_nodes(
        cluster,
        api=_core_api(),
    )

    db.session.commit()

    node = NodeInventory.query.filter_by(
        cluster_id=cluster.id,
        node_name='worker-unknown',
    ).first()

    assert node is not None
    assert node.status == 'Unknown'


def test_save_nodes_handles_invalid_cpu_as_none(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    monkeypatch.setattr(
        'app.inventory.service.get_nodes',
        lambda api: [
            _fake_node(
                name='worker-01',
                cpu='not-a-number',
            ),
        ],
    )

    save_nodes(
        cluster,
        api=_core_api(),
    )

    db.session.commit()

    node = NodeInventory.query.filter_by(
        cluster_id=cluster.id,
        node_name='worker-01',
    ).first()

    assert node is not None
    assert node.cpu is None


def test_save_nodes_replaces_existing_node_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    existing = NodeInventory()

    existing.cluster_id = cluster.id
    existing.node_name = 'old-node'
    existing.role = 'worker'
    existing.status = 'Ready'
    existing.cpu = 1
    existing.memory = '1048576Ki'
    existing.ephemeral_storage = '10485760Ki'
    existing.ephemeral_storage_allocatable = '9437184Ki'

    db.session.add(existing)
    db.session.commit()

    monkeypatch.setattr(
        'app.inventory.service.get_nodes',
        lambda api: [
            _fake_node(
                name='new-node',
                cpu='4',
            ),
        ],
    )

    save_nodes(
        cluster,
        api=_core_api(),
    )

    db.session.commit()

    nodes = NodeInventory.query.filter_by(
        cluster_id=cluster.id,
    ).all()

    assert len(nodes) == 1
    assert nodes[0].node_name == 'new-node'


def test_save_namespaces_creates_namespace_inventory(
    cluster_factory,
):
    cluster = cluster_factory()

    api = _core_api_with_namespaces(
        [
            _fake_namespace(
                name='default',
                status='Active',
            ),
            _fake_namespace(
                name='kube-system',
                status='Active',
            ),
        ],
    )

    save_namespaces(
        cluster,
        api,
    )

    db.session.commit()

    namespaces = (
        NamespaceInventory.query.filter_by(
            cluster_id=cluster.id,
        )
        .order_by(
            NamespaceInventory.namespace,
        )
        .all()
    )

    assert len(namespaces) == 2
    assert namespaces[0].namespace == 'default'
    assert namespaces[0].status == 'Active'
    assert namespaces[1].namespace == 'kube-system'


def test_save_namespaces_replaces_existing_namespace_inventory(
    cluster_factory,
):
    cluster = cluster_factory()

    existing = NamespaceInventory()

    existing.cluster_id = cluster.id
    existing.namespace = 'old-namespace'
    existing.status = 'Active'

    db.session.add(existing)
    db.session.commit()

    api = _core_api_with_namespaces(
        [
            _fake_namespace(
                name='new-namespace',
                status='Active',
            ),
        ],
    )

    save_namespaces(
        cluster,
        api,
    )

    db.session.commit()

    namespaces = NamespaceInventory.query.filter_by(
        cluster_id=cluster.id,
    ).all()

    assert len(namespaces) == 1
    assert namespaces[0].namespace == 'new-namespace'


def test_save_workloads_creates_workload_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()
    created_at = _created_at()

    monkeypatch.setattr(
        'app.inventory.service.get_workloads',
        lambda api: [
            {
                'namespace': 'default',
                'name': 'web',
                'workload_type': 'Deployment',
                'ready': '1/1',
                'status': 'Running',
                'created_at': created_at,
            },
            {
                'namespace': 'default',
                'name': 'db',
                'workload_type': 'StatefulSet',
                'ready': '1/1',
                'status': 'Running',
                'created_at': created_at,
            },
        ],
    )

    save_workloads(
        cluster,
        apps_api=_apps_api(),
    )

    db.session.commit()

    workloads = (
        WorkloadInventory.query.filter_by(
            cluster_id=cluster.id,
        )
        .order_by(
            WorkloadInventory.name,
        )
        .all()
    )

    assert len(workloads) == 2
    assert workloads[0].name == 'db'
    assert workloads[0].workload_type == 'StatefulSet'
    assert workloads[1].name == 'web'
    assert workloads[1].workload_type == 'Deployment'


def test_save_pods_creates_pod_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()
    created_at = _created_at()

    monkeypatch.setattr(
        'app.inventory.service.get_pods',
        lambda api: [
            {
                'namespace': 'default',
                'pod_name': 'web-pod',
                'node_name': 'worker-01',
                'phase': 'Running',
                'pod_ip': '10.244.0.10',
                'ready': '1/1',
                'restart_count': 0,
                'created_at': created_at,
            },
        ],
    )

    save_pods(
        cluster,
        api=_core_api(),
    )
    db.session.commit()

    pod = PodInventory.query.filter_by(
        cluster_id=cluster.id,
        pod_name='web-pod',
    ).first()

    assert pod is not None
    assert pod.namespace == 'default'
    assert pod.node_name == 'worker-01'
    assert pod.phase == 'Running'
    assert pod.pod_ip == '10.244.0.10'
    assert pod.ready == '1/1'
    assert pod.restart_count == 0


def test_save_services_creates_service_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()
    created_at = _created_at()

    monkeypatch.setattr(
        'app.inventory.service.get_services',
        lambda api: [
            {
                'namespace': 'default',
                'service_name': 'web-service',
                'service_type': 'ClusterIP',
                'cluster_ip': '10.96.0.10',
                'external_ip': '-',
                'ports': '80/TCP',
                'created_at': created_at,
            },
        ],
    )

    save_services(
        cluster,
        api=_core_api(),
    )

    db.session.commit()

    service = ServiceInventory.query.filter_by(
        cluster_id=cluster.id,
        service_name='web-service',
    ).first()

    assert service is not None
    assert service.namespace == 'default'
    assert service.service_type == 'ClusterIP'
    assert service.cluster_ip == '10.96.0.10'
    assert service.external_ip == '-'
    assert service.ports == '80/TCP'


def test_save_ingresses_creates_ingress_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()
    created_at = _created_at()

    monkeypatch.setattr(
        'app.inventory.service.get_ingresses',
        lambda api: [
            {
                'namespace': 'default',
                'ingress_name': 'web-ingress',
                'ingress_class': 'nginx',
                'host': 'web.example.local',
                'address': '127.0.0.1',
                'tls_enabled': True,
                'created_at': created_at,
            },
        ],
    )

    save_ingresses(
        cluster,
        api=_networking_api(),
    )

    db.session.commit()

    ingress = IngressInventory.query.filter_by(
        cluster_id=cluster.id,
        ingress_name='web-ingress',
    ).first()

    assert ingress is not None
    assert ingress.namespace == 'default'
    assert ingress.ingress_class == 'nginx'
    assert ingress.host == 'web.example.local'
    assert ingress.address == '127.0.0.1'
    assert ingress.tls_enabled is True


def test_save_storage_inventory_creates_storage_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()
    created_at = _created_at()

    monkeypatch.setattr(
        'app.inventory.service.get_storage_inventory',
        lambda core_api, storage_api: [
            {
                'namespace': None,
                'name': 'standard',
                'storage_type': 'StorageClass',
                'storage_class': 'standard',
                'capacity': '-',
                'status': 'Available',
                'created_at': created_at,
            },
            {
                'namespace': 'default',
                'name': 'data-pvc',
                'storage_type': 'PersistentVolumeClaim',
                'storage_class': 'standard',
                'capacity': '10Gi',
                'status': 'Bound',
                'created_at': created_at,
            },
        ],
    )

    save_storage_inventory(
        cluster,
        core_api=_core_api(),
        storage_api=_storage_api(),
    )

    db.session.commit()

    storage_items = (
        StorageInventory.query.filter_by(
            cluster_id=cluster.id,
        )
        .order_by(
            StorageInventory.name,
        )
        .all()
    )

    assert len(storage_items) == 2

    pvc = next(item for item in storage_items if item.name == 'data-pvc')

    storage_class = next(item for item in storage_items if item.name == 'standard')

    assert storage_class.storage_type == 'StorageClass'
    assert storage_class.storage_class == 'standard'
    assert storage_class.status == 'Available'

    assert pvc.namespace == 'default'
    assert pvc.storage_type == 'PersistentVolumeClaim'
    assert pvc.capacity == '10Gi'
    assert pvc.status == 'Bound'


def test_save_storage_inventory_replaces_existing_storage_inventory(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    existing = StorageInventory()

    existing.cluster_id = cluster.id
    existing.namespace = 'default'
    existing.name = 'old-pvc'
    existing.storage_type = 'PersistentVolumeClaim'
    existing.storage_class = 'standard'
    existing.capacity = '1Gi'
    existing.status = 'Bound'

    db.session.add(existing)
    db.session.commit()

    monkeypatch.setattr(
        'app.inventory.service.get_storage_inventory',
        lambda core_api, storage_api: [
            {
                'namespace': 'default',
                'name': 'new-pvc',
                'storage_type': 'PersistentVolumeClaim',
                'storage_class': 'standard',
                'capacity': '10Gi',
                'status': 'Bound',
                'created_at': _created_at(),
            },
        ],
    )

    save_storage_inventory(
        cluster,
        core_api=_core_api(),
        storage_api=_storage_api(),
    )

    db.session.commit()

    storage_items = StorageInventory.query.filter_by(
        cluster_id=cluster.id,
    ).all()

    assert len(storage_items) == 1
    assert storage_items[0].name == 'new-pvc'
