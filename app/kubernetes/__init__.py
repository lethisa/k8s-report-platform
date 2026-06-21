from flask import Blueprint

from app.kubernetes.service import test_cluster_connection

cluster_bp = Blueprint(
    'cluster',
    __name__,
    url_prefix='/clusters',
)


__all__ = ['test_cluster_connection']
