from flask import Blueprint, current_app, render_template, request
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
    )

    cluster = None

    if cluster_id:
        cluster = Cluster.query.filter_by(
            id=cluster_id,
        ).first()

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
            risk_assessment={
                'cpu': 'Low',
                'memory': 'Low',
                'storage': 'Low',
                'pods': 'Low',
            },
        )

    summary = {
        'cpu_capacity': 0,
        'cpu_usage': 0,
        'cpu_utilization': 0,
        'memory_capacity': 0,
        'memory_usage': 0,
        'memory_utilization': 0,
        'storage_capacity': 0,
        'storage_usage': 0,
        'storage_utilization': 0,
        'pod_count': 0,
        'pod_capacity': 0,
        'pod_utilization': 0,
    }

    cluster_info = {
        'kubernetes_version': '-',
        'total_nodes': 0,
        'worker_nodes': 0,
        'master_nodes': 0,
        'cpu_capacity': 0,
        'memory_capacity': 0,
        'pod_capacity': 0,
    }

    summary_table = []

    trends = {
        'cpu': [],
        'memory': [],
        'storage': [],
    }

    top_cpu = []
    top_memory = []

    error = None
    prometheus_connected = False

    try:
        prometheus = PrometheusService(
            cluster,
        )

        service = UtilizationService(
            prometheus,
        )

        summary = service.get_summary()

        cluster_info = service.get_cluster_info(
            summary,
        )

        summary_table = service.get_summary_table()

        trends = service.get_trends()

        top_cpu = service.get_top_cpu_consumers()

        top_memory = service.get_top_memory_consumers()

        prometheus_connected = True

    except Exception as exc:
        current_app.logger.exception(
            exc,
        )

        error = (
            'Unable to connect to Prometheus. '
            'Please verify endpoint, credentials, '
            'SSL configuration, and network connectivity.'
        )

    risk_assessment = {
        'cpu': 'Low',
        'memory': 'Low',
        'storage': 'Low',
        'pods': 'Low',
    }

    def calculate_risk(
        utilization: float,
    ) -> str:
        if utilization >= 85:
            return 'High'

        if utilization >= 70:
            return 'Medium'

        return 'Low'

    risk_assessment['cpu'] = calculate_risk(
        summary.get(
            'cpu_utilization',
            0,
        )
    )

    risk_assessment['memory'] = calculate_risk(
        summary.get(
            'memory_utilization',
            0,
        )
    )

    risk_assessment['storage'] = calculate_risk(
        summary.get(
            'storage_utilization',
            0,
        )
    )

    risk_assessment['pods'] = calculate_risk(
        summary.get(
            'pod_utilization',
            0,
        )
    )

    return render_template(
        'analytics/utilization.html',
        cluster=cluster,
        clusters=clusters,
        summary=summary,
        summary_table=summary_table,
        trends=trends,
        top_cpu=top_cpu,
        top_memory=top_memory,
        error=error,
        prometheus_connected=prometheus_connected,
        cluster_info=cluster_info,
        risk_assessment=risk_assessment,
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
