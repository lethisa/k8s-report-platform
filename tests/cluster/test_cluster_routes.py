from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

from app.extensions import db
from app.models import Cluster


def test_cluster_list_requires_login(client):
    response = client.get('/clusters/')

    assert response.status_code in [302, 401]


def test_authenticated_user_can_open_cluster_list(authenticated_client):
    response = authenticated_client.get('/clusters/')

    assert response.status_code == 200
    assert b'Cluster Management' in response.data
    assert b'Cluster Inventory' in response.data


def test_authenticated_user_can_open_add_cluster_page(authenticated_client):
    response = authenticated_client.get('/clusters/add')

    assert response.status_code == 200
    assert b'Add Cluster' in response.data


def test_authenticated_user_can_add_cluster(
    authenticated_client,
    valid_kubeconfig,
):
    response = authenticated_client.post(
        '/clusters/add',
        data={
            'name': 'docker-desktop',
            'environment': 'dev',
            'description': 'Local test cluster',
            'kubeconfig': (
                BytesIO(valid_kubeconfig.encode('utf-8')),
                'kubeconfig.yaml',
            ),
        },
        content_type='multipart/form-data',
        follow_redirects=True,
    )

    cluster = Cluster.query.filter_by(name='docker-desktop').first()

    assert response.status_code == 200
    assert cluster is not None
    assert cluster.environment == 'dev'
    assert b'Cluster Management' in response.data


def test_authenticated_user_can_open_edit_cluster_page(
    authenticated_client,
    cluster_factory,
):
    cluster = cluster_factory(
        name='docker-desktop',
        environment='dev',
    )

    response = authenticated_client.get(f'/clusters/{cluster.id}/edit')

    assert response.status_code == 200
    assert b'Edit Cluster' in response.data
    assert b'docker-desktop' in response.data


def test_authenticated_user_can_update_cluster(
    authenticated_client,
    cluster_factory,
):
    cluster = cluster_factory(
        name='docker-desktop',
        environment='dev',
    )

    response = authenticated_client.post(
        f'/clusters/{cluster.id}/edit',
        data={
            'name': 'docker-desktop-renamed',
            'environment': 'stg',
            'description': 'Updated from route test',
        },
        follow_redirects=True,
    )

    updated_cluster = db.session.get(Cluster, cluster.id)

    assert response.status_code == 200
    assert updated_cluster is not None
    assert updated_cluster.name == 'docker-desktop-renamed'
    assert updated_cluster.environment == 'stg'
    assert b'Cluster Management' in response.data


def test_authenticated_user_can_delete_cluster(
    authenticated_client,
    cluster_factory,
):
    cluster = cluster_factory(
        name='docker-desktop',
        environment='dev',
    )

    cluster_id = cluster.id

    response = authenticated_client.post(
        f'/clusters/{cluster_id}/delete',
        follow_redirects=True,
    )

    deleted_cluster = db.session.get(Cluster, cluster_id)

    assert response.status_code == 200
    assert deleted_cluster is None
    assert b'Cluster Management' in response.data


def test_test_connection_route_updates_cluster_status_and_returns_table_partial(
    authenticated_client,
    cluster_factory,
):
    cluster = cluster_factory(
        name='docker-desktop',
        environment='dev',
    )

    with patch(
        'app.cluster.service.test_cluster_connection',
        return_value={
            'success': True,
            'node_count': 3,
        },
    ):
        response = authenticated_client.post(
            f'/clusters/{cluster.id}/test',
            headers={
                'HX-Request': 'true',
            },
        )

    updated_cluster = db.session.get(Cluster, cluster.id)

    assert response.status_code == 200
    assert updated_cluster is not None
    assert updated_cluster.status == 'connected'
    assert updated_cluster.node_count == 3

    assert b'id="cluster-table-container"' in response.data
    assert b'x-model="search"' in response.data
    assert b'x-model="envFilter"' in response.data
