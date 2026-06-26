from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.inventory.service import (
    convert_ki_to_gib,
    format_age,
    get_ingress_inventory,
    get_inventory_overview,
    get_namespace_inventory,
    get_node_inventory,
    get_pod_inventory,
    get_service_inventory,
    get_storage_inventory_view,
    get_workload_inventory,
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


def _now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture(autouse=True)
def _use_app_context(app):
    pass


def _seed_node(
    cluster_id: str,
    *,
    node_name: str = 'worker-01',
    role: str = 'worker',
    cpu: int = 4,
    memory: str = '8388608Ki',
) -> NodeInventory:
    node = NodeInventory()

    node.cluster_id = cluster_id
    node.node_name = node_name
    node.role = role
    node.os_image = 'Ubuntu 22.04'
    node.kernel_version = '6.1.0'
    node.container_runtime = 'containerd://1.7.0'
    node.cpu = cpu
    node.memory = memory

    db.session.add(node)
    db.session.commit()

    return node


def _seed_namespace(
    cluster_id: str,
    *,
    namespace: str = 'default',
    status: str = 'Active',
) -> NamespaceInventory:
    namespace_inventory = NamespaceInventory()

    namespace_inventory.cluster_id = cluster_id
    namespace_inventory.namespace = namespace
    namespace_inventory.status = status

    db.session.add(namespace_inventory)
    db.session.commit()

    return namespace_inventory


def _seed_workload(
    cluster_id: str,
    *,
    namespace: str = 'default',
    name: str = 'nginx-deployment',
    workload_type: str = 'Deployment',
    ready: str = '1/1',
    status: str = 'Running',
) -> WorkloadInventory:
    workload = WorkloadInventory()

    workload.cluster_id = cluster_id
    workload.namespace = namespace
    workload.name = name
    workload.workload_type = workload_type
    workload.ready = ready
    workload.status = status
    workload.created_at = _now() - timedelta(hours=2)

    db.session.add(workload)
    db.session.commit()

    return workload


def _seed_pod(
    cluster_id: str,
    *,
    namespace: str = 'default',
    pod_name: str = 'nginx-pod',
    phase: str = 'Running',
    restart_count: int = 0,
) -> PodInventory:
    pod = PodInventory()

    pod.cluster_id = cluster_id
    pod.namespace = namespace
    pod.pod_name = pod_name
    pod.node_name = 'worker-01'
    pod.phase = phase
    pod.pod_ip = '10.244.0.10'
    pod.ready = '1/1'
    pod.restart_count = restart_count
    pod.created_at = _now() - timedelta(hours=3)

    db.session.add(pod)
    db.session.commit()

    return pod


def _seed_service(
    cluster_id: str,
    *,
    namespace: str = 'default',
    service_name: str = 'nginx-service',
    service_type: str = 'ClusterIP',
) -> ServiceInventory:
    service = ServiceInventory()

    service.cluster_id = cluster_id
    service.namespace = namespace
    service.service_name = service_name
    service.service_type = service_type
    service.cluster_ip = '10.96.0.10'
    service.external_ip = '-'
    service.ports = '80/TCP'
    service.created_at = _now() - timedelta(hours=4)

    db.session.add(service)
    db.session.commit()

    return service


def _seed_ingress(
    cluster_id: str,
    *,
    namespace: str = 'default',
    ingress_name: str = 'nginx-ingress',
    ingress_class: str = 'nginx',
    host: str = 'nginx.example.local',
    tls_enabled: bool = True,
) -> IngressInventory:
    ingress = IngressInventory()

    ingress.cluster_id = cluster_id
    ingress.namespace = namespace
    ingress.ingress_name = ingress_name
    ingress.ingress_class = ingress_class
    ingress.host = host
    ingress.address = '127.0.0.1'
    ingress.tls_enabled = tls_enabled
    ingress.created_at = _now() - timedelta(hours=5)

    db.session.add(ingress)
    db.session.commit()

    return ingress


def _seed_storage(
    cluster_id: str,
    *,
    namespace: str | None = 'default',
    name: str = 'data-pvc',
    storage_type: str = 'PersistentVolumeClaim',
    storage_class: str = 'standard',
    capacity: str = '10Gi',
    status: str = 'Bound',
) -> StorageInventory:
    storage = StorageInventory()

    storage.cluster_id = cluster_id
    storage.namespace = namespace
    storage.name = name
    storage.storage_type = storage_type
    storage.storage_class = storage_class
    storage.capacity = capacity
    storage.status = status
    storage.created_at = _now() - timedelta(hours=6)

    db.session.add(storage)
    db.session.commit()

    return storage


def _seed_cluster_inventory(
    cluster_id: str,
    *,
    kubernetes_version: str = 'v1.30.0',
) -> ClusterInventory:
    inventory = ClusterInventory()

    inventory.cluster_id = cluster_id
    inventory.kubernetes_version = kubernetes_version

    db.session.add(inventory)
    db.session.commit()

    return inventory


def test_convert_ki_to_gib():
    assert convert_ki_to_gib('1048576Ki') == 1.0
    assert convert_ki_to_gib('8388608Ki') == 8.0
    assert convert_ki_to_gib(None) == 0
    assert convert_ki_to_gib('') == 0
    assert convert_ki_to_gib('8Gi') == 0
    assert convert_ki_to_gib('invalidKi') == 0


def test_format_age_returns_dash_for_empty_value():
    assert format_age(None) == '-'


def test_format_age_returns_hours_for_recent_datetime():
    created_at = _now() - timedelta(hours=2)

    assert format_age(created_at) == '2h'


def test_format_age_returns_days_for_old_datetime():
    created_at = _now() - timedelta(days=3)

    assert format_age(created_at) == '3d'


def test_get_node_inventory_returns_summary(cluster_factory):
    cluster = cluster_factory()

    _seed_node(
        cluster.id,
        node_name='worker-01',
        role='worker',
        cpu=4,
        memory='8388608Ki',
    )

    data = get_node_inventory()

    assert data['total_nodes'] == 1
    assert data['total_cpu'] == 4
    assert data['total_memory'] == 8.0
    assert data['nodes'][0]['cluster_name'] == cluster.name
    assert data['nodes'][0]['node_name'] == 'worker-01'
    assert data['nodes'][0]['role'] == 'worker'
    assert data['nodes'][0]['memory_display'] == '8.0 GiB'
    assert data['nodes'][0]['runtime_display'] == 'containerd'


def test_get_node_inventory_can_filter_by_role(cluster_factory):
    cluster = cluster_factory()

    _seed_node(
        cluster.id,
        node_name='control-plane-01',
        role='control-plane',
    )

    _seed_node(
        cluster.id,
        node_name='worker-01',
        role='worker',
    )

    data = get_node_inventory(
        role='worker',
    )

    assert data['total_nodes'] == 1
    assert data['nodes'][0]['node_name'] == 'worker-01'


def test_get_node_inventory_can_filter_by_search(cluster_factory):
    cluster = cluster_factory()

    _seed_node(
        cluster.id,
        node_name='worker-alpha',
    )

    _seed_node(
        cluster.id,
        node_name='worker-beta',
    )

    data = get_node_inventory(
        search='alpha',
    )

    assert data['total_nodes'] == 1
    assert data['nodes'][0]['node_name'] == 'worker-alpha'


def test_get_namespace_inventory_returns_summary(cluster_factory):
    cluster = cluster_factory()

    _seed_namespace(
        cluster.id,
        namespace='default',
        status='Active',
    )

    _seed_namespace(
        cluster.id,
        namespace='terminating-ns',
        status='Terminating',
    )

    data = get_namespace_inventory()

    assert data['total_namespaces'] == 2
    assert data['total_clusters'] == 1
    assert data['active_namespaces'] == 1
    assert data['status_counts']['Active'] == 1
    assert data['status_counts']['Terminating'] == 1


def test_get_namespace_inventory_can_filter_by_status(cluster_factory):
    cluster = cluster_factory()

    _seed_namespace(
        cluster.id,
        namespace='default',
        status='Active',
    )

    _seed_namespace(
        cluster.id,
        namespace='old-ns',
        status='Terminating',
    )

    data = get_namespace_inventory(
        status='Active',
    )

    assert data['total_namespaces'] == 1

    namespace, cluster_name = data['namespaces'][0]

    assert namespace.namespace == 'default'
    assert cluster_name == cluster.name


def test_get_workload_inventory_returns_summary(cluster_factory):
    cluster = cluster_factory()

    _seed_workload(
        cluster.id,
        name='app-deployment',
        workload_type='Deployment',
        status='Running',
    )

    _seed_workload(
        cluster.id,
        name='db-statefulset',
        workload_type='StatefulSet',
        status='Progressing',
    )

    _seed_workload(
        cluster.id,
        name='agent-daemonset',
        workload_type='DaemonSet',
        status='Running',
    )

    data = get_workload_inventory()

    assert data['total_workloads'] == 3
    assert data['deployments'] == 1
    assert data['statefulsets'] == 1
    assert data['daemonsets'] == 1
    assert data['status_counts']['Running'] == 2
    assert data['status_counts']['Progressing'] == 1


def test_get_workload_inventory_can_filter_by_type(cluster_factory):
    cluster = cluster_factory()

    _seed_workload(
        cluster.id,
        name='app-deployment',
        workload_type='Deployment',
    )

    _seed_workload(
        cluster.id,
        name='db-statefulset',
        workload_type='StatefulSet',
    )

    data = get_workload_inventory(
        workload_type='StatefulSet',
    )

    assert data['total_workloads'] == 1
    assert data['workloads'][0]['name'] == 'db-statefulset'
    assert data['workloads'][0]['type'] == 'StatefulSet'


def test_get_pod_inventory_returns_summary(cluster_factory):
    cluster = cluster_factory()

    _seed_pod(
        cluster.id,
        pod_name='running-pod',
        phase='Running',
    )

    _seed_pod(
        cluster.id,
        pod_name='pending-pod',
        phase='Pending',
    )

    _seed_pod(
        cluster.id,
        pod_name='failed-pod',
        phase='Failed',
        restart_count=3,
    )

    data = get_pod_inventory()

    assert data['total_pods'] == 3
    assert data['running'] == 1
    assert data['pending'] == 1
    assert data['failed'] == 1
    assert 'default' in data['namespaces']


def test_get_pod_inventory_can_filter_by_status(cluster_factory):
    cluster = cluster_factory()

    _seed_pod(
        cluster.id,
        pod_name='running-pod',
        phase='Running',
    )

    _seed_pod(
        cluster.id,
        pod_name='failed-pod',
        phase='Failed',
    )

    data = get_pod_inventory(
        status='Failed',
    )

    assert data['total_pods'] == 1
    assert data['pods'][0]['name'] == 'failed-pod'
    assert data['pods'][0]['status'] == 'Failed'


def test_get_service_inventory_returns_summary(cluster_factory):
    cluster = cluster_factory()

    _seed_service(
        cluster.id,
        service_name='internal-service',
        service_type='ClusterIP',
    )

    _seed_service(
        cluster.id,
        service_name='nodeport-service',
        service_type='NodePort',
    )

    _seed_service(
        cluster.id,
        service_name='external-service',
        service_type='LoadBalancer',
    )

    data = get_service_inventory()

    assert data['total_services'] == 3
    assert data['cluster_ip'] == 1
    assert data['node_port'] == 1
    assert data['load_balancer'] == 1
    assert 'default' in data['namespaces']


def test_get_service_inventory_can_filter_by_type(cluster_factory):
    cluster = cluster_factory()

    _seed_service(
        cluster.id,
        service_name='internal-service',
        service_type='ClusterIP',
    )

    _seed_service(
        cluster.id,
        service_name='external-service',
        service_type='LoadBalancer',
    )

    data = get_service_inventory(
        service_type='LoadBalancer',
    )

    assert data['total_services'] == 1
    assert data['services'][0]['service_name'] == 'external-service'
    assert data['services'][0]['service_type'] == 'LoadBalancer'


def test_get_ingress_inventory_returns_summary(cluster_factory):
    cluster = cluster_factory()

    _seed_ingress(
        cluster.id,
        ingress_name='api-ingress',
        host='api.example.local',
        tls_enabled=True,
    )

    _seed_ingress(
        cluster.id,
        ingress_name='web-ingress',
        host='web.example.local',
        tls_enabled=False,
    )

    data = get_ingress_inventory()

    assert data['total_ingresses'] == 2
    assert data['tls_enabled'] == 1
    assert data['total_hosts'] == 2
    assert data['ingress_classes'] == 1
    assert data['total_namespaces'] == 1


def test_get_ingress_inventory_can_filter_by_class(cluster_factory):
    cluster = cluster_factory()

    _seed_ingress(
        cluster.id,
        ingress_name='nginx-ingress',
        ingress_class='nginx',
    )

    _seed_ingress(
        cluster.id,
        ingress_name='traefik-ingress',
        ingress_class='traefik',
    )

    data = get_ingress_inventory(
        ingress_class='traefik',
    )

    assert data['total_ingresses'] == 1
    assert data['ingresses'][0]['name'] == 'traefik-ingress'
    assert data['ingresses'][0]['class'] == 'traefik'


def test_get_storage_inventory_view_returns_summary(cluster_factory):
    cluster = cluster_factory()

    _seed_storage(
        cluster.id,
        namespace=None,
        name='standard',
        storage_type='StorageClass',
        storage_class='standard',
        capacity='-',
        status='Available',
    )

    _seed_storage(
        cluster.id,
        namespace=None,
        name='pv-data',
        storage_type='PersistentVolume',
        storage_class='standard',
        capacity='100Gi',
        status='Available',
    )

    _seed_storage(
        cluster.id,
        namespace='default',
        name='data-pvc',
        storage_type='PersistentVolumeClaim',
        storage_class='standard',
        capacity='10Gi',
        status='Bound',
    )

    data = get_storage_inventory_view()

    assert data['total_storage'] == 3
    assert data['storage_classes'] == 1
    assert data['persistent_volumes'] == 1
    assert data['persistent_volume_claims'] == 1
    assert 'default' in data['namespaces']


def test_get_storage_inventory_view_can_filter_by_type(cluster_factory):
    cluster = cluster_factory()

    _seed_storage(
        cluster.id,
        namespace=None,
        name='standard',
        storage_type='StorageClass',
        status='Available',
    )

    _seed_storage(
        cluster.id,
        namespace='default',
        name='data-pvc',
        storage_type='PersistentVolumeClaim',
        status='Bound',
    )

    data = get_storage_inventory_view(
        storage_type='PersistentVolumeClaim',
    )

    assert data['total_storage'] == 1
    assert data['storage_items'][0]['name'] == 'data-pvc'
    assert data['storage_items'][0]['type'] == 'PersistentVolumeClaim'


def test_get_inventory_overview_returns_total_counts(cluster_factory):
    cluster = cluster_factory()

    _seed_cluster_inventory(cluster.id)
    _seed_node(cluster.id)
    _seed_namespace(cluster.id)
    _seed_workload(cluster.id)
    _seed_pod(cluster.id)
    _seed_service(cluster.id)
    _seed_ingress(cluster.id)
    _seed_storage(cluster.id)

    data = get_inventory_overview()

    assert data['total_clusters'] == 1
    assert data['total_nodes'] == 1
    assert data['total_namespaces'] == 1
    assert data['total_workloads'] == 1
    assert data['total_pods'] == 1
    assert data['total_services'] == 1
    assert data['total_ingresses'] == 1
    assert data['total_storage'] == 1
    assert data['health']['never_synced'] == 0
