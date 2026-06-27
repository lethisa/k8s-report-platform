from typing import cast

from flask import Blueprint, current_app, render_template, request
from flask_login import login_required

from app.analytics.capacity.routes import (
    capacity,
    capacity_storage,
    capacity_tenant_quota,
    capacity_workload_mapping,
)
from app.analytics.forecast import ForecastService
from app.analytics.overview.service import get_analytics_overview
from app.analytics.utilization.service import UtilizationService
from app.models import Cluster
from app.prometheus.service import PrometheusService

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
    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

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

    allowed_trend_hours = [
        1,
        3,
        6,
        12,
        24,
    ]

    try:
        trend_hours = int(
            request.args.get(
                'trend_hours',
                1,
            )
        )
    except ValueError:
        trend_hours = 1

    if trend_hours not in allowed_trend_hours:
        trend_hours = 1

    trend_step_map = {
        1: '5m',
        3: '10m',
        6: '15m',
        12: '30m',
        24: '1h',
    }

    trend_step = trend_step_map[trend_hours]

    selected_node = request.args.get(
        'node',
        '',
        type=str,
    )

    selected_filesystem_instance = request.args.get(
        'filesystem_instance',
        '',
        type=str,
    )

    selected_trend_node = request.args.get(
        'trend_node',
        '',
        type=str,
    )

    empty_summary = {
        'cpu_capacity': 0,
        'cpu_usage': 0,
        'cpu_utilization': 0,
        'memory_capacity': 0,
        'memory_usage': 0,
        'memory_utilization': 0,
        'storage_capacity': 0,
        'storage_usage': 0,
        'storage_available': 0,
        'storage_utilization': 0,
        'storage_capacity_gib': 0,
        'storage_usage_gib': 0,
        'storage_available_gib': 0,
        'pod_count': 0,
        'pod_capacity': 0,
        'pod_utilization': 0,
    }

    empty_cluster_info = {
        'kubernetes_version': '-',
        'total_nodes': 0,
        'ready_nodes': 0,
        'not_ready_nodes': 0,
        'worker_nodes': 0,
        'master_nodes': 0,
        'cpu_capacity': 0,
        'memory_capacity': 0,
        'pod_capacity': 0,
    }

    if not cluster:
        return render_template(
            'analytics/utilization.html',
            cluster=None,
            clusters=[],
            summary=empty_summary,
            summary_table=[],
            detail_summary=empty_summary,
            trends={},
            top_cpu=[],
            top_memory=[],
            error='No cluster configured',
            prometheus_connected=False,
            cluster_info=empty_cluster_info,
            risk_assessment={
                'cpu': {
                    'status': 'Normal',
                    'reason': 'No utilization data available',
                    'pressure_nodes': 0,
                    'utilization': 0,
                },
                'memory': {
                    'status': 'Normal',
                    'reason': 'No utilization data available',
                    'pressure_nodes': 0,
                    'utilization': 0,
                },
                'storage': {
                    'status': 'Normal',
                    'reason': 'No utilization data available',
                    'pressure_nodes': 0,
                    'utilization': 0,
                },
                'pods': {
                    'status': 'Normal',
                    'reason': 'No utilization data available',
                    'pressure_nodes': 0,
                    'utilization': 0,
                },
            },
            detail_risk_assessment={
                'cpu': {
                    'status': 'Normal',
                    'reason': 'No utilization data available',
                    'pressure_nodes': 0,
                    'utilization': 0,
                },
                'memory': {
                    'status': 'Normal',
                    'reason': 'No utilization data available',
                    'pressure_nodes': 0,
                    'utilization': 0,
                },
                'storage': {
                    'status': 'Normal',
                    'reason': 'No utilization data available',
                    'pressure_nodes': 0,
                    'utilization': 0,
                },
                'pods': {
                    'status': 'Normal',
                    'reason': 'No utilization data available',
                    'pressure_nodes': 0,
                    'utilization': 0,
                },
            },
            trend_hours=trend_hours,
            allowed_trend_hours=allowed_trend_hours,
            available_nodes=[],
            available_worker_nodes=[],
            available_filesystem_instances=[],
            selected_node='',
            selected_filesystem_instance='',
            selected_trend_node='',
        )

    summary = empty_summary.copy()
    cluster_info = empty_cluster_info.copy()
    summary_table = []
    detail_summary = empty_summary.copy()
    trends = {
        'cpu': [],
        'memory': [],
        'storage': [],
    }
    top_cpu = []
    top_memory = []
    available_nodes: list[str] = []
    available_worker_nodes: list[str] = []
    available_filesystem_instances: list[str] = []

    error = None
    prometheus_connected = False
    service: UtilizationService | None = None

    try:
        prometheus = PrometheusService(
            cluster,
        )

        service = UtilizationService(
            prometheus,
        )

        available_nodes = service.get_node_names()
        available_worker_nodes = service.get_worker_node_names()
        available_filesystem_instances = service.get_filesystem_instances()

        if selected_node not in available_nodes:
            selected_node = ''

        if selected_trend_node not in available_worker_nodes:
            selected_trend_node = ''

        if selected_filesystem_instance not in available_filesystem_instances:
            selected_filesystem_instance = ''

        summary = service.get_summary()

        cluster_info = service.get_cluster_info(
            summary,
        )

        summary_table = service.get_summary_table(
            summary,
        )

        detail_summary = service.get_detail_summary(
            node_name=selected_node or None,
            filesystem_instance=(selected_filesystem_instance or None),
        )

        trends = service.get_trends(
            hours=trend_hours,
            step=trend_step,
            node_name=selected_trend_node or None,
        )

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
        'cpu': {
            'status': 'Normal',
            'reason': 'No utilization data available',
            'pressure_nodes': 0,
            'utilization': 0,
        },
        'memory': {
            'status': 'Normal',
            'reason': 'No utilization data available',
            'pressure_nodes': 0,
            'utilization': 0,
        },
        'storage': {
            'status': 'Normal',
            'reason': 'No utilization data available',
            'pressure_nodes': 0,
            'utilization': 0,
        },
        'pods': {
            'status': 'Normal',
            'reason': 'No utilization data available',
            'pressure_nodes': 0,
            'utilization': 0,
        },
    }

    detail_risk_assessment = risk_assessment.copy()

    if prometheus_connected and service is not None:
        try:
            risk_assessment = service.get_capacity_pressure_risk(
                cast(
                    dict[str, int | float],
                    summary,
                ),
            )

            detail_risk_assessment = service.get_capacity_pressure_risk(
                cast(
                    dict[str, int | float],
                    detail_summary,
                ),
                selected_node or None,
            )
        except Exception as exc:
            current_app.logger.exception(
                exc,
            )

    return render_template(
        'analytics/utilization.html',
        cluster=cluster,
        clusters=clusters,
        summary=summary,
        summary_table=summary_table,
        detail_summary=detail_summary,
        trends=trends,
        top_cpu=top_cpu,
        top_memory=top_memory,
        error=error,
        prometheus_connected=prometheus_connected,
        cluster_info=cluster_info,
        risk_assessment=risk_assessment,
        detail_risk_assessment=detail_risk_assessment,
        trend_hours=trend_hours,
        allowed_trend_hours=allowed_trend_hours,
        available_nodes=available_nodes,
        available_worker_nodes=available_worker_nodes,
        available_filesystem_instances=available_filesystem_instances,
        selected_node=selected_node,
        selected_filesystem_instance=selected_filesystem_instance,
        selected_trend_node=selected_trend_node,
    )


analytics_bp.add_url_rule(
    '/capacity',
    endpoint='capacity',
    view_func=capacity,
)

analytics_bp.add_url_rule(
    '/capacity/storage',
    endpoint='capacity_storage',
    view_func=capacity_storage,
)

analytics_bp.add_url_rule(
    '/capacity/tenant-quota',
    endpoint='capacity_tenant_quota',
    view_func=capacity_tenant_quota,
)

analytics_bp.add_url_rule(
    '/capacity/workload-mapping',
    endpoint='capacity_workload_mapping',
    view_func=capacity_workload_mapping,
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
