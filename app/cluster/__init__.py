from flask import Blueprint

from app.cluster.forms import ClusterCreateForm, ClusterEditForm
from app.cluster.service import (
    create_cluster,
    delete_cluster,
    get_cluster_summary,
    parse_kubeconfig,
    run_test_cluster,
    update_cluster,
)

cluster_bp = Blueprint('cluster', __name__, url_prefix='/clusters')


__all__ = [
    'update_cluster',
    'run_test_cluster',
    'create_cluster',
    'ClusterEditForm',
    'ClusterCreateForm',
    'parse_kubeconfig',
    'get_cluster_summary',
    'delete_cluster',
]
