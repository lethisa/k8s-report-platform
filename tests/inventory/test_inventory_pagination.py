from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.models import (
    IngressInventory,
    NamespaceInventory,
    NodeInventory,
    PodInventory,
    ServiceInventory,
    StorageInventory,
    WorkloadInventory,
)


def _create_nodes(cluster_id: str, total: int = 30) -> None:
    for index in range(total):
        node = NodeInventory()

        node.cluster_id = cluster_id
        node.node_name = f'node-{index:02d}'
        node.role = 'worker'
        node.os_image = 'Ubuntu 22.04'
        node.kernel_version = '6.1.0'
        node.container_runtime = 'containerd://1.7.0'
        node.cpu = 4
        node.memory = '8388608Ki'

        db.session.add(node)

    db.session.commit()


def _create_namespaces(cluster_id: str, total: int = 30) -> None:
    for index in range(total):
        namespace = NamespaceInventory()

        namespace.cluster_id = cluster_id
        namespace.namespace = f'namespace-{index:02d}'
        namespace.status = 'Active'

        db.session.add(namespace)

    db.session.commit()


def _create_workloads(cluster_id: str, total: int = 30) -> None:
    now = datetime.now(UTC)

    for index in range(total):
        workload = WorkloadInventory()

        workload.cluster_id = cluster_id
        workload.namespace = 'default'
        workload.name = f'workload-{index:02d}'
        workload.workload_type = 'Deployment'
        workload.ready = '1/1'
        workload.status = 'Running'
        workload.created_at = now - timedelta(hours=index)

        db.session.add(workload)

    db.session.commit()


def _create_pods(cluster_id: str, total: int = 30) -> None:
    now = datetime.now(UTC)

    for index in range(total):
        pod = PodInventory()

        pod.cluster_id = cluster_id
        pod.namespace = 'default'
        pod.pod_name = f'pod-{index:02d}'
        pod.node_name = 'node-01'
        pod.phase = 'Running'
        pod.pod_ip = f'10.244.0.{index + 1}'
        pod.ready = '1/1'
        pod.restart_count = 0
        pod.created_at = now - timedelta(hours=index)

        db.session.add(pod)

    db.session.commit()


def _create_services(cluster_id: str, total: int = 30) -> None:
    now = datetime.now(UTC)

    for index in range(total):
        service = ServiceInventory()

        service.cluster_id = cluster_id
        service.namespace = 'default'
        service.service_name = f'service-{index:02d}'
        service.service_type = 'ClusterIP'
        service.cluster_ip = f'10.96.0.{index + 1}'
        service.external_ip = '-'
        service.ports = '80/TCP'
        service.created_at = now - timedelta(hours=index)

        db.session.add(service)

    db.session.commit()


def _create_ingresses(cluster_id: str, total: int = 30) -> None:
    now = datetime.now(UTC)

    for index in range(total):
        ingress = IngressInventory()

        ingress.cluster_id = cluster_id
        ingress.namespace = 'default'
        ingress.ingress_name = f'ingress-{index:02d}'
        ingress.ingress_class = 'nginx'
        ingress.host = f'app-{index:02d}.example.local'
        ingress.address = '127.0.0.1'
        ingress.tls_enabled = index % 2 == 0
        ingress.created_at = now - timedelta(hours=index)

        db.session.add(ingress)

    db.session.commit()


def _create_storage_items(cluster_id: str, total: int = 30) -> None:
    now = datetime.now(UTC)

    for index in range(total):
        storage = StorageInventory()

        storage.cluster_id = cluster_id
        storage.namespace = 'default'
        storage.name = f'pvc-{index:02d}'
        storage.storage_type = 'PersistentVolumeClaim'
        storage.storage_class = 'standard'
        storage.capacity = '10Gi'
        storage.status = 'Bound'
        storage.created_at = now - timedelta(hours=index)

        db.session.add(storage)

    db.session.commit()


@pytest.mark.parametrize(
    ('route', 'seed_function'),
    [
        (
            '/inventory/nodes',
            _create_nodes,
        ),
        (
            '/inventory/namespaces',
            _create_namespaces,
        ),
        (
            '/inventory/workloads',
            _create_workloads,
        ),
        (
            '/inventory/pods',
            _create_pods,
        ),
        (
            '/inventory/services',
            _create_services,
        ),
        (
            '/inventory/ingresses',
            _create_ingresses,
        ),
        (
            '/inventory/storage',
            _create_storage_items,
        ),
    ],
)
def test_inventory_pagination_default_per_page_shows_first_page(
    authenticated_client,
    cluster_factory,
    route,
    seed_function,
):
    cluster = cluster_factory()

    seed_function(
        cluster.id,
        30,
    )

    response = authenticated_client.get(route)

    assert response.status_code == 200
    assert b'Page 1 / 2' in response.data
    assert b'Showing' in response.data
    assert b'30' in response.data


@pytest.mark.parametrize(
    ('route', 'seed_function', 'expected_second_page_item'),
    [
        (
            '/inventory/nodes',
            _create_nodes,
            b'node-25',
        ),
        (
            '/inventory/namespaces',
            _create_namespaces,
            b'namespace-25',
        ),
        (
            '/inventory/workloads',
            _create_workloads,
            b'workload-25',
        ),
        (
            '/inventory/pods',
            _create_pods,
            b'pod-25',
        ),
        (
            '/inventory/services',
            _create_services,
            b'service-25',
        ),
        (
            '/inventory/ingresses',
            _create_ingresses,
            b'ingress-25',
        ),
        (
            '/inventory/storage',
            _create_storage_items,
            b'pvc-25',
        ),
    ],
)
def test_inventory_pagination_can_open_second_page(
    authenticated_client,
    cluster_factory,
    route,
    seed_function,
    expected_second_page_item,
):
    cluster = cluster_factory()

    seed_function(
        cluster.id,
        30,
    )

    response = authenticated_client.get(
        f'{route}?page=2',
    )

    assert response.status_code == 200
    assert b'Page 2 / 2' in response.data
    assert expected_second_page_item in response.data


@pytest.mark.parametrize(
    ('route', 'seed_function'),
    [
        (
            '/inventory/nodes',
            _create_nodes,
        ),
        (
            '/inventory/namespaces',
            _create_namespaces,
        ),
        (
            '/inventory/workloads',
            _create_workloads,
        ),
        (
            '/inventory/pods',
            _create_pods,
        ),
        (
            '/inventory/services',
            _create_services,
        ),
        (
            '/inventory/ingresses',
            _create_ingresses,
        ),
        (
            '/inventory/storage',
            _create_storage_items,
        ),
    ],
)
def test_inventory_pagination_invalid_per_page_falls_back_to_25(
    authenticated_client,
    cluster_factory,
    route,
    seed_function,
):
    cluster = cluster_factory()

    seed_function(
        cluster.id,
        30,
    )

    response = authenticated_client.get(
        f'{route}?per_page=999',
    )

    assert response.status_code == 200
    assert b'Page 1 / 2' in response.data
    assert b'<option value="25" selected>25</option>' in response.data


@pytest.mark.parametrize(
    ('route', 'seed_function'),
    [
        (
            '/inventory/nodes',
            _create_nodes,
        ),
        (
            '/inventory/namespaces',
            _create_namespaces,
        ),
        (
            '/inventory/workloads',
            _create_workloads,
        ),
        (
            '/inventory/pods',
            _create_pods,
        ),
        (
            '/inventory/services',
            _create_services,
        ),
        (
            '/inventory/ingresses',
            _create_ingresses,
        ),
        (
            '/inventory/storage',
            _create_storage_items,
        ),
    ],
)
def test_inventory_pagination_page_too_large_falls_back_to_last_page(
    authenticated_client,
    cluster_factory,
    route,
    seed_function,
):
    cluster = cluster_factory()

    seed_function(
        cluster.id,
        30,
    )

    response = authenticated_client.get(
        f'{route}?page=999',
    )

    assert response.status_code == 200
    assert b'Page 2 / 2' in response.data


@pytest.mark.parametrize(
    ('route', 'seed_function'),
    [
        (
            '/inventory/nodes',
            _create_nodes,
        ),
        (
            '/inventory/namespaces',
            _create_namespaces,
        ),
        (
            '/inventory/workloads',
            _create_workloads,
        ),
        (
            '/inventory/pods',
            _create_pods,
        ),
        (
            '/inventory/services',
            _create_services,
        ),
        (
            '/inventory/ingresses',
            _create_ingresses,
        ),
        (
            '/inventory/storage',
            _create_storage_items,
        ),
    ],
)
def test_inventory_pagination_page_less_than_one_falls_back_to_first_page(
    authenticated_client,
    cluster_factory,
    route,
    seed_function,
):
    cluster = cluster_factory()

    seed_function(
        cluster.id,
        30,
    )

    response = authenticated_client.get(
        f'{route}?page=-10',
    )

    assert response.status_code == 200
    assert b'Page 1 / 2' in response.data
