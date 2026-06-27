from __future__ import annotations

from typing import cast

from flask import current_app, render_template, request
from flask_login import login_required

from app.analytics.utilization.service import (
    UtilizationService,
    get_selected_cluster,
    get_utilization_clusters,
)
from app.prometheus.service import PrometheusService

ALLOWED_TREND_HOURS = [
    1,
    3,
    6,
    12,
    24,
]

TREND_STEP_MAP = {
    1: '5m',
    3: '10m',
    6: '15m',
    12: '30m',
    24: '1h',
}


def _get_trend_hours() -> int:
    try:
        trend_hours = int(
            request.args.get(
                'trend_hours',
                1,
            )
        )
    except ValueError:
        return 1

    if trend_hours not in ALLOWED_TREND_HOURS:
        return 1

    return trend_hours


@login_required
def utilization_trend() -> str:
    cluster_id = request.args.get(
        'cluster_id',
    )

    cluster = get_selected_cluster(
        cluster_id,
    )

    trend_hours = _get_trend_hours()
    trend_step = TREND_STEP_MAP[trend_hours]

    selected_trend_node = request.args.get(
        'trend_node',
        '',
        type=str,
    )

    summary = _empty_summary()

    trends: dict[str, list[dict[str, float]]] = {
        'cpu': [],
        'memory': [],
        'pods': [],
    }

    available_worker_nodes: list[str] = []

    error = None

    if not cluster:
        return render_template(
            'analytics/utilization/_trend.html',
            cluster=None,
            summary=summary,
            trends=trends,
            trend_hours=trend_hours,
            allowed_trend_hours=ALLOWED_TREND_HOURS,
            available_worker_nodes=[],
            selected_trend_node='',
            error='No cluster configured',
        )

    try:
        prometheus = PrometheusService(
            cluster,
        )

        service = UtilizationService(
            prometheus,
        )

        available_worker_nodes = service.get_worker_node_names()

        if selected_trend_node not in available_worker_nodes:
            selected_trend_node = ''

        summary = service.get_summary()

        trends = service.get_trends(
            hours=trend_hours,
            step=trend_step,
            node_name=selected_trend_node or None,
        )

    except Exception as exc:
        current_app.logger.exception(
            exc,
        )

        error = (
            'Unable to retrieve utilization trend from Prometheus. '
            'Please verify endpoint, credentials, SSL configuration, '
            'and network connectivity.'
        )

    return render_template(
        'analytics/utilization/_trend.html',
        cluster=cluster,
        summary=summary,
        trends=trends,
        trend_hours=trend_hours,
        allowed_trend_hours=ALLOWED_TREND_HOURS,
        available_worker_nodes=available_worker_nodes,
        selected_trend_node=selected_trend_node,
        error=error,
    )


def _empty_summary() -> dict[str, int | float]:
    return {
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


def _empty_cluster_info() -> dict[str, int | float | str]:
    return {
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


def _empty_risk_assessment() -> dict[str, dict[str, int | float | str]]:
    return {
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


def _empty_prometheus_status() -> dict[str, bool | int | str | None]:
    return {
        'connected': False,
        'response_time_ms': None,
        'label': 'Prometheus Disconnected',
        'description': 'No successful Prometheus response.',
    }


@login_required
def utilization() -> str:
    clusters = get_utilization_clusters()

    cluster_id = request.args.get(
        'cluster_id',
    )

    cluster = get_selected_cluster(
        cluster_id,
    )

    trend_hours = _get_trend_hours()
    trend_step = TREND_STEP_MAP[trend_hours]

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

    summary = _empty_summary()
    detail_summary = _empty_summary()
    cluster_info = _empty_cluster_info()
    summary_table: list[dict[str, str | float]] = []

    trends: dict[str, list[dict[str, float]]] = {
        'cpu': [],
        'memory': [],
        'pods': [],
    }

    available_nodes: list[str] = []
    available_worker_nodes: list[str] = []
    available_filesystem_instances: list[str] = []

    risk_assessment = _empty_risk_assessment()
    detail_risk_assessment = _empty_risk_assessment()
    prometheus_status = _empty_prometheus_status()

    error = None

    if not cluster:
        return render_template(
            'analytics/utilization.html',
            cluster=None,
            clusters=[],
            summary=summary,
            summary_table=summary_table,
            detail_summary=detail_summary,
            trends=trends,
            error='No cluster configured',
            prometheus_status=prometheus_status,
            cluster_info=cluster_info,
            risk_assessment=risk_assessment,
            detail_risk_assessment=detail_risk_assessment,
            trend_hours=trend_hours,
            allowed_trend_hours=ALLOWED_TREND_HOURS,
            available_nodes=[],
            available_worker_nodes=[],
            available_filesystem_instances=[],
            selected_node='',
            selected_filesystem_instance='',
            selected_trend_node='',
            cluster_query_endpoint='analytics.utilization',
            cluster_query_hidden_params={},
        )

    try:
        prometheus = PrometheusService(
            cluster,
        )

        service = UtilizationService(
            prometheus,
        )

        prometheus_status = service.get_prometheus_status()

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
            filesystem_instance=selected_filesystem_instance or None,
        )

        trends = service.get_trends(
            hours=trend_hours,
            step=trend_step,
            node_name=selected_trend_node or None,
        )

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

        error = (
            'Unable to connect to Prometheus. '
            'Please verify endpoint, credentials, '
            'SSL configuration, and network connectivity.'
        )

    return render_template(
        'analytics/utilization.html',
        cluster=cluster,
        clusters=clusters,
        summary=summary,
        summary_table=summary_table,
        detail_summary=detail_summary,
        trends=trends,
        error=error,
        prometheus_status=prometheus_status,
        cluster_info=cluster_info,
        risk_assessment=risk_assessment,
        detail_risk_assessment=detail_risk_assessment,
        trend_hours=trend_hours,
        allowed_trend_hours=ALLOWED_TREND_HOURS,
        available_nodes=available_nodes,
        available_worker_nodes=available_worker_nodes,
        available_filesystem_instances=available_filesystem_instances,
        selected_node=selected_node,
        selected_filesystem_instance=selected_filesystem_instance,
        selected_trend_node=selected_trend_node,
        cluster_query_endpoint='analytics.utilization',
        cluster_query_hidden_params={
            'trend_hours': trend_hours,
            'trend_node': selected_trend_node,
            'node': selected_node,
            'filesystem_instance': selected_filesystem_instance,
        },
    )


@login_required
def utilization_node_detail() -> str:
    cluster_id = request.args.get(
        'cluster_id',
    )

    cluster = get_selected_cluster(
        cluster_id,
    )

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

    detail_summary = _empty_summary()
    detail_risk_assessment = _empty_risk_assessment()

    available_nodes: list[str] = []
    available_filesystem_instances: list[str] = []

    error = None

    if not cluster:
        return render_template(
            'analytics/utilization/_node_detail.html',
            cluster=None,
            detail_summary=detail_summary,
            detail_risk_assessment=detail_risk_assessment,
            available_nodes=available_nodes,
            available_filesystem_instances=available_filesystem_instances,
            selected_node='',
            selected_filesystem_instance='',
            error='No cluster configured',
        )

    try:
        prometheus = PrometheusService(
            cluster,
        )

        service = UtilizationService(
            prometheus,
        )

        available_nodes = service.get_node_names()
        available_filesystem_instances = service.get_filesystem_instances()

        if selected_node not in available_nodes:
            selected_node = ''

        if selected_filesystem_instance not in available_filesystem_instances:
            selected_filesystem_instance = ''

        detail_summary = service.get_detail_summary(
            node_name=selected_node or None,
            filesystem_instance=selected_filesystem_instance or None,
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

        error = (
            'Unable to retrieve node detail from Prometheus. '
            'Please verify endpoint, credentials, SSL configuration, '
            'and network connectivity.'
        )

    return render_template(
        'analytics/utilization/_node_detail.html',
        cluster=cluster,
        detail_summary=detail_summary,
        detail_risk_assessment=detail_risk_assessment,
        available_nodes=available_nodes,
        available_filesystem_instances=available_filesystem_instances,
        selected_node=selected_node,
        selected_filesystem_instance=selected_filesystem_instance,
        error=error,
    )
