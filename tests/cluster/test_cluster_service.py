from __future__ import annotations

import pytest

from app.cluster.service import (
    build_cluster_context,
    create_cluster,
    parse_kubeconfig,
    update_cluster,
)
from app.extensions import db
from app.models import Cluster


def test_parse_kubeconfig_returns_cluster_server(app, valid_kubeconfig):
    parsed = parse_kubeconfig(valid_kubeconfig)

    assert parsed['server'] == 'https://127.0.0.1:6443'


def test_parse_kubeconfig_rejects_invalid_yaml(app):
    with pytest.raises(ValueError):
        parse_kubeconfig('invalid: [yaml')


def test_parse_kubeconfig_rejects_missing_clusters(app):
    invalid_kubeconfig = """
apiVersion: v1
kind: Config
clusters: []
contexts: []
users: []
"""

    with pytest.raises(ValueError):
        parse_kubeconfig(invalid_kubeconfig)


def test_parse_kubeconfig_rejects_missing_server(app):
    invalid_kubeconfig = """
apiVersion: v1
kind: Config
clusters:
- name: broken-cluster
  cluster: {}
contexts: []
users: []
"""

    with pytest.raises(ValueError):
        parse_kubeconfig(invalid_kubeconfig)


def test_create_cluster_from_kubeconfig_success(app, valid_kubeconfig):
    cluster = create_cluster(
        name='docker-desktop',
        environment='dev',
        description='Local Docker Desktop cluster',
        kubeconfig=valid_kubeconfig,
    )

    saved_cluster = Cluster.query.filter_by(name='docker-desktop').first()

    assert saved_cluster is not None
    assert saved_cluster.id == cluster.id
    assert saved_cluster.name == 'docker-desktop'
    assert saved_cluster.environment == 'dev'
    assert saved_cluster.description == 'Local Docker Desktop cluster'
    assert saved_cluster.kubeconfig == valid_kubeconfig
    assert saved_cluster.server == 'https://127.0.0.1:6443'
    assert saved_cluster.status == 'unknown'
    assert saved_cluster.node_count == 0


def test_create_cluster_rejects_duplicate_name(app, valid_kubeconfig):
    create_cluster(
        name='docker-desktop',
        environment='dev',
        description='First cluster',
        kubeconfig=valid_kubeconfig,
    )

    with pytest.raises(ValueError):
        create_cluster(
            name='docker-desktop',
            environment='stg',
            description='Duplicate cluster',
            kubeconfig=valid_kubeconfig,
        )


def test_update_cluster_basic_metadata_success(app, cluster_factory):
    cluster = cluster_factory(
        name='docker-desktop',
        environment='dev',
    )

    updated_cluster = update_cluster(
        cluster=cluster,
        name='docker-desktop-renamed',
        environment='stg',
        description='Updated cluster description',
    )

    db.session.refresh(updated_cluster)

    assert updated_cluster.name == 'docker-desktop-renamed'
    assert updated_cluster.environment == 'stg'
    assert updated_cluster.description == 'Updated cluster description'


def test_update_cluster_rejects_duplicate_name(app, cluster_factory):
    first_cluster = cluster_factory(
        name='cluster-a',
        environment='dev',
    )

    cluster_factory(
        name='cluster-b',
        environment='stg',
    )

    with pytest.raises(ValueError):
        update_cluster(
            cluster=first_cluster,
            name='cluster-b',
            environment='prd',
            description='Should fail because name already exists',
        )


def test_build_cluster_context_without_inventory_data(app, cluster_factory):
    cluster_a = cluster_factory(
        name='cluster-a',
        environment='dev',
    )

    cluster_b = cluster_factory(
        name='cluster-b',
        environment='stg',
    )

    cluster_a.status = 'connected'
    cluster_b.status = 'failed'

    db.session.commit()

    context = build_cluster_context()

    assert len(context['clusters']) == 2
    assert context['connected_clusters'] == 1
    assert context['synced_clusters'] == 0

    assert cluster_a.id in context['inventory_summary']
    assert cluster_b.id in context['inventory_summary']

    assert context['inventory_summary'][cluster_a.id]['version'] == '-'
    assert context['inventory_summary'][cluster_a.id]['namespaces'] == 0
    assert context['inventory_summary'][cluster_a.id]['synced_at'] is None

    assert context['inventory_summary'][cluster_b.id]['version'] == '-'
    assert context['inventory_summary'][cluster_b.id]['namespaces'] == 0
    assert context['inventory_summary'][cluster_b.id]['synced_at'] is None
