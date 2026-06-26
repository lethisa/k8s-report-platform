from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from kubernetes.client import AppsV1Api, CoreV1Api, NetworkingV1Api, StorageV1Api

from app.inventory.service import sync_inventory


@pytest.fixture(autouse=True)
def _use_app_context(app):
    pass


class FakeKubernetesClient:
    def __init__(self, kubeconfig: str):
        self.kubeconfig = kubeconfig

    def core_api(self) -> CoreV1Api:
        return cast(
            CoreV1Api,
            SimpleNamespace(name='core-api'),
        )

    def apps_api(self) -> AppsV1Api:
        return cast(
            AppsV1Api,
            SimpleNamespace(name='apps-api'),
        )

    def networking_api(self) -> NetworkingV1Api:
        return cast(
            NetworkingV1Api,
            SimpleNamespace(name='networking-api'),
        )

    def storage_api(self) -> StorageV1Api:
        return cast(
            StorageV1Api,
            SimpleNamespace(name='storage-api'),
        )


def test_sync_inventory_calls_all_save_functions(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    called = {
        'save_cluster_info': False,
        'save_nodes': False,
        'save_namespaces': False,
        'save_workloads': False,
        'save_pods': False,
        'save_services': False,
        'save_ingresses': False,
        'save_storage_inventory': False,
        'commit': False,
        'rollback': False,
    }

    monkeypatch.setattr(
        'app.inventory.service.KubernetesClient',
        FakeKubernetesClient,
    )

    def fake_save_cluster_info(received_cluster):
        assert received_cluster.id == cluster.id
        called['save_cluster_info'] = True

    def fake_save_nodes(received_cluster, api):
        assert received_cluster.id == cluster.id
        assert getattr(api, 'name') == 'core-api'
        called['save_nodes'] = True

    def fake_save_namespaces(received_cluster, api):
        assert received_cluster.id == cluster.id
        assert getattr(api, 'name') == 'core-api'
        called['save_namespaces'] = True

    def fake_save_workloads(received_cluster, apps_api):
        assert received_cluster.id == cluster.id
        assert getattr(apps_api, 'name') == 'apps-api'
        called['save_workloads'] = True

    def fake_save_pods(received_cluster, api):
        assert received_cluster.id == cluster.id
        assert getattr(api, 'name') == 'core-api'
        called['save_pods'] = True

    def fake_save_services(received_cluster, api):
        assert received_cluster.id == cluster.id
        assert getattr(api, 'name') == 'core-api'
        called['save_services'] = True

    def fake_save_ingresses(received_cluster, api):
        assert received_cluster.id == cluster.id
        assert getattr(api, 'name') == 'networking-api'
        called['save_ingresses'] = True

    def fake_save_storage_inventory(received_cluster, core_api, storage_api):
        assert received_cluster.id == cluster.id
        assert getattr(core_api, 'name') == 'core-api'
        assert getattr(storage_api, 'name') == 'storage-api'
        called['save_storage_inventory'] = True

    monkeypatch.setattr(
        'app.inventory.service.save_cluster_info',
        fake_save_cluster_info,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_nodes',
        fake_save_nodes,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_namespaces',
        fake_save_namespaces,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_workloads',
        fake_save_workloads,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_pods',
        fake_save_pods,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_services',
        fake_save_services,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_ingresses',
        fake_save_ingresses,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_storage_inventory',
        fake_save_storage_inventory,
    )

    monkeypatch.setattr(
        'app.inventory.service.db.session.commit',
        lambda: called.update(commit=True),
    )

    monkeypatch.setattr(
        'app.inventory.service.db.session.rollback',
        lambda: called.update(rollback=True),
    )

    sync_inventory(cluster)

    assert called == {
        'save_cluster_info': True,
        'save_nodes': True,
        'save_namespaces': True,
        'save_workloads': True,
        'save_pods': True,
        'save_services': True,
        'save_ingresses': True,
        'save_storage_inventory': True,
        'commit': True,
        'rollback': False,
    }


def test_sync_inventory_commits_when_successful(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    called = {
        'commit': False,
        'rollback': False,
    }

    monkeypatch.setattr(
        'app.inventory.service.KubernetesClient',
        FakeKubernetesClient,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_cluster_info',
        lambda cluster: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_nodes',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_namespaces',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_workloads',
        lambda cluster, apps_api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_pods',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_services',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_ingresses',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_storage_inventory',
        lambda cluster, core_api, storage_api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.db.session.commit',
        lambda: called.update(commit=True),
    )

    monkeypatch.setattr(
        'app.inventory.service.db.session.rollback',
        lambda: called.update(rollback=True),
    )

    sync_inventory(cluster)

    assert called['commit'] is True
    assert called['rollback'] is False


def test_sync_inventory_rolls_back_when_save_function_fails(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    called = {
        'commit': False,
        'rollback': False,
    }

    monkeypatch.setattr(
        'app.inventory.service.KubernetesClient',
        FakeKubernetesClient,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_cluster_info',
        lambda cluster: None,
    )

    def failing_save_nodes(cluster, api):
        raise RuntimeError('collector failed')

    monkeypatch.setattr(
        'app.inventory.service.save_nodes',
        failing_save_nodes,
    )

    monkeypatch.setattr(
        'app.inventory.service.db.session.commit',
        lambda: called.update(commit=True),
    )

    monkeypatch.setattr(
        'app.inventory.service.db.session.rollback',
        lambda: called.update(rollback=True),
    )

    with pytest.raises(
        RuntimeError,
        match='collector failed',
    ):
        sync_inventory(cluster)

    assert called['commit'] is False
    assert called['rollback'] is True


def test_sync_inventory_passes_cluster_kubeconfig_to_kubernetes_client(
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()
    received = {
        'kubeconfig': None,
    }

    class TrackingKubernetesClient(FakeKubernetesClient):
        def __init__(self, kubeconfig: str):
            super().__init__(kubeconfig)
            received['kubeconfig'] = kubeconfig

    monkeypatch.setattr(
        'app.inventory.service.KubernetesClient',
        TrackingKubernetesClient,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_cluster_info',
        lambda cluster: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_nodes',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_namespaces',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_workloads',
        lambda cluster, apps_api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_pods',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_services',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_ingresses',
        lambda cluster, api: None,
    )

    monkeypatch.setattr(
        'app.inventory.service.save_storage_inventory',
        lambda cluster, core_api, storage_api: None,
    )

    sync_inventory(cluster)

    assert received['kubeconfig'] == cluster.kubeconfig
