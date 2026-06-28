from datetime import UTC, datetime
from typing import Any

import yaml
from sqlalchemy import func

from app.extensions import db
from app.kubernetes.service import test_cluster_connection
from app.models import (
    AlertmanagerConfig,
    Cluster,
    ClusterInventory,
    ClusterStatus,
    NamespaceInventory,
)


def parse_kubeconfig(kubeconfig: str) -> dict[str, str]:
    try:
        parsed_config = yaml.safe_load(kubeconfig)
    except yaml.YAMLError as exc:
        raise ValueError('Invalid kubeconfig format') from exc

    if not isinstance(parsed_config, dict):
        raise ValueError('Invalid kubeconfig format')

    clusters = parsed_config.get('clusters')

    if not isinstance(clusters, list) or len(clusters) == 0:
        raise ValueError('Kubeconfig does not contain any cluster definition')

    first_cluster = clusters[0]

    if not isinstance(first_cluster, dict):
        raise ValueError('Invalid kubeconfig cluster definition')

    cluster_data = first_cluster.get('cluster')

    if not isinstance(cluster_data, dict):
        raise ValueError('Invalid kubeconfig cluster data')

    server = cluster_data.get('server')

    if not isinstance(server, str) or not server.strip():
        raise ValueError('Kubeconfig cluster server is missing')

    return {
        'server': server.strip(),
    }


def get_cluster_summary() -> tuple[list[Cluster], dict[str, dict[str, Any]]]:
    clusters = Cluster.query.order_by(
        Cluster.created_at.desc(),
    ).all()

    inventories = {inventory.cluster_id: inventory for inventory in ClusterInventory.query.all()}

    namespace_counts = {
        cluster_id: count
        for cluster_id, count in (
            db.session.query(
                NamespaceInventory.cluster_id,
                func.count(
                    NamespaceInventory.id,
                ),
            )
            .group_by(
                NamespaceInventory.cluster_id,
            )
            .all()
        )
    }

    inventory_summary: dict[str, dict[str, Any]] = {}

    for cluster in clusters:
        inventory = inventories.get(
            cluster.id,
        )

        inventory_summary[cluster.id] = {
            'version': inventory.kubernetes_version if inventory else '-',
            'namespaces': namespace_counts.get(
                cluster.id,
                0,
            ),
            'synced_at': inventory.collected_at if inventory else None,
        }

    return clusters, inventory_summary


def get_alertmanager_summary() -> dict[str, dict[str, Any]]:
    configs = AlertmanagerConfig.query.all()
    summary: dict[str, dict[str, Any]] = {}

    for config in configs:
        summary[config.cluster_id] = {
            'configured': bool(
                config.endpoint,
            ),
            'connected': config.last_status == 'connected',
            'status': config.last_status or 'configured',
            'label': config.display_status,
            'response_time_ms': config.last_response_time_ms,
            'last_checked_at': config.last_checked_at,
            'error': config.last_error,
        }

    return summary


def get_prometheus_summary(
    clusters: list[Cluster],
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}

    for cluster in clusters:
        config = getattr(
            cluster,
            'prometheus_config',
            None,
        )

        if config is None:
            summary[cluster.id] = {
                'configured': False,
                'label': 'Not Set',
                'endpoint': None,
            }
            continue

        summary[cluster.id] = {
            'configured': bool(
                getattr(
                    config,
                    'endpoint',
                    None,
                )
            ),
            'label': 'Configured'
            if getattr(
                config,
                'endpoint',
                None,
            )
            else 'Not Set',
            'endpoint': getattr(
                config,
                'endpoint',
                None,
            ),
        }

    return summary


def get_cluster_by_id(cluster_id: str) -> Cluster | None:
    return db.session.get(
        Cluster,
        cluster_id,
    )


def create_cluster(
    name: str,
    environment: str,
    kubeconfig: str,
    description: str | None = None,
) -> Cluster:
    existing = Cluster.query.filter_by(
        name=name,
    ).first()

    if existing:
        raise ValueError('Cluster name already exists')

    result = parse_kubeconfig(
        kubeconfig,
    )

    cluster = Cluster()

    cluster.name = name
    cluster.environment = environment
    cluster.description = description
    cluster.kubeconfig = kubeconfig
    cluster.server = result['server']

    db.session.add(
        cluster,
    )
    db.session.commit()

    return cluster


def run_test_cluster(cluster: Cluster) -> dict[str, Any]:
    result = test_cluster_connection(
        cluster.kubeconfig,
    )

    cluster.last_check = datetime.now(
        UTC,
    )

    if result['success']:
        cluster.status = ClusterStatus.CONNECTED.value

        cluster.node_count = result.get(
            'node_count',
            0,
        )

    else:
        cluster.status = ClusterStatus.FAILED.value

    db.session.commit()

    return result


def update_cluster(
    *,
    cluster: Cluster,
    name: str,
    environment: str,
    description: str | None,
) -> Cluster:
    existing = Cluster.query.filter(
        Cluster.name == name,
        Cluster.id != cluster.id,
    ).first()

    if existing:
        raise ValueError('Cluster name already exists')

    cluster.name = name
    cluster.environment = environment
    cluster.description = description

    db.session.commit()

    return cluster


def delete_cluster(cluster: Cluster) -> None:
    db.session.delete(
        cluster,
    )

    db.session.commit()


def build_cluster_context() -> dict[str, Any]:
    clusters, inventory_summary = get_cluster_summary()

    connected_clusters = sum(
        1
        for cluster in clusters
        if getattr(
            cluster,
            'status',
            '',
        )
        == 'connected'
    )

    synced_clusters = sum(
        1
        for summary in inventory_summary.values()
        if summary.get(
            'synced_at',
        )
        is not None
    )

    return {
        'clusters': clusters,
        'inventory_summary': inventory_summary,
        'prometheus_summary': get_prometheus_summary(
            clusters,
        ),
        'alertmanager_summary': get_alertmanager_summary(),
        'connected_clusters': connected_clusters,
        'synced_clusters': synced_clusters,
    }
