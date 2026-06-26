from datetime import UTC, datetime

import yaml
from sqlalchemy import func

from app.extensions import db
from app.kubernetes.service import test_cluster_connection
from app.models import Cluster, ClusterInventory, ClusterStatus, NamespaceInventory


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


def get_cluster_summary():
    clusters = Cluster.query.order_by(Cluster.created_at.desc()).all()

    inventories = {inventory.cluster_id: inventory for inventory in ClusterInventory.query.all()}

    namespace_counts = {
        cluster_id: count
        for cluster_id, count in (
            db.session.query(
                NamespaceInventory.cluster_id,
                func.count(NamespaceInventory.id),
            )
            .group_by(NamespaceInventory.cluster_id)
            .all()
        )
    }

    inventory_summary = {}

    for cluster in clusters:
        inventory = inventories.get(cluster.id)

        inventory_summary[cluster.id] = {
            'version': (inventory.kubernetes_version if inventory else '-'),
            'namespaces': namespace_counts.get(
                cluster.id,
                0,
            ),
            'synced_at': (inventory.collected_at if inventory else None),
        }

    return clusters, inventory_summary


def get_cluster_by_id(cluster_id: str) -> Cluster | None:
    return db.session.get(Cluster, cluster_id)


def create_cluster(
    name: str,
    environment: str,
    kubeconfig: str,
    description: str | None = None,
):
    existing = Cluster.query.filter_by(name=name).first()

    if existing:
        raise ValueError('Cluster name already exists')

    result = parse_kubeconfig(kubeconfig)

    cluster = Cluster()

    cluster.name = name
    cluster.environment = environment
    cluster.description = description
    cluster.kubeconfig = kubeconfig
    cluster.server = result['server']

    db.session.add(cluster)
    db.session.commit()

    return cluster


def run_test_cluster(cluster: Cluster) -> dict:
    result = test_cluster_connection(cluster.kubeconfig)

    cluster.last_check = datetime.now(UTC)

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
    db.session.delete(cluster)

    db.session.commit()


def build_cluster_context():
    clusters, inventory_summary = get_cluster_summary()

    connected_clusters = sum(1 for cluster in clusters if getattr(cluster, 'status', '') == 'connected')

    synced_clusters = sum(1 for summary in inventory_summary.values() if summary.get('synced_at') is not None)

    return {
        'clusters': clusters,
        'inventory_summary': inventory_summary,
        'connected_clusters': connected_clusters,
        'synced_clusters': synced_clusters,
    }
