from app.models.cluster import Cluster
from app.models.inventory import NodeInventory


def get_dashboard_summary() -> dict[str, int]:

    return {
        'cluster_count': Cluster.query.count(),
        'node_count': NodeInventory.query.count(),
        'namespace_count': 0,
    }


def get_cluster_health() -> dict[str, int]:

    return {
        'healthy': 0,
        'warning': 0,
        'critical': 0,
        'unknown': 0,
    }


def get_recent_activities() -> list[dict[str, str]]:

    return []
