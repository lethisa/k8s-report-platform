from flask import Blueprint, render_template, request
from flask_login import login_required

from app.analytics.overview.service import (
    get_analytics_overview,
)
from app.analytics.utilization.service import (
    UtilizationService,
)
from app.models import Cluster
from app.prometheus.service import (
    PrometheusService,
)
from app.utils.formatters import (
    bytes_to_human,
)

analytics_bp = Blueprint(
    'analytics',
    __name__,
    url_prefix='/analytics',
)


@analytics_bp.route('/')
@login_required
def overview() -> str:

    analytics = get_analytics_overview()

    return render_template(
        'analytics/overview.html',
        analytics=analytics,
    )


@analytics_bp.route('/utilization')
@login_required
def utilization() -> str:

    clusters = Cluster.query.order_by(Cluster.name).all()

    cluster_id = request.args.get(
        'cluster_id',
        type=int,
    )

    cluster = None

    if cluster_id:
        cluster = Cluster.query.get(
            cluster_id,
        )

    if not cluster and clusters:
        cluster = clusters[0]

    if not cluster:
        return render_template(
            'analytics/utilization.html',
            clusters=[],
            error='No cluster configured',
            summary={},
            summary_table=[],
            trends={},
            top_cpu=[],
            top_memory=[],
        )

    summary = {}
    summary_table = []
    trends = {}
    top_cpu = []
    top_memory = []
    error = None

    try:
        prometheus = PrometheusService(
            cluster,
        )

        service = UtilizationService(
            prometheus,
        )

        summary = service.get_summary()

        memory_capacity_human = bytes_to_human(
            summary.get(
                'memory_capacity',
                0,
            )
        )

        memory_usage_human = bytes_to_human(
            summary.get(
                'memory_usage',
                0,
            )
        )

        storage_capacity_human = bytes_to_human(
            summary.get(
                'storage_capacity',
                0,
            )
        )

        storage_usage_human = bytes_to_human(
            summary.get(
                'storage_usage',
                0,
            )
        )

        summary_table = service.get_summary_table()

        trends = service.get_trends()

        top_cpu = service.get_top_cpu_consumers()

        top_memory = service.get_top_memory_consumers()

    except Exception as exc:
        error = str(exc)

    return render_template(
        'analytics/utilization.html',
        cluster=cluster,
        clusters=clusters,
        summary=summary,
        summary_table=summary_table,
        trends=trends,
        top_cpu=top_cpu,
        top_memory=top_memory,
        memory_capacity_human=memory_capacity_human,
        memory_usage_human=memory_usage_human,
        storage_capacity_human=storage_capacity_human,
        storage_usage_human=storage_usage_human,
        error=error,
    )


@analytics_bp.route('/capacity')
@login_required
def capacity() -> str:
    return render_template(
        'analytics/capacity.html',
    )


@analytics_bp.route('/forecast')
@login_required
def forecast() -> str:
    return render_template(
        'analytics/forecast.html',
    )


@analytics_bp.route('/consumers')
@login_required
def consumers() -> str:
    return render_template(
        'analytics/consumers.html',
    )


@analytics_bp.route('/anomalies')
@login_required
def anomalies() -> str:
    return render_template(
        'analytics/anomalies.html',
    )
