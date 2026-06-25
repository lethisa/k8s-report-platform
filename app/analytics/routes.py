from flask import Blueprint, current_app, render_template, request
from flask_login import login_required

from app.analytics.capacity.service import (
    CapacityService,
)
from app.analytics.forecast import (
    ForecastService,
)
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


@analytics_bp.route(
    '/capacity',
)
@login_required
def capacity():
    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    cluster_id = request.args.get(
        'cluster_id',
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
            'analytics/capacity.html',
            clusters=[],
            capacity_summary={},
        )

    prometheus = PrometheusService(
        cluster,
    )

    utilization_service = UtilizationService(
        prometheus,
    )

    capacity_service = CapacityService(
        utilization_service,
    )

    summary = utilization_service.get_summary()

    cluster_info = utilization_service.get_cluster_info(
        summary,
    )

    capacity_summary = capacity_service.get_capacity_summary()

    capacity_assessment = {}

    for resource, item in capacity_summary.items():
        headroom = item.get(
            'headroom',
            0,
        )

        if headroom < 15:
            status = 'Critical'

        elif headroom < 30:
            status = 'Warning'

        else:
            status = 'Healthy'

        capacity_assessment[resource] = {
            'status': status,
            'headroom': headroom,
        }

    resource_ranking = sorted(
        [
            {
                'resource': resource,
                'headroom': item.get(
                    'headroom',
                    0,
                ),
            }
            for resource, item in capacity_summary.items()
        ],
        key=lambda x: x['headroom'],
    )

    recommendations = []

    for resource, item in capacity_summary.items():
        headroom = item.get(
            'headroom',
            0,
        )

        if headroom < 15:
            recommendations.append(f'{resource.title()} capacity is critical ' f'({headroom:.1f}% headroom remaining).')

        elif headroom < 30:
            recommendations.append(
                f'{resource.title()} capacity is running low ' f'({headroom:.1f}% headroom remaining).'
            )

        elif headroom < 50:
            recommendations.append(f'Monitor {resource} growth trends. ' f'Current headroom is ' f'{headroom:.1f}%.')

    if not recommendations:
        recommendations.append('All cluster resources currently have healthy capacity headroom.')

    return render_template(
        'analytics/capacity.html',
        clusters=clusters,
        cluster=cluster,
        cluster_info=cluster_info,
        capacity_summary=capacity_summary,
        capacity_assessment=capacity_assessment,
        resource_ranking=resource_ranking,
        recommendations=recommendations,
        capacity_chart={
            'cpu': {
                'used': capacity_summary['cpu']['used'],
                'available': capacity_summary['cpu']['available'],
            },
            'memory': {
                'used': capacity_summary['memory']['used'],
                'available': capacity_summary['memory']['available'],
            },
            'storage': {
                'used': capacity_summary['storage']['used'],
                'available': capacity_summary['storage']['available'],
            },
            'pods': {
                'used': capacity_summary['pods']['used'],
                'available': capacity_summary['pods']['available'],
            },
        },
    )


@analytics_bp.route(
    '/forecast',
)
@login_required
def forecast():
    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    cluster_id = request.args.get(
        'cluster_id',
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
            'analytics/forecast.html',
            clusters=[],
            forecast_summary={},
            error='No cluster configured',
        )

    try:
        prometheus = PrometheusService(
            cluster,
        )

        utilization_service = UtilizationService(
            prometheus,
        )

        forecast_service = ForecastService(
            utilization_service,
        )

        forecast_summary = forecast_service.get_forecast_summary()
        forecast_insights = forecast_service.get_insights()
        projection_data = forecast_service.get_projection_chart_data()

        error = None

    except Exception as exc:
        current_app.logger.exception(
            exc,
        )

        forecast_summary = {}

        projection_data = {
            'labels': [],
            'historical': [],
            'projection_labels': [],
            'projected': [],
        }

        forecast_insights = []

        error = (
            'Unable to connect to Prometheus. '
            'Please verify endpoint, credentials, '
            'SSL configuration, and network connectivity.'
        )

    return render_template(
        'analytics/forecast.html',
        clusters=clusters,
        cluster=cluster,
        forecast_summary=forecast_summary,
        projection_data=projection_data,
        forecast_insights=forecast_insights,
        error=error,
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
