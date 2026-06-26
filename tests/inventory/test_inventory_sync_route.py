from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _use_app_context(app):
    pass


def test_inventory_sync_route_requires_login(
    client,
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    called = {
        'sync_inventory': False,
    }

    def fake_sync_inventory(received_cluster):
        called['sync_inventory'] = True

    monkeypatch.setattr(
        'app.inventory.routes.sync_inventory',
        fake_sync_inventory,
    )

    response = client.post(
        f'/inventory/{cluster.id}/sync',
        follow_redirects=False,
    )

    assert response.status_code in [
        302,
        401,
    ]

    assert called['sync_inventory'] is False


def test_inventory_sync_route_calls_sync_inventory_for_authenticated_user(
    authenticated_client,
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    called = {
        'sync_inventory': False,
        'get_cluster_summary': False,
        'template': None,
    }

    def fake_sync_inventory(received_cluster):
        assert received_cluster.id == cluster.id
        called['sync_inventory'] = True

    def fake_get_cluster_summary():
        called['get_cluster_summary'] = True

        return [
            cluster,
        ], {
            cluster.id: {
                'nodes': 0,
                'namespaces': 0,
                'workloads': 0,
                'pods': 0,
                'services': 0,
                'ingresses': 0,
                'storage': 0,
            },
        }

    def fake_render_template(template_name, **context):
        called['template'] = template_name

        assert context['clusters'] == [
            cluster,
        ]

        assert cluster.id in context['inventory_summary']

        return 'sync-ok'

    monkeypatch.setattr(
        'app.inventory.routes.sync_inventory',
        fake_sync_inventory,
    )

    monkeypatch.setattr(
        'app.inventory.routes.get_cluster_summary',
        fake_get_cluster_summary,
    )

    monkeypatch.setattr(
        'app.inventory.routes.render_template',
        fake_render_template,
    )

    response = authenticated_client.post(
        f'/inventory/{cluster.id}/sync',
    )

    assert response.status_code == 200
    assert response.data == b'sync-ok'
    assert called['sync_inventory'] is True
    assert called['get_cluster_summary'] is True
    assert called['template'] == 'cluster/partials/table.html'


def test_inventory_sync_route_returns_404_when_cluster_not_found(
    authenticated_client,
    monkeypatch,
):
    called = {
        'sync_inventory': False,
    }

    def fake_sync_inventory(received_cluster):
        called['sync_inventory'] = True

    monkeypatch.setattr(
        'app.inventory.routes.sync_inventory',
        fake_sync_inventory,
    )

    response = authenticated_client.post(
        '/inventory/not-found-cluster-id/sync',
    )

    assert response.status_code == 404
    assert called['sync_inventory'] is False


def test_inventory_sync_route_propagates_sync_error(
    authenticated_client,
    cluster_factory,
    monkeypatch,
):
    cluster = cluster_factory()

    def fake_sync_inventory(received_cluster):
        assert received_cluster.id == cluster.id

        raise RuntimeError('sync failed')

    monkeypatch.setattr(
        'app.inventory.routes.sync_inventory',
        fake_sync_inventory,
    )

    with pytest.raises(
        RuntimeError,
        match='sync failed',
    ):
        authenticated_client.post(
            f'/inventory/{cluster.id}/sync',
        )
