# app/analytics/capacity/service.py

from __future__ import annotations

import re
import time
from collections.abc import Mapping
from typing import Any

from flask import current_app

from app.analytics.capacity import queries
from app.analytics.common.base_service import (
    AnalyticsBaseService,
    bytes_to_gib,
    raw_percent,
    safe_percent,
    safe_round,
)
from app.analytics.utilization.service import UtilizationService
from app.models import Cluster
from app.prometheus.service import PrometheusService

REQUIRED_QUOTA_KEYS = [
    'requests.cpu',
    'limits.cpu',
    'requests.memory',
    'limits.memory',
    'pods',
]


ALLOWED_TIME_RANGE_VALUES = [
    '1h',
    '6h',
    '24h',
    '7d',
]

ALLOWED_PER_PAGE_VALUES = [
    5,
    10,
    25,
    50,
]


def get_query_value(
    query_args: Mapping[str, Any],
    name: str,
    default: str = '',
) -> str:
    value = query_args.get(
        name,
        default,
    )

    if value is None:
        return default

    return str(
        value,
    )


def get_positive_int_arg(
    query_args: Mapping[str, Any],
    name: str,
    default: int,
) -> int:
    raw_value = query_args.get(
        name,
        default,
    )

    try:
        value = int(
            raw_value,
        )
    except (
        TypeError,
        ValueError,
    ):
        return default

    if value < 1:
        return default

    return value


def get_per_page_arg(
    query_args: Mapping[str, Any],
    name: str,
    default: int = 10,
) -> int:
    value = get_positive_int_arg(
        query_args=query_args,
        name=name,
        default=default,
    )

    if value not in ALLOWED_PER_PAGE_VALUES:
        return default

    return value


def get_selected_time_range(
    query_args: Mapping[str, Any],
) -> str:
    selected_time_range = get_query_value(
        query_args=query_args,
        name='time_range',
        default='24h',
    )

    if selected_time_range not in ALLOWED_TIME_RANGE_VALUES:
        return '24h'

    return selected_time_range


def get_empty_capacity_payload(
    selected_namespace: str,
    selected_time_range: str,
) -> dict[str, Any]:
    empty_pagination = {
        'page': 1,
        'per_page': 10,
        'total_items': 0,
        'total_pages': 1,
        'start_item': 0,
        'end_item': 0,
        'has_previous': False,
        'has_next': False,
        'previous_page': 1,
        'next_page': 1,
        'per_page_options': ALLOWED_PER_PAGE_VALUES,
    }

    return {
        'cluster_info': {
            'kubernetes_version': '-',
            'total_nodes': 0,
            'ready_nodes': 0,
            'not_ready_nodes': 0,
            'worker_nodes': 0,
            'master_nodes': 0,
            'cpu_capacity': 0,
            'memory_capacity': 0,
            'pod_capacity': 0,
        },
        'capacity_summary': {
            'cpu': {
                'capacity': 0,
                'used': 0,
                'available': 0,
                'headroom': 0,
            },
            'memory': {
                'capacity': 0,
                'used': 0,
                'available': 0,
                'headroom': 0,
            },
            'storage': {
                'capacity': 0,
                'used': 0,
                'available': 0,
                'headroom': 0,
            },
            'pods': {
                'capacity': 0,
                'used': 0,
                'available': 0,
                'headroom': 0,
            },
        },
        'allocation_summary': {
            'cpu': {
                'title': 'CPU',
                'status': {
                    'label': 'Unknown',
                    'class': 'bg-slate-100 text-slate-700',
                },
                'items': [],
            },
            'memory': {
                'title': 'Memory',
                'status': {
                    'label': 'Unknown',
                    'class': 'bg-slate-100 text-slate-700',
                },
                'items': [],
            },
            'pods': {
                'title': 'Pods',
                'status': {
                    'label': 'Unknown',
                    'class': 'bg-slate-100 text-slate-700',
                },
                'items': [],
            },
        },
        'storage_summary': {
            'node_filesystem': {
                'selected_node': '',
                'available_nodes': [],
                'summary': {
                    'capacity': '-',
                    'used': '-',
                    'free': '-',
                    'usage_percent': 0,
                    'free_percent': 0,
                    'highest_usage': 0,
                    'highest_node': '-',
                },
                'rows': [],
            },
            'persistent_storage': {
                'pv': {
                    'count': 0,
                    'capacity': '-',
                    'used': '-',
                    'free': '-',
                    'used_percent': 0,
                    'free_percent': 0,
                },
                'pvc': {
                    'count': 0,
                    'requested': '-',
                    'used': '-',
                    'free': '-',
                    'used_percent': 0,
                    'free_percent': 0,
                },
                'pvc_rows': [],
                'pvc_pagination': empty_pagination,
                'pvc_status_options': [],
                'pvc_storage_class_options': [],
                'pvc_selected_status': '',
                'pvc_selected_storage_class': '',
                'pv_rows': [],
                'pv_pagination': empty_pagination,
                'pv_status_options': [],
                'pv_storage_class_options': [],
                'pv_selected_status': '',
                'pv_selected_storage_class': '',
            },
        },
        'tenant_quota_summary': {
            'summary_cards': [],
            'rows': [],
            'pagination': empty_pagination,
        },
        'tenant_quota_rows': [],
        'workload_mapping_payload': {
            'rows': [],
            'filters': {},
            'pagination': empty_pagination,
        },
        'workload_mapping_rows': [],
        'namespace_options': [],
        'quota_coverage': {
            'total_namespaces': 0,
            'quota_namespaces': 0,
            'coverage_percent': 0,
        },
        'risk_summary': [],
        'governance_findings': [
            {
                'label': 'No capacity data available',
                'severity': 'warning',
                'icon': 'triangle-alert',
            },
        ],
        'recommendation_cards': [
            {
                'title': 'Connect Prometheus Metrics',
                'description': (
                    'Capacity analysis requires Prometheus and kube-state-metrics '
                    'to compare quota, requests, limits, and actual usage.'
                ),
                'icon': 'plug-zap',
                'icon_class': 'bg-amber-100 text-amber-600',
            },
        ],
        'kpi_cards': [],
        'selected_namespace': selected_namespace,
        'selected_storage_node': '',
        'selected_storage_tab': 'pvc',
        'selected_pvc_search': '',
        'selected_pvc_status': '',
        'selected_pvc_storage_class': '',
        'selected_pv_search': '',
        'selected_pv_status': '',
        'selected_pv_storage_class': '',
        'selected_time_range': selected_time_range,
        'allowed_time_ranges': [
            {
                'label': 'Last 1 Hour',
                'value': '1h',
            },
            {
                'label': 'Last 6 Hours',
                'value': '6h',
            },
            {
                'label': 'Last 24 Hours',
                'value': '24h',
            },
            {
                'label': 'Last 7 Days',
                'value': '7d',
            },
        ],
    }


def get_selected_cluster(
    clusters: list[Cluster],
    cluster_id: str,
) -> Cluster | None:
    if cluster_id:
        cluster = Cluster.query.filter_by(
            id=cluster_id,
        ).first()

        if cluster:
            return cluster

    if clusters:
        return clusters[0]

    return None


def get_capacity_page_context(
    query_args: Mapping[str, Any],
) -> dict[str, Any]:
    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    selected_namespace = get_query_value(
        query_args=query_args,
        name='namespace',
        default='',
    )

    selected_time_range = get_selected_time_range(
        query_args=query_args,
    )

    cluster_id = get_query_value(
        query_args=query_args,
        name='cluster_id',
        default='',
    )

    quota_page = get_positive_int_arg(
        query_args=query_args,
        name='quota_page',
        default=1,
    )

    quota_per_page = get_per_page_arg(
        query_args=query_args,
        name='quota_per_page',
        default=10,
    )

    workload_page = get_positive_int_arg(
        query_args=query_args,
        name='workload_page',
        default=1,
    )

    workload_per_page = get_per_page_arg(
        query_args=query_args,
        name='workload_per_page',
        default=10,
    )

    selected_storage_tab = get_query_value(
        query_args=query_args,
        name='storage_tab',
        default='pvc',
    )

    if selected_storage_tab not in [
        'pvc',
        'pv',
    ]:
        selected_storage_tab = 'pvc'

    selected_pvc_search = get_query_value(
        query_args=query_args,
        name='pvc_search',
        default='',
    )

    selected_pvc_status = get_query_value(
        query_args=query_args,
        name='pvc_status',
        default='',
    )

    selected_pvc_storage_class = get_query_value(
        query_args=query_args,
        name='pvc_storage_class',
        default='',
    )

    pvc_page = get_positive_int_arg(
        query_args=query_args,
        name='pvc_page',
        default=1,
    )

    pvc_per_page = get_per_page_arg(
        query_args=query_args,
        name='pvc_per_page',
        default=10,
    )

    selected_pv_search = get_query_value(
        query_args=query_args,
        name='pv_search',
        default='',
    )

    selected_pv_status = get_query_value(
        query_args=query_args,
        name='pv_status',
        default='',
    )

    selected_pv_storage_class = get_query_value(
        query_args=query_args,
        name='pv_storage_class',
        default='',
    )

    pv_page = get_positive_int_arg(
        query_args=query_args,
        name='pv_page',
        default=1,
    )

    pv_per_page = get_per_page_arg(
        query_args=query_args,
        name='pv_per_page',
        default=10,
    )

    selected_storage_node = get_query_value(
        query_args=query_args,
        name='storage_node',
        default='',
    )

    cluster = get_selected_cluster(
        clusters=clusters,
        cluster_id=cluster_id,
    )

    empty_capacity_payload = get_empty_capacity_payload(
        selected_namespace=selected_namespace,
        selected_time_range=selected_time_range,
    )

    if not cluster:
        return {
            'clusters': [],
            'cluster': None,
            'error': 'No cluster configured',
            'prometheus_connected': False,
            **empty_capacity_payload,
        }

    error = None
    prometheus_connected = False
    prometheus_status = {
        'connected': False,
        'response_time_ms': None,
        'label': 'Prometheus Disconnected',
        'description': 'Prometheus unavailable',
    }
    capacity_payload = empty_capacity_payload.copy()

    try:
        prometheus = PrometheusService(
            cluster,
        )

        utilization_service = UtilizationService(
            prometheus,
        )

        capacity_service = CapacityService(
            utilization_service,
        )

        prometheus_status = capacity_service.get_prometheus_status()

        capacity_payload = capacity_service.get_capacity_analysis(
            selected_namespace=selected_namespace,
            time_range=selected_time_range,
            selected_storage_node=selected_storage_node,
            quota_page=quota_page,
            quota_per_page=quota_per_page,
            workload_page=workload_page,
            workload_per_page=workload_per_page,
            selected_storage_tab=selected_storage_tab,
            selected_pvc_search=selected_pvc_search,
            selected_pvc_status=selected_pvc_status,
            selected_pvc_storage_class=selected_pvc_storage_class,
            pvc_page=pvc_page,
            pvc_per_page=pvc_per_page,
            selected_pv_search=selected_pv_search,
            selected_pv_status=selected_pv_status,
            selected_pv_storage_class=selected_pv_storage_class,
            pv_page=pv_page,
            pv_per_page=pv_per_page,
        )

        prometheus_connected = True

    except Exception as exc:
        current_app.logger.exception(
            exc,
        )

        error = (
            'Unable to connect to Prometheus. '
            'Please verify endpoint, credentials, SSL configuration, '
            'and network connectivity.'
        )

    return {
        'clusters': clusters,
        'cluster': cluster,
        'error': error,
        'prometheus_connected': prometheus_connected,
        'prometheus_status': prometheus_status,
        **capacity_payload,
    }


class CapacityService(AnalyticsBaseService):
    def __init__(
        self,
        utilization_service: UtilizationService,
    ) -> None:
        self.utilization_service = utilization_service

    def get_capacity_analysis(
        self,
        selected_namespace: str = '',
        time_range: str = '24h',
        selected_storage_node: str = '',
        quota_page: int = 1,
        quota_per_page: int = 10,
        workload_page: int = 1,
        workload_per_page: int = 10,
        selected_storage_tab: str = 'pvc',
        selected_pvc_search: str = '',
        selected_pvc_status: str = '',
        selected_pvc_storage_class: str = '',
        pvc_page: int = 1,
        pvc_per_page: int = 10,
        selected_pv_search: str = '',
        selected_pv_status: str = '',
        selected_pv_storage_class: str = '',
        pv_page: int = 1,
        pv_per_page: int = 10,
    ) -> dict[str, Any]:
        summary = self.utilization_service.get_summary()

        cluster_info = self.utilization_service.get_cluster_info(
            summary,
        )

        capacity_summary = self.get_capacity_summary_from_summary(
            summary,
        )

        allocation_summary = self.get_cluster_allocation_summary(
            summary=summary,
            time_range=time_range,
        )

        worker_capacity_summary = self.get_worker_capacity_summary(
            cluster_info=cluster_info,
            capacity_summary=capacity_summary,
        )

        namespace_options = self.get_all_namespace_options()

        risk_summary = self.get_capacity_risk_summary(
            capacity_summary=capacity_summary,
        )

        governance_findings = self.get_capacity_governance_findings(
            capacity_summary=capacity_summary,
        )

        recommendation_cards = self.get_capacity_recommendation_cards(
            capacity_summary=capacity_summary,
        )

        kpi_cards = self.get_kpi_cards(
            cluster_info=cluster_info,
            capacity_summary=capacity_summary,
        )

        return {
            'cluster_info': cluster_info,
            'capacity_summary': capacity_summary,
            'worker_capacity_summary': worker_capacity_summary,
            'allocation_summary': allocation_summary,
            'storage_summary': {},
            'tenant_quota_summary': {
                'summary_cards': [],
                'rows': [],
                'pagination': {},
            },
            'tenant_quota_rows': [],
            'quota_status_options': [],
            'tenant_risk_options': [],
            'workload_mapping_payload': {
                'rows': [],
                'filters': {},
                'pagination': {},
                'workload_type_options': [],
                'resource_status_options': [],
                'qos_options': [],
                'risk_options': [],
            },
            'workload_mapping_rows': [],
            'namespace_options': namespace_options,
            'quota_coverage': {
                'total_namespaces': len(
                    namespace_options,
                ),
                'quota_namespaces': 0,
                'coverage_percent': 0,
            },
            'risk_summary': risk_summary,
            'governance_findings': governance_findings,
            'recommendation_cards': recommendation_cards,
            'kpi_cards': kpi_cards,
            'selected_namespace': selected_namespace,
            'selected_storage_node': selected_storage_node,
            'selected_storage_tab': selected_storage_tab,
            'selected_pvc_search': selected_pvc_search,
            'selected_pvc_status': selected_pvc_status,
            'selected_pvc_storage_class': selected_pvc_storage_class,
            'selected_pv_search': selected_pv_search,
            'selected_pv_status': selected_pv_status,
            'selected_pv_storage_class': selected_pv_storage_class,
            'selected_time_range': time_range,
            'allowed_time_ranges': self.get_allowed_time_ranges(),
        }

    def get_allowed_time_ranges(
        self,
    ) -> list[dict[str, str]]:
        return [
            {
                'label': 'Last 1 Hour',
                'value': '1h',
            },
            {
                'label': 'Last 6 Hours',
                'value': '6h',
            },
            {
                'label': 'Last 24 Hours',
                'value': '24h',
            },
            {
                'label': 'Last 7 Days',
                'value': '7d',
            },
        ]

    def build_range_query(
        self,
        query_template: str,
        time_range: str,
    ) -> str:
        return query_template.replace(
            '__TIME_RANGE__',
            time_range,
        )

    def get_capacity_summary_from_summary(
        self,
        summary: dict[str, Any],
    ) -> dict[str, dict[str, float]]:
        cpu_capacity = self.to_float(
            summary.get(
                'cpu_capacity',
                0,
            )
        )

        cpu_usage = self.to_float(
            summary.get(
                'cpu_usage',
                0,
            )
        )

        memory_capacity = self.to_float(
            summary.get(
                'memory_capacity',
                0,
            )
        )

        memory_usage = self.to_float(
            summary.get(
                'memory_usage',
                0,
            )
        )

        pod_capacity = self.to_float(
            summary.get(
                'pod_capacity',
                0,
            )
        )

        pod_usage = self.to_float(
            summary.get(
                'pod_count',
                0,
            )
        )

        cpu_available = max(
            cpu_capacity - cpu_usage,
            0,
        )

        memory_available = max(
            memory_capacity - memory_usage,
            0,
        )

        pod_available = max(
            pod_capacity - pod_usage,
            0,
        )

        return {
            'cpu': {
                'capacity': safe_round(
                    cpu_capacity,
                ),
                'used': safe_round(
                    cpu_usage,
                ),
                'available': safe_round(
                    cpu_available,
                ),
                'headroom': safe_percent(
                    cpu_available,
                    cpu_capacity,
                ),
            },
            'memory': {
                'capacity': bytes_to_gib(
                    memory_capacity,
                ),
                'used': bytes_to_gib(
                    memory_usage,
                ),
                'available': bytes_to_gib(
                    memory_available,
                ),
                'headroom': safe_percent(
                    memory_available,
                    memory_capacity,
                ),
            },
            'pods': {
                'capacity': safe_round(
                    pod_capacity,
                    0,
                ),
                'used': safe_round(
                    pod_usage,
                    0,
                ),
                'available': safe_round(
                    pod_available,
                    0,
                ),
                'headroom': safe_percent(
                    pod_available,
                    pod_capacity,
                ),
            },
            # Backward-compatible key for old template only.
            'storage': {
                'capacity': 0,
                'used': 0,
                'available': 0,
                'headroom': 0,
            },
        }

    def get_worker_capacity_summary(
        self,
        cluster_info: dict[str, Any],
        capacity_summary: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        return {
            'title': 'Worker Capacity Summary',
            'subtitle': (
                'Schedulable capacity is calculated from Ready worker nodes. '
                'Control-plane nodes are shown for context only.'
            ),
            'cards': self.get_kpi_cards(
                cluster_info=cluster_info,
                capacity_summary=capacity_summary,
            ),
        }

    def get_kpi_cards(
        self,
        cluster_info: dict[str, Any],
        capacity_summary: dict[str, dict[str, float]],
    ) -> list[dict[str, Any]]:
        return [
            {
                'label': 'Worker Nodes',
                'value': cluster_info.get(
                    'worker_nodes',
                    0,
                ),
                'caption': (
                    f"{cluster_info.get('ready_nodes', 0)} Ready, "
                    f"{cluster_info.get('not_ready_nodes', 0)} Not Ready"
                ),
                'footer': (
                    f"Total nodes {cluster_info.get('total_nodes', 0)} · "
                    f"Control-plane {cluster_info.get('master_nodes', 0)}"
                ),
                'icon': 'users',
                'icon_class': 'bg-blue-100 text-blue-600',
            },
            {
                'label': 'Allocatable CPU',
                'value': f"{capacity_summary['cpu']['capacity']} cores",
                'caption': 'Ready worker nodes only',
                'footer': '',
                'icon': 'cpu',
                'icon_class': 'bg-emerald-100 text-emerald-600',
            },
            {
                'label': 'Allocatable Memory',
                'value': f"{capacity_summary['memory']['capacity']} GiB",
                'caption': 'Ready worker nodes only',
                'footer': '',
                'icon': 'memory-stick',
                'icon_class': 'bg-violet-100 text-violet-600',
            },
            {
                'label': 'Pod Capacity',
                'value': f"{int(capacity_summary['pods']['capacity'])} pods",
                'caption': 'Ready worker nodes only',
                'footer': '',
                'icon': 'box',
                'icon_class': 'bg-cyan-100 text-cyan-600',
            },
        ]

    def get_cluster_allocation_summary(
        self,
        summary: dict[str, Any],
        time_range: str,
    ) -> dict[str, dict[str, Any]]:
        cpu_allocatable = self.to_float(
            summary.get(
                'cpu_capacity',
                0,
            )
        )

        memory_allocatable_bytes = self.to_float(
            summary.get(
                'memory_capacity',
                0,
            )
        )

        pod_capacity = self.to_float(
            summary.get(
                'pod_capacity',
                0,
            )
        )

        cpu_actual = self.to_float(
            summary.get(
                'cpu_usage',
                0,
            )
        )

        memory_actual_bytes = self.to_float(
            summary.get(
                'memory_usage',
                0,
            )
        )

        current_pods = self.get_prometheus_scalar(
            queries.CURRENT_PODS_QUERY,
        )

        if not current_pods:
            current_pods = self.to_float(
                summary.get(
                    'pod_count',
                    0,
                )
            )

        cpu_requests = self.get_prometheus_scalar(
            queries.CPU_REQUESTS_TOTAL_QUERY,
        )

        cpu_limits = self.get_prometheus_scalar(
            queries.CPU_LIMITS_TOTAL_QUERY,
        )

        memory_requests_bytes = self.get_prometheus_scalar(
            queries.MEMORY_REQUESTS_TOTAL_QUERY,
        )

        memory_limits_bytes = self.get_prometheus_scalar(
            queries.MEMORY_LIMITS_TOTAL_QUERY,
        )

        cpu_peak = self.get_prometheus_scalar(
            self.build_range_query(
                queries.CPU_PEAK_QUERY_TEMPLATE,
                time_range,
            ),
        )

        memory_peak_bytes = self.get_prometheus_scalar(
            self.build_range_query(
                queries.MEMORY_PEAK_QUERY_TEMPLATE,
                time_range,
            ),
        )

        if not cpu_peak:
            cpu_peak = cpu_actual

        if not memory_peak_bytes:
            memory_peak_bytes = memory_actual_bytes

        pod_remaining = max(
            pod_capacity - current_pods,
            0,
        )

        return {
            'cpu': {
                'title': 'CPU',
                'unit': 'cores',
                'status': self.get_allocation_status(
                    requested=cpu_limits,
                    allocatable=cpu_allocatable,
                    resource='cpu',
                ),
                'items': self.build_cpu_allocation_items(
                    allocatable=cpu_allocatable,
                    requests=cpu_requests,
                    limits=cpu_limits,
                    actual=cpu_actual,
                    peak=cpu_peak,
                ),
            },
            'memory': {
                'title': 'Memory',
                'unit': 'GiB',
                'status': self.get_allocation_status(
                    requested=memory_limits_bytes,
                    allocatable=memory_allocatable_bytes,
                    resource='memory',
                ),
                'items': self.build_memory_allocation_items(
                    allocatable_bytes=memory_allocatable_bytes,
                    requests_bytes=memory_requests_bytes,
                    limits_bytes=memory_limits_bytes,
                    actual_bytes=memory_actual_bytes,
                    peak_bytes=memory_peak_bytes,
                ),
            },
            'pods': {
                'title': 'Pods',
                'unit': 'pods',
                'status': self.get_allocation_status(
                    requested=current_pods,
                    allocatable=pod_capacity,
                    resource='pods',
                ),
                'items': self.build_pod_allocation_items(
                    capacity=pod_capacity,
                    current=current_pods,
                    remaining=pod_remaining,
                ),
            },
        }

    def build_cpu_allocation_items(
        self,
        allocatable: float,
        requests: float,
        limits: float,
        actual: float,
        peak: float,
    ) -> list[dict[str, Any]]:
        return [
            {
                'label': 'Allocatable',
                'display': f'{safe_round(allocatable)} cores (100%)',
                'percent': 100,
                'bar_class': 'bg-slate-300',
            },
            {
                'label': 'Configured Requests',
                'display': (f'{safe_round(requests)} cores ' f'({safe_round(raw_percent(requests, allocatable), 1)}%)'),
                'percent': safe_percent(
                    requests,
                    allocatable,
                ),
                'bar_class': 'bg-blue-500',
            },
            {
                'label': 'Configured Limits',
                'display': (f'{safe_round(limits)} cores ' f'({safe_round(raw_percent(limits, allocatable), 1)}%)'),
                'percent': safe_percent(
                    limits,
                    allocatable,
                ),
                'bar_class': 'bg-blue-300',
            },
            {
                'label': 'Actual Avg Usage',
                'display': (f'{safe_round(actual)} cores ' f'({safe_round(raw_percent(actual, allocatable), 1)}%)'),
                'percent': safe_percent(
                    actual,
                    allocatable,
                ),
                'bar_class': 'bg-indigo-500',
            },
            {
                'label': 'Peak Usage',
                'display': (f'{safe_round(peak)} cores ' f'({safe_round(raw_percent(peak, allocatable), 1)}%)'),
                'percent': safe_percent(
                    peak,
                    allocatable,
                ),
                'bar_class': 'bg-slate-800',
            },
        ]

    def build_memory_allocation_items(
        self,
        allocatable_bytes: float,
        requests_bytes: float,
        limits_bytes: float,
        actual_bytes: float,
        peak_bytes: float,
    ) -> list[dict[str, Any]]:
        return [
            {
                'label': 'Allocatable',
                'display': f'{bytes_to_gib(allocatable_bytes)} GiB (100%)',
                'percent': 100,
                'bar_class': 'bg-slate-300',
            },
            {
                'label': 'Configured Requests',
                'display': (
                    f'{bytes_to_gib(requests_bytes)} GiB '
                    f'({safe_round(raw_percent(requests_bytes, allocatable_bytes), 1)}%)'
                ),
                'percent': safe_percent(
                    requests_bytes,
                    allocatable_bytes,
                ),
                'bar_class': 'bg-blue-500',
            },
            {
                'label': 'Configured Limits',
                'display': (
                    f'{bytes_to_gib(limits_bytes)} GiB '
                    f'({safe_round(raw_percent(limits_bytes, allocatable_bytes), 1)}%)'
                ),
                'percent': safe_percent(
                    limits_bytes,
                    allocatable_bytes,
                ),
                'bar_class': 'bg-blue-300',
            },
            {
                'label': 'Actual Avg Usage',
                'display': (
                    f'{bytes_to_gib(actual_bytes)} GiB '
                    f'({safe_round(raw_percent(actual_bytes, allocatable_bytes), 1)}%)'
                ),
                'percent': safe_percent(
                    actual_bytes,
                    allocatable_bytes,
                ),
                'bar_class': 'bg-indigo-500',
            },
            {
                'label': 'Peak Usage',
                'display': (
                    f'{bytes_to_gib(peak_bytes)} GiB ' f'({safe_round(raw_percent(peak_bytes, allocatable_bytes), 1)}%)'
                ),
                'percent': safe_percent(
                    peak_bytes,
                    allocatable_bytes,
                ),
                'bar_class': 'bg-slate-800',
            },
        ]

    def build_pod_allocation_items(
        self,
        capacity: float,
        current: float,
        remaining: float,
    ) -> list[dict[str, Any]]:
        return [
            {
                'label': 'Pod Capacity',
                'display': f'{safe_round(capacity, 0):.0f} pods (100%)',
                'percent': 100,
                'bar_class': 'bg-slate-300',
            },
            {
                'label': 'Current Pods',
                'display': (
                    f'{safe_round(current, 0):.0f} pods ' f'({safe_round(raw_percent(current, capacity), 1)}%)'
                ),
                'percent': safe_percent(
                    current,
                    capacity,
                ),
                'bar_class': 'bg-blue-500',
            },
            {
                'label': 'Remaining Pod Slots',
                'display': (
                    f'{safe_round(remaining, 0):.0f} pods ' f'({safe_round(raw_percent(remaining, capacity), 1)}%)'
                ),
                'percent': safe_percent(
                    remaining,
                    capacity,
                ),
                'bar_class': 'bg-cyan-500',
            },
            {
                'label': 'Pod Usage',
                'display': f'{safe_round(raw_percent(current, capacity), 1)}%',
                'percent': safe_percent(
                    current,
                    capacity,
                ),
                'bar_class': 'bg-indigo-500',
            },
        ]

    def paginate_rows(
        self,
        rows: list[dict[str, Any]],
        page: int,
        per_page: int,
    ) -> dict[str, Any]:
        return self.paginate_rows_with_options(
            rows=rows,
            page=page,
            per_page=per_page,
            allowed_per_page=ALLOWED_PER_PAGE_VALUES,
            default_per_page=10,
        )

    def filter_storage_rows(
        self,
        rows: list[dict[str, Any]],
        selected_search: str = '',
        selected_status: str = '',
        selected_storage_class: str = '',
    ) -> list[dict[str, Any]]:
        filtered_rows: list[dict[str, Any]] = []

        for row in rows:
            if selected_search:
                haystack = ' '.join(
                    str(row.get(key, ''))
                    for key in [
                        'name',
                        'namespace',
                        'claim',
                    ]
                ).lower()

                if selected_search.lower() not in haystack:
                    continue

            if (
                selected_status
                and row.get(
                    'status',
                )
                != selected_status
            ):
                continue

            if (
                selected_storage_class
                and row.get(
                    'storage_class',
                )
                != selected_storage_class
            ):
                continue

            filtered_rows.append(
                row,
            )

        return filtered_rows

    def get_unique_options(
        self,
        rows: list[dict[str, Any]],
        key: str,
    ) -> list[str]:
        values = {
            str(
                row.get(
                    key,
                    '',
                )
            )
            for row in rows
            if row.get(
                key,
            )
        }

        return sorted(
            values,
        )

    def get_storage_capacity_summary(
        self,
        selected_namespace: str,
        selected_node: str,
        selected_pvc_search: str = '',
        selected_pvc_status: str = '',
        selected_pvc_storage_class: str = '',
        pvc_page: int = 1,
        pvc_per_page: int = 10,
        selected_pv_search: str = '',
        selected_pv_status: str = '',
        selected_pv_storage_class: str = '',
        pv_page: int = 1,
        pv_per_page: int = 10,
    ) -> dict[str, Any]:
        node_size = self.get_prometheus_vector_map(
            query=queries.NODE_VAR_FILESYSTEM_SIZE_QUERY,
            label='instance',
        )

        node_available = self.get_prometheus_vector_map(
            query=queries.NODE_VAR_FILESYSTEM_AVAILABLE_QUERY,
            label='instance',
        )

        node_rows: list[dict[str, Any]] = []

        for node, size in sorted(
            node_size.items(),
        ):
            if selected_node and node != selected_node:
                continue

            available = node_available.get(
                node,
                0,
            )

            used = max(
                size - available,
                0,
            )

            usage_percent = raw_percent(
                used,
                size,
            )

            node_rows.append(
                {
                    'node': node,
                    'mountpoint': '/var',
                    'capacity': self.format_bytes(
                        size,
                    ),
                    'used': self.format_bytes(
                        used,
                    ),
                    'free': self.format_bytes(
                        available,
                    ),
                    'usage_percent': safe_round(
                        usage_percent,
                        1,
                    ),
                    'risk': self.get_usage_risk(
                        usage_percent,
                    ),
                    'capacity_bytes': size,
                    'used_bytes': used,
                    'free_bytes': available,
                }
            )

        total_capacity = sum(row['capacity_bytes'] for row in node_rows)

        total_used = sum(row['used_bytes'] for row in node_rows)

        total_free = sum(row['free_bytes'] for row in node_rows)

        highest_row = max(
            node_rows,
            key=lambda row: row['usage_percent'],
            default=None,
        )

        pvc_requested = self.get_prometheus_scalar(
            queries.PVC_REQUESTED_TOTAL_QUERY,
        )

        pvc_used = self.get_prometheus_scalar(
            queries.PVC_USED_TOTAL_QUERY,
        )

        pvc_free = self.get_prometheus_scalar(
            queries.PVC_AVAILABLE_TOTAL_QUERY,
        )

        if selected_namespace:
            pvc_requested_by_claim = self.get_prometheus_vector_map(
                query=queries.PVC_REQUESTED_BY_CLAIM_QUERY,
                label='persistentvolumeclaim',
                secondary_label='namespace',
            )

            pvc_used_by_claim = self.get_prometheus_vector_map(
                query=queries.PVC_USED_BY_CLAIM_QUERY,
                label='persistentvolumeclaim',
                secondary_label='namespace',
            )

            pvc_available_by_claim = self.get_prometheus_vector_map(
                query=queries.PVC_AVAILABLE_BY_CLAIM_QUERY,
                label='persistentvolumeclaim',
                secondary_label='namespace',
            )

            pvc_requested = sum(
                value
                for key, value in pvc_requested_by_claim.items()
                if key.startswith(
                    f'{selected_namespace}/',
                )
            )

            pvc_used = sum(
                value
                for key, value in pvc_used_by_claim.items()
                if key.startswith(
                    f'{selected_namespace}/',
                )
            )

            pvc_free = sum(
                value
                for key, value in pvc_available_by_claim.items()
                if key.startswith(
                    f'{selected_namespace}/',
                )
            )

        pv_capacity = self.get_prometheus_scalar(
            queries.PV_CAPACITY_QUERY,
        )

        pv_count = self.get_prometheus_scalar(
            queries.PV_COUNT_QUERY,
        )

        pvc_count = self.get_prometheus_scalar(
            queries.PVC_COUNT_QUERY,
        )

        pvc_all_rows = self.get_pvc_detail_rows(
            selected_namespace=selected_namespace,
        )

        pvc_status_options = self.get_unique_options(
            rows=pvc_all_rows,
            key='status',
        )

        pvc_storage_class_options = self.get_unique_options(
            rows=pvc_all_rows,
            key='storage_class',
        )

        pvc_filtered_rows = self.filter_storage_rows(
            rows=pvc_all_rows,
            selected_search=selected_pvc_search,
            selected_status=selected_pvc_status,
            selected_storage_class=selected_pvc_storage_class,
        )

        pvc_page_payload = self.paginate_rows(
            rows=pvc_filtered_rows,
            page=pvc_page,
            per_page=pvc_per_page,
        )

        pv_all_rows = self.get_pv_detail_rows()

        pv_status_options = self.get_unique_options(
            rows=pv_all_rows,
            key='status',
        )

        pv_storage_class_options = self.get_unique_options(
            rows=pv_all_rows,
            key='storage_class',
        )

        pv_filtered_rows = self.filter_storage_rows(
            rows=pv_all_rows,
            selected_search=selected_pv_search,
            selected_status=selected_pv_status,
            selected_storage_class=selected_pv_storage_class,
        )

        pv_page_payload = self.paginate_rows(
            rows=pv_filtered_rows,
            page=pv_page,
            per_page=pv_per_page,
        )

        return {
            'node_filesystem': {
                'selected_node': selected_node,
                'available_nodes': sorted(
                    node_size.keys(),
                ),
                'summary': {
                    'capacity': self.format_bytes(
                        total_capacity,
                    ),
                    'used': self.format_bytes(
                        total_used,
                    ),
                    'free': self.format_bytes(
                        total_free,
                    ),
                    'usage_percent': safe_round(
                        raw_percent(
                            total_used,
                            total_capacity,
                        ),
                        1,
                    ),
                    'free_percent': safe_round(
                        raw_percent(
                            total_free,
                            total_capacity,
                        ),
                        1,
                    ),
                    'highest_usage': (highest_row['usage_percent'] if highest_row else 0),
                    'highest_node': (highest_row['node'] if highest_row else '-'),
                },
                'rows': node_rows,
            },
            'persistent_storage': {
                'pv': {
                    'count': int(
                        pv_count,
                    ),
                    'capacity': self.format_bytes(
                        pv_capacity,
                    ),
                    'used': self.format_bytes(
                        pvc_used,
                    ),
                    'free': self.format_bytes(
                        pvc_free,
                    ),
                    'used_percent': safe_round(
                        raw_percent(
                            pvc_used,
                            pv_capacity,
                        ),
                        1,
                    ),
                    'free_percent': safe_round(
                        raw_percent(
                            pvc_free,
                            pv_capacity,
                        ),
                        1,
                    ),
                },
                'pvc': {
                    'count': int(
                        pvc_count,
                    ),
                    'requested': self.format_bytes(
                        pvc_requested,
                    ),
                    'used': self.format_bytes(
                        pvc_used,
                    ),
                    'free': self.format_bytes(
                        pvc_free,
                    ),
                    'used_percent': safe_round(
                        raw_percent(
                            pvc_used,
                            pvc_requested,
                        ),
                        1,
                    ),
                    'free_percent': safe_round(
                        raw_percent(
                            pvc_free,
                            pvc_requested,
                        ),
                        1,
                    ),
                },
                'pvc_rows': pvc_page_payload['rows'],
                'pvc_pagination': pvc_page_payload['pagination'],
                'pvc_selected_search': selected_pvc_search,
                'pvc_status_options': pvc_status_options,
                'pvc_storage_class_options': pvc_storage_class_options,
                'pvc_selected_status': selected_pvc_status,
                'pvc_selected_storage_class': selected_pvc_storage_class,
                'pv_rows': pv_page_payload['rows'],
                'pv_pagination': pv_page_payload['pagination'],
                'pv_selected_search': selected_pv_search,
                'pv_status_options': pv_status_options,
                'pv_storage_class_options': pv_storage_class_options,
                'pv_selected_status': selected_pv_status,
                'pv_selected_storage_class': selected_pv_storage_class,
            },
        }

    def get_pv_reclaim_policy_map(
        self,
    ) -> dict[str, str]:
        result = self.get_prometheus_result(
            queries.PV_RECLAIM_POLICY_QUERY,
        )

        values: dict[str, str] = {}

        for item in result:
            metric = item.get(
                'metric',
                {},
            )

            if not isinstance(
                metric,
                dict,
            ):
                continue

            volume = metric.get(
                'persistentvolume',
                '',
            )

            reclaim_policy = metric.get(
                'reclaim_policy',
                '',
            )

            if not reclaim_policy:
                reclaim_policy = metric.get(
                    'reclaimpolicy',
                    '',
                )

            if (
                not isinstance(
                    volume,
                    str,
                )
                or not volume
                or not isinstance(
                    reclaim_policy,
                    str,
                )
                or not reclaim_policy
            ):
                continue

            value = self.extract_value(
                item,
            )

            if value == 1:
                values[volume] = reclaim_policy

        return values

    def get_pv_claim_map(
        self,
    ) -> dict[str, str]:
        result = self.get_prometheus_result(
            queries.PVC_INFO_QUERY,
        )

        values: dict[str, str] = {}

        for item in result:
            metric = item.get(
                'metric',
                {},
            )

            if not isinstance(
                metric,
                dict,
            ):
                continue

            namespace = metric.get(
                'namespace',
                '',
            )

            pvc_name = metric.get(
                'persistentvolumeclaim',
                '',
            )

            volume_name = metric.get(
                'volumename',
                '',
            )

            if (
                not isinstance(
                    namespace,
                    str,
                )
                or not namespace
                or not isinstance(
                    pvc_name,
                    str,
                )
                or not pvc_name
                or not isinstance(
                    volume_name,
                    str,
                )
                or not volume_name
            ):
                continue

            values[volume_name] = f'{namespace}/{pvc_name}'

        return values

    def get_pvc_risk(
        self,
        status: str,
        usage_percent: float,
    ) -> dict[str, str]:
        if status == 'Pending':
            return {
                'label': 'Warning',
                'class': 'bg-amber-100 text-amber-700',
            }

        if status == 'Lost':
            return {
                'label': 'Critical',
                'class': 'bg-red-100 text-red-700',
            }

        if usage_percent >= 90:
            return {
                'label': 'Critical',
                'class': 'bg-red-100 text-red-700',
            }

        if usage_percent >= 75:
            return {
                'label': 'High',
                'class': 'bg-orange-100 text-orange-700',
            }

        return {
            'label': 'Healthy',
            'class': 'bg-emerald-100 text-emerald-700',
        }

    def get_pvc_status_map(
        self,
    ) -> dict[str, str]:
        result = self.get_prometheus_result(
            queries.PVC_STATUS_BY_CLAIM_QUERY,
        )

        values: dict[str, str] = {}

        for item in result:
            metric = item.get(
                'metric',
                {},
            )

            if not isinstance(
                metric,
                dict,
            ):
                continue

            namespace = metric.get(
                'namespace',
                '',
            )

            pvc_name = metric.get(
                'persistentvolumeclaim',
                '',
            )

            phase = metric.get(
                'phase',
                '',
            )

            if (
                not isinstance(
                    namespace,
                    str,
                )
                or not namespace
                or not isinstance(
                    pvc_name,
                    str,
                )
                or not pvc_name
                or not isinstance(
                    phase,
                    str,
                )
                or not phase
            ):
                continue

            value = self.extract_value(
                item,
            )

            if value == 1:
                values[f'{namespace}/{pvc_name}'] = phase

        return values

    def get_pvc_detail_rows(
        self,
        selected_namespace: str,
    ) -> list[dict[str, Any]]:
        requested = self.get_prometheus_vector_map(
            query=queries.PVC_REQUESTED_BY_CLAIM_QUERY,
            label='persistentvolumeclaim',
            secondary_label='namespace',
        )

        used = self.get_prometheus_vector_map(
            query=queries.PVC_USED_BY_CLAIM_QUERY,
            label='persistentvolumeclaim',
            secondary_label='namespace',
        )

        available = self.get_prometheus_vector_map(
            query=queries.PVC_AVAILABLE_BY_CLAIM_QUERY,
            label='persistentvolumeclaim',
            secondary_label='namespace',
        )

        storage_classes = self.get_prometheus_label_map(
            query=queries.PVC_INFO_QUERY,
            key_label='persistentvolumeclaim',
            value_label='storageclass',
            secondary_key_label='namespace',
        )

        status_map = self.get_pvc_status_map()

        keys = set(
            requested.keys(),
        )

        keys.update(
            used.keys(),
        )

        rows: list[dict[str, Any]] = []

        for key in sorted(
            keys,
        ):
            namespace, pvc_name = self.split_composite_key(
                key,
            )

            if selected_namespace and namespace != selected_namespace:
                continue

            requested_value = requested.get(
                key,
                0,
            )

            used_value = used.get(
                key,
                0,
            )

            free_value = available.get(
                key,
                0,
            )

            status = status_map.get(
                key,
                'Unknown',
            )

            usage_percent = raw_percent(
                used_value,
                requested_value,
            )

            rows.append(
                {
                    'name': pvc_name,
                    'namespace': namespace,
                    'status': status,
                    'storage_class': storage_classes.get(
                        key,
                        'No StorageClass',
                    ),
                    'requested': self.format_bytes(
                        requested_value,
                    ),
                    'used': self.format_bytes(
                        used_value,
                    ),
                    'free': self.format_bytes(
                        free_value,
                    ),
                    'usage_percent': safe_round(
                        usage_percent,
                        1,
                    ),
                    'risk': self.get_pvc_risk(
                        status=status,
                        usage_percent=usage_percent,
                    ),
                }
            )

        return rows

    def get_pv_detail_rows(
        self,
    ) -> list[dict[str, Any]]:
        capacities = self.get_prometheus_vector_map(
            query=queries.PV_CAPACITY_BY_VOLUME_QUERY,
            label='persistentvolume',
        )

        storage_classes = self.get_prometheus_label_map(
            query=queries.PV_INFO_QUERY,
            key_label='persistentvolume',
            value_label='storageclass',
        )

        claim_map = self.get_pv_claim_map()

        reclaim_policies = self.get_pv_reclaim_policy_map()

        status_map = self.get_pv_status_map()

        rows: list[dict[str, Any]] = []

        for volume, capacity in sorted(
            capacities.items(),
        ):
            status = status_map.get(
                volume,
                'Unknown',
            )

            rows.append(
                {
                    'name': volume,
                    'status': status,
                    'capacity': self.format_bytes(
                        capacity,
                    ),
                    'storage_class': storage_classes.get(
                        volume,
                        'No StorageClass',
                    ),
                    'claim': claim_map.get(
                        volume,
                        '-',
                    ),
                    'reclaim_policy': reclaim_policies.get(
                        volume,
                        '-',
                    ),
                    'risk': self.get_pv_risk(
                        status,
                    ),
                }
            )

        return rows

    def get_pv_risk(
        self,
        status: str,
    ) -> dict[str, str]:
        if status == 'Bound':
            return {
                'label': 'Healthy',
                'class': 'bg-emerald-100 text-emerald-700',
            }

        if status in [
            'Available',
            'Released',
        ]:
            return {
                'label': 'Watch',
                'class': 'bg-amber-100 text-amber-700',
            }

        if status == 'Failed':
            return {
                'label': 'Critical',
                'class': 'bg-red-100 text-red-700',
            }

        return {
            'label': 'Unknown',
            'class': 'bg-slate-100 text-slate-700',
        }

    def get_tenant_quota_summary(
        self,
        selected_namespace: str,
    ) -> dict[str, Any]:
        namespaces = self.get_prometheus_vector_map(
            query=queries.NAMESPACE_ACTIVE_QUERY,
            label='namespace',
        )

        hard = self.get_resource_quota_map(
            query=queries.TENANT_QUOTA_HARD_QUERY,
        )

        used = self.get_resource_quota_map(
            query=queries.TENANT_QUOTA_USED_QUERY,
        )

        cpu_actual = self.get_prometheus_vector_map(
            query=queries.TENANT_CPU_ACTUAL_QUERY,
            label='namespace',
        )

        memory_actual = self.get_prometheus_vector_map(
            query=queries.TENANT_MEMORY_ACTUAL_QUERY,
            label='namespace',
        )

        pod_actual = self.get_prometheus_vector_map(
            query=queries.TENANT_POD_ACTUAL_QUERY,
            label='namespace',
        )

        namespace_names = set(
            namespaces.keys(),
        )

        namespace_names.update(
            hard.keys(),
        )

        namespace_names.update(
            used.keys(),
        )

        rows: list[dict[str, Any]] = []

        for namespace in sorted(
            namespace_names,
        ):
            if selected_namespace and namespace != selected_namespace:
                continue

            hard_values = hard.get(
                namespace,
                {},
            )

            used_values = used.get(
                namespace,
                {},
            )

            missing_keys = [
                key
                for key in REQUIRED_QUOTA_KEYS
                if not hard_values.get(
                    key,
                    0,
                )
            ]

            quota_status = self.get_quota_status(
                hard_values=hard_values,
                missing_keys=missing_keys,
            )

            quota_usage_percent = self.get_highest_quota_percent(
                hard_values=hard_values,
                used_values=used_values,
            )

            actual_usage_percent = self.get_highest_actual_percent(
                hard_values=hard_values,
                cpu_actual=cpu_actual.get(
                    namespace,
                    0,
                ),
                memory_actual=memory_actual.get(
                    namespace,
                    0,
                ),
                pod_actual=pod_actual.get(
                    namespace,
                    0,
                ),
            )

            risk = self.get_tenant_analysis_risk(
                quota_status=quota_status['label'],
                quota_usage_percent=quota_usage_percent,
                actual_usage_percent=actual_usage_percent,
            )

            recommendation = self.get_tenant_recommendation(
                quota_status=quota_status['label'],
                missing_keys=missing_keys,
                quota_usage_percent=quota_usage_percent,
                actual_usage_percent=actual_usage_percent,
            )

            row = {
                'namespace': namespace,
                'quota_status': quota_status,
                'quota_usage_percent': safe_round(
                    quota_usage_percent,
                    1,
                ),
                'actual_usage_percent': safe_round(
                    actual_usage_percent,
                    1,
                ),
                'risk': risk,
                'recommendation': recommendation,
                'missing_keys': missing_keys,
                'missing_key_labels': [
                    self.get_resource_quota_label(
                        key,
                    )
                    for key in missing_keys
                ],
                'hard': hard_values,
                'used': used_values,
                'hard_items': self.build_resource_quota_items(
                    hard_values,
                ),
                'used_items': self.build_resource_quota_items(
                    used_values,
                ),
                'actual': {
                    'cpu': cpu_actual.get(
                        namespace,
                        0,
                    ),
                    'memory': memory_actual.get(
                        namespace,
                        0,
                    ),
                    'pods': pod_actual.get(
                        namespace,
                        0,
                    ),
                },
                # Backward-compatible fields for old template.
                'cpu_quota': hard_values.get(
                    'limits.cpu',
                    0,
                ),
                'cpu_requested': used_values.get(
                    'requests.cpu',
                    0,
                ),
                'cpu_limited': used_values.get(
                    'limits.cpu',
                    0,
                ),
                'cpu_actual': cpu_actual.get(
                    namespace,
                    0,
                ),
                'cpu_requested_percent': safe_percent(
                    used_values.get(
                        'requests.cpu',
                        0,
                    ),
                    hard_values.get(
                        'limits.cpu',
                        0,
                    ),
                ),
                'cpu_limited_percent': safe_percent(
                    used_values.get(
                        'limits.cpu',
                        0,
                    ),
                    hard_values.get(
                        'limits.cpu',
                        0,
                    ),
                ),
                'cpu_actual_percent': safe_percent(
                    cpu_actual.get(
                        namespace,
                        0,
                    ),
                    hard_values.get(
                        'limits.cpu',
                        0,
                    ),
                ),
                'memory_quota': bytes_to_gib(
                    hard_values.get(
                        'limits.memory',
                        0,
                    )
                ),
                'memory_requested': bytes_to_gib(
                    used_values.get(
                        'requests.memory',
                        0,
                    )
                ),
                'memory_limited': bytes_to_gib(
                    used_values.get(
                        'limits.memory',
                        0,
                    )
                ),
                'memory_actual': bytes_to_gib(
                    memory_actual.get(
                        namespace,
                        0,
                    )
                ),
                'memory_requested_percent': safe_percent(
                    used_values.get(
                        'requests.memory',
                        0,
                    ),
                    hard_values.get(
                        'limits.memory',
                        0,
                    ),
                ),
                'memory_limited_percent': safe_percent(
                    used_values.get(
                        'limits.memory',
                        0,
                    ),
                    hard_values.get(
                        'limits.memory',
                        0,
                    ),
                ),
                'memory_actual_percent': safe_percent(
                    memory_actual.get(
                        namespace,
                        0,
                    ),
                    hard_values.get(
                        'limits.memory',
                        0,
                    ),
                ),
                'workloads': int(
                    pod_actual.get(
                        namespace,
                        0,
                    )
                ),
            }

            rows.append(
                row,
            )

        total_namespaces = len(
            rows,
        )

        covered_namespaces = len([row for row in rows if row['quota_status']['label'] != 'Missing'])

        near_limit_count = len([row for row in rows if row['quota_usage_percent'] >= 75])

        efficiency_risk_count = len(
            [row for row in rows if (row['quota_usage_percent'] >= 75 and row['actual_usage_percent'] < 40)]
        )

        return {
            'summary_cards': [
                {
                    'label': 'Namespaces',
                    'value': total_namespaces,
                    'caption': 'Selected scope',
                    'icon': 'network',
                    'icon_class': 'bg-blue-100 text-blue-600',
                },
                {
                    'label': 'Quota Coverage',
                    'value': f'{safe_round(safe_percent(covered_namespaces, total_namespaces), 1)}%',
                    'caption': f'{covered_namespaces} of {total_namespaces} namespaces',
                    'icon': 'shield-check',
                    'icon_class': 'bg-cyan-100 text-cyan-600',
                },
                {
                    'label': 'Quota Near Limit',
                    'value': near_limit_count,
                    'caption': f'{safe_round(safe_percent(near_limit_count, total_namespaces), 1)}%',
                    'icon': 'triangle-alert',
                    'icon_class': 'bg-orange-100 text-orange-600',
                },
                {
                    'label': 'Quota Efficiency Risk',
                    'value': efficiency_risk_count,
                    'caption': f'{safe_round(safe_percent(efficiency_risk_count, total_namespaces), 1)}%',
                    'icon': 'activity',
                    'icon_class': 'bg-violet-100 text-violet-600',
                },
            ],
            'rows': rows,
        }

    def get_workload_mapping_payload(
        self,
        selected_namespace: str,
        time_range: str,
    ) -> dict[str, Any]:
        cpu_requests = self.get_prometheus_vector_map(
            query=queries.WORKLOAD_CPU_REQUESTS_QUERY,
            label='pod',
            secondary_label='namespace',
        )

        cpu_limits = self.get_prometheus_vector_map(
            query=queries.WORKLOAD_CPU_LIMITS_QUERY,
            label='pod',
            secondary_label='namespace',
        )

        cpu_avg = self.get_prometheus_vector_map(
            query=queries.WORKLOAD_CPU_AVG_QUERY,
            label='pod',
            secondary_label='namespace',
        )

        cpu_peak = self.get_prometheus_vector_map(
            query=self.build_range_query(
                queries.WORKLOAD_CPU_PEAK_QUERY_TEMPLATE,
                time_range,
            ),
            label='pod',
            secondary_label='namespace',
        )

        memory_requests = self.get_prometheus_vector_map(
            query=queries.WORKLOAD_MEMORY_REQUESTS_QUERY,
            label='pod',
            secondary_label='namespace',
        )

        memory_limits = self.get_prometheus_vector_map(
            query=queries.WORKLOAD_MEMORY_LIMITS_QUERY,
            label='pod',
            secondary_label='namespace',
        )

        memory_avg = self.get_prometheus_vector_map(
            query=queries.WORKLOAD_MEMORY_AVG_QUERY,
            label='pod',
            secondary_label='namespace',
        )

        memory_peak = self.get_prometheus_vector_map(
            query=self.build_range_query(
                queries.WORKLOAD_MEMORY_PEAK_QUERY_TEMPLATE,
                time_range,
            ),
            label='pod',
            secondary_label='namespace',
        )

        owner_map = self.get_pod_owner_map()

        qos_map = self.get_pod_qos_map()

        keys = set(
            cpu_requests.keys(),
        )

        keys.update(
            cpu_limits.keys(),
        )

        keys.update(
            cpu_avg.keys(),
        )

        keys.update(
            memory_requests.keys(),
        )

        keys.update(
            memory_limits.keys(),
        )

        keys.update(
            memory_avg.keys(),
        )

        workload_map: dict[str, dict[str, Any]] = {}

        for key in sorted(
            keys,
        ):
            namespace, pod = self.split_composite_key(
                key,
            )

            if selected_namespace and namespace != selected_namespace:
                continue

            owner = owner_map.get(
                key,
                self.infer_workload_owner(
                    pod,
                ),
            )

            workload_key = f"{namespace}/{owner['name']}"

            if workload_key not in workload_map:
                workload_map[workload_key] = {
                    'workload': owner['name'],
                    'type': owner['kind'],
                    'namespace': namespace,
                    'replicas': 0,
                    'pods': [],
                    'cpu_request_raw': 0.0,
                    'cpu_limit_raw': 0.0,
                    'cpu_avg_raw': 0.0,
                    'cpu_peak_raw': 0.0,
                    'memory_request_raw': 0.0,
                    'memory_limit_raw': 0.0,
                    'memory_avg_raw': 0.0,
                    'memory_peak_raw': 0.0,
                    'qos_distribution': {},
                }

            item = workload_map[workload_key]

            item['replicas'] += 1
            item['pods'].append(
                pod,
            )

            item['cpu_request_raw'] += cpu_requests.get(
                key,
                0,
            )

            item['cpu_limit_raw'] += cpu_limits.get(
                key,
                0,
            )

            item['cpu_avg_raw'] += cpu_avg.get(
                key,
                0,
            )

            item['cpu_peak_raw'] += cpu_peak.get(
                key,
                cpu_avg.get(
                    key,
                    0,
                ),
            )

            item['memory_request_raw'] += memory_requests.get(
                key,
                0,
            )

            item['memory_limit_raw'] += memory_limits.get(
                key,
                0,
            )

            item['memory_avg_raw'] += memory_avg.get(
                key,
                0,
            )

            item['memory_peak_raw'] += memory_peak.get(
                key,
                memory_avg.get(
                    key,
                    0,
                ),
            )

            qos = qos_map.get(
                key,
                'Unknown',
            )

            qos_distribution = item['qos_distribution']

            qos_distribution[qos] = (
                qos_distribution.get(
                    qos,
                    0,
                )
                + 1
            )

        rows: list[dict[str, Any]] = []

        for item in workload_map.values():
            resource_status = self.get_resource_status(
                cpu_request=item['cpu_request_raw'],
                cpu_limit=item['cpu_limit_raw'],
                memory_request=item['memory_request_raw'],
                memory_limit=item['memory_limit_raw'],
            )

            qos = self.get_workload_qos(
                item['qos_distribution'],
            )

            efficiency = self.get_efficiency_score(
                cpu_usage=item['cpu_avg_raw'],
                cpu_request=item['cpu_request_raw'],
                memory_usage=item['memory_avg_raw'],
                memory_request=item['memory_request_raw'],
            )

            recommendation = self.get_workload_recommendation(
                cpu_usage=item['cpu_avg_raw'],
                cpu_request=item['cpu_request_raw'],
                cpu_limit=item['cpu_limit_raw'],
                memory_usage=item['memory_avg_raw'],
                memory_request=item['memory_request_raw'],
                memory_limit=item['memory_limit_raw'],
                resource_status=resource_status['label'],
            )

            risk = self.get_workload_risk(
                resource_status=resource_status['label'],
                efficiency=efficiency,
                recommendation=recommendation,
            )

            rows.append(
                {
                    'workload': item['workload'],
                    'type': item['type'],
                    'namespace': item['namespace'],
                    'replicas': item['replicas'],
                    'resource_status': resource_status,
                    'qos': qos,
                    'cpu_summary': (
                        f"Req {self.format_cpu(item['cpu_request_raw'])} · "
                        f"Lim {self.format_cpu(item['cpu_limit_raw'])} · "
                        f"Avg {self.format_cpu(item['cpu_avg_raw'])} · "
                        f"Peak {self.format_cpu(item['cpu_peak_raw'])}"
                    ),
                    'memory_summary': (
                        f"Req {self.format_memory_bytes(item['memory_request_raw'])} · "
                        f"Lim {self.format_memory_bytes(item['memory_limit_raw'])} · "
                        f"Avg {self.format_memory_bytes(item['memory_avg_raw'])} · "
                        f"Peak {self.format_memory_bytes(item['memory_peak_raw'])}"
                    ),
                    'efficiency': efficiency,
                    'risk': risk,
                    'recommendation': recommendation,
                    'detail': {
                        'pods': item['pods'],
                        'qos_distribution': item['qos_distribution'],
                    },
                    # Backward-compatible fields for old template.
                    'cpu_request': self.format_cpu(
                        item['cpu_request_raw'],
                    ),
                    'cpu_limit': self.format_cpu(
                        item['cpu_limit_raw'],
                    ),
                    'cpu_avg': self.format_cpu(
                        item['cpu_avg_raw'],
                    ),
                    'cpu_peak': self.format_cpu(
                        item['cpu_peak_raw'],
                    ),
                    'memory_request': self.format_memory_bytes(
                        item['memory_request_raw'],
                    ),
                    'memory_limit': self.format_memory_bytes(
                        item['memory_limit_raw'],
                    ),
                    'memory_avg': self.format_memory_bytes(
                        item['memory_avg_raw'],
                    ),
                    'memory_peak': self.format_memory_bytes(
                        item['memory_peak_raw'],
                    ),
                }
            )

        rows.sort(
            key=lambda row: (
                self.get_risk_sort_weight(
                    row['risk']['label'],
                ),
                row['namespace'],
                row['workload'],
            )
        )

        return {
            'rows': rows,
            'filters': {
                'resource_status': [
                    'All',
                    'Complete',
                    'Partial',
                    'Missing Request',
                    'Missing Limit',
                    'BestEffort',
                    'No Metrics',
                ],
                'qos': [
                    'All',
                    'Guaranteed',
                    'Burstable',
                    'BestEffort',
                    'Mixed',
                    'Unknown',
                ],
                'risk': [
                    'All',
                    'Low',
                    'Medium',
                    'High',
                ],
            },
        }

    def get_namespace_options(
        self,
        tenant_quota_rows: list[dict[str, Any]],
        workload_mapping_rows: list[dict[str, Any]],
    ) -> list[str]:
        namespaces = {
            item['namespace']
            for item in tenant_quota_rows
            if item.get(
                'namespace',
            )
        }

        namespaces.update(
            {
                item['namespace']
                for item in workload_mapping_rows
                if item.get(
                    'namespace',
                )
            }
        )

        return sorted(
            namespaces,
        )

    def get_all_namespace_options(
        self,
    ) -> list[str]:
        active_namespaces = self.get_prometheus_vector_map(
            query=queries.NAMESPACE_ACTIVE_QUERY,
            label='namespace',
        )

        quota_hard = self.get_resource_quota_map(
            query=queries.TENANT_QUOTA_HARD_QUERY,
        )

        quota_used = self.get_resource_quota_map(
            query=queries.TENANT_QUOTA_USED_QUERY,
        )

        runtime_namespaces = self.get_prometheus_vector_map(
            query=queries.TENANT_POD_ACTUAL_QUERY,
            label='namespace',
        )

        namespaces = set(
            active_namespaces.keys(),
        )

        namespaces.update(
            quota_hard.keys(),
        )

        namespaces.update(
            quota_used.keys(),
        )

        namespaces.update(
            runtime_namespaces.keys(),
        )

        return sorted(namespace for namespace in namespaces if namespace)

    def get_quota_coverage(
        self,
        tenant_quota_rows: list[dict[str, Any]],
        namespace_options: list[str],
    ) -> dict[str, Any]:
        total_namespaces = len(
            namespace_options,
        )

        quota_namespaces = len(
            [
                item
                for item in tenant_quota_rows
                if item.get(
                    'quota_status',
                    {},
                ).get(
                    'label',
                )
                != 'Missing'
            ]
        )

        return {
            'total_namespaces': total_namespaces,
            'quota_namespaces': quota_namespaces,
            'coverage_percent': safe_percent(
                quota_namespaces,
                total_namespaces,
            ),
        }

    def get_capacity_risk_summary(
        self,
        capacity_summary: dict[str, dict[str, float]],
    ) -> list[dict[str, Any]]:
        icon_map = {
            'cpu': 'cpu',
            'memory': 'memory-stick',
            'pods': 'box',
        }

        icon_class_map = {
            'cpu': 'bg-emerald-100 text-emerald-600',
            'memory': 'bg-violet-100 text-violet-600',
            'pods': 'bg-cyan-100 text-cyan-600',
        }

        risks: list[dict[str, Any]] = []

        for resource in [
            'cpu',
            'memory',
            'pods',
        ]:
            item = capacity_summary.get(
                resource,
                {},
            )

            headroom = self.to_float(
                item.get(
                    'headroom',
                    0,
                )
            )

            status = self.get_headroom_status(
                headroom,
            )

            risks.append(
                {
                    'resource': resource,
                    'label': 'Pod' if resource == 'pods' else resource.title(),
                    'headroom': headroom,
                    'status': status,
                    'icon': icon_map.get(
                        resource,
                        'activity',
                    ),
                    'icon_class': icon_class_map.get(
                        resource,
                        'bg-slate-100 text-slate-600',
                    ),
                }
            )

        return risks

    def get_capacity_governance_findings(
        self,
        capacity_summary: dict[str, dict[str, float]],
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        low_headroom = [
            resource
            for resource, item in capacity_summary.items()
            if resource
            in [
                'cpu',
                'memory',
                'pods',
            ]
            and self.to_float(
                item.get(
                    'headroom',
                    0,
                )
            )
            < 30
        ]

        if low_headroom:
            findings.append(
                {
                    'label': ('Low capacity headroom detected on ' f"{', '.join(low_headroom)}"),
                    'severity': 'critical',
                    'icon': 'circle-alert',
                    'filter': 'capacity-headroom',
                }
            )

        findings.append(
            {
                'label': 'Open Workload Analysis for quota and request/limit findings',
                'severity': 'info',
                'icon': 'boxes',
                'filter': 'workload-analysis',
            }
        )

        findings.append(
            {
                'label': 'Open Storage Analysis for PV, PVC, and filesystem findings',
                'severity': 'info',
                'icon': 'hard-drive',
                'filter': 'storage-analysis',
            }
        )

        if not findings:
            findings.append(
                {
                    'label': 'No capacity findings detected',
                    'severity': 'healthy',
                    'icon': 'check-circle',
                    'filter': '',
                }
            )

        return findings

    def get_capacity_recommendation_cards(
        self,
        capacity_summary: dict[str, dict[str, float]],
    ) -> list[dict[str, Any]]:
        low_headroom = [
            resource
            for resource, item in capacity_summary.items()
            if resource
            in [
                'cpu',
                'memory',
                'pods',
            ]
            and self.to_float(
                item.get(
                    'headroom',
                    0,
                )
            )
            < 30
        ]

        capacity_description = (
            'Monitor headroom trend and plan capacity expansion ' 'before sustained usage reaches warning threshold.'
        )

        if low_headroom:
            capacity_description = (
                'Low headroom detected on '
                f"{', '.join(low_headroom)}. "
                'Prioritize capacity planning for these resources.'
            )

        return [
            {
                'title': 'Monitor Capacity Growth',
                'description': capacity_description,
                'icon': 'trending-up',
                'icon_class': 'bg-violet-100 text-violet-600',
            },
            {
                'title': 'Review Storage Capacity',
                'description': (
                    'Open Storage Analysis to review node filesystem, '
                    'PersistentVolume capacity, PVC requests, and storage risk.'
                ),
                'icon': 'hard-drive',
                'icon_class': 'bg-blue-100 text-blue-600',
            },
            {
                'title': 'Review Workload Governance',
                'description': (
                    'Open Workload Analysis to validate ResourceQuota coverage, '
                    'workload requests, limits, QoS class, and right-sizing actions.'
                ),
                'icon': 'shield-alert',
                'icon_class': 'bg-orange-100 text-orange-600',
            },
            {
                'title': 'Right-size Resource Requests',
                'description': (
                    'Use Workload Analysis to compare requests and limits '
                    'against actual runtime usage before changing quotas.'
                ),
                'icon': 'activity',
                'icon_class': 'bg-emerald-100 text-emerald-600',
            },
        ]

    def get_governance_findings(
        self,
        tenant_quota_rows: list[dict[str, Any]],
        workload_mapping_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        no_quota_count = len(
            [
                row
                for row in tenant_quota_rows
                if row.get(
                    'quota_status',
                    {},
                ).get(
                    'label',
                )
                == 'Missing'
            ]
        )

        missing_request_count = len(
            [
                row
                for row in workload_mapping_rows
                if row.get(
                    'resource_status',
                    {},
                ).get(
                    'label',
                )
                in [
                    'Missing Request',
                    'BestEffort',
                ]
            ]
        )

        missing_limit_count = len(
            [
                row
                for row in workload_mapping_rows
                if row.get(
                    'resource_status',
                    {},
                ).get(
                    'label',
                )
                in [
                    'Missing Limit',
                    'BestEffort',
                ]
            ]
        )

        best_effort_count = len(
            [
                row
                for row in workload_mapping_rows
                if row.get(
                    'qos',
                    {},
                ).get(
                    'label',
                )
                == 'BestEffort'
            ]
        )

        over_requested_count = len(
            [
                row
                for row in workload_mapping_rows
                if 'reduce'
                in str(
                    row.get(
                        'recommendation',
                        '',
                    )
                ).lower()
            ]
        )

        findings: list[dict[str, Any]] = []

        if no_quota_count:
            findings.append(
                {
                    'label': f'{no_quota_count} namespaces without ResourceQuota',
                    'severity': 'warning',
                    'icon': 'triangle-alert',
                    'filter': 'missing-quota',
                }
            )

        if missing_request_count:
            findings.append(
                {
                    'label': f'{missing_request_count} workloads missing requests',
                    'severity': 'warning',
                    'icon': 'triangle-alert',
                    'filter': 'missing-request',
                }
            )

        if missing_limit_count:
            findings.append(
                {
                    'label': f'{missing_limit_count} workloads missing limits',
                    'severity': 'warning',
                    'icon': 'triangle-alert',
                    'filter': 'missing-limit',
                }
            )

        if best_effort_count:
            findings.append(
                {
                    'label': f'{best_effort_count} BestEffort workloads',
                    'severity': 'warning',
                    'icon': 'info',
                    'filter': 'best-effort',
                }
            )

        if over_requested_count:
            findings.append(
                {
                    'label': f'{over_requested_count} workloads over-requested',
                    'severity': 'critical',
                    'icon': 'circle-alert',
                    'filter': 'over-requested',
                }
            )

        if not findings:
            findings.append(
                {
                    'label': 'No critical governance findings detected',
                    'severity': 'healthy',
                    'icon': 'check-circle',
                    'filter': '',
                }
            )

        return findings

    def get_recommendation_cards(
        self,
        capacity_summary: dict[str, dict[str, float]],
        tenant_quota_rows: list[dict[str, Any]],
        workload_mapping_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        low_headroom = [
            resource
            for resource, item in capacity_summary.items()
            if resource
            in [
                'cpu',
                'memory',
                'pods',
            ]
            and self.to_float(
                item.get(
                    'headroom',
                    0,
                )
            )
            < 30
        ]

        no_quota_count = len(
            [
                row
                for row in tenant_quota_rows
                if row.get(
                    'quota_status',
                    {},
                ).get(
                    'label',
                )
                == 'Missing'
            ]
        )

        reduce_count = len(
            [
                row
                for row in workload_mapping_rows
                if 'reduce'
                in str(
                    row.get(
                        'recommendation',
                        '',
                    )
                ).lower()
            ]
        )

        missing_request_count = len(
            [
                row
                for row in workload_mapping_rows
                if row.get(
                    'resource_status',
                    {},
                ).get(
                    'label',
                )
                in [
                    'Missing Request',
                    'BestEffort',
                ]
            ]
        )

        missing_limit_count = len(
            [
                row
                for row in workload_mapping_rows
                if row.get(
                    'resource_status',
                    {},
                ).get(
                    'label',
                )
                in [
                    'Missing Limit',
                    'BestEffort',
                ]
            ]
        )

        capacity_description = (
            'Monitor headroom trend and plan capacity expansion ' 'before sustained usage reaches warning threshold.'
        )

        if low_headroom:
            capacity_description = (
                'Low headroom detected on '
                f"{', '.join(low_headroom)}. "
                'Prioritize capacity planning for these resources.'
            )

        return [
            {
                'title': 'Right-size Resource Requests',
                'description': (
                    f'{reduce_count} workloads have potential over-requested '
                    'resources. Review request values against actual usage.'
                ),
                'icon': 'activity',
                'icon_class': 'bg-emerald-100 text-emerald-600',
            },
            {
                'title': 'Strengthen Governance',
                'description': (
                    f'{missing_request_count} workloads missing requests, '
                    f'{missing_limit_count} workloads missing limits, and '
                    f'{no_quota_count} namespaces without ResourceQuota need attention.'
                ),
                'icon': 'shield-alert',
                'icon_class': 'bg-orange-100 text-orange-600',
            },
            {
                'title': 'Optimize Limit Quota Allocation',
                'description': (
                    'Review tenant ResourceQuota allocation and compare '
                    'configured workload limits against actual runtime usage.'
                ),
                'icon': 'sliders-horizontal',
                'icon_class': 'bg-blue-100 text-blue-600',
            },
            {
                'title': 'Monitor Capacity Growth',
                'description': capacity_description,
                'icon': 'trending-up',
                'icon_class': 'bg-violet-100 text-violet-600',
            },
        ]

    def get_resource_quota_map(
        self,
        query: str,
    ) -> dict[str, dict[str, float]]:
        result = self.get_prometheus_result(
            query,
        )

        values: dict[str, dict[str, float]] = {}

        for item in result:
            metric = item.get(
                'metric',
                {},
            )

            if not isinstance(
                metric,
                dict,
            ):
                continue

            namespace = metric.get(
                'namespace',
                '',
            )

            resource = metric.get(
                'resource',
                '',
            )

            if (
                not isinstance(
                    namespace,
                    str,
                )
                or not namespace
                or not isinstance(
                    resource,
                    str,
                )
                or not resource
            ):
                continue

            if namespace not in values:
                values[namespace] = {}

            values[namespace][resource] = self.extract_value(
                item,
            )

        return values

    def get_pod_owner_map(
        self,
    ) -> dict[str, dict[str, str]]:
        result = self.get_prometheus_result(
            queries.WORKLOAD_POD_OWNER_QUERY,
        )

        values: dict[str, dict[str, str]] = {}

        for item in result:
            metric = item.get(
                'metric',
                {},
            )

            if not isinstance(
                metric,
                dict,
            ):
                continue

            namespace = metric.get(
                'namespace',
                '',
            )

            pod = metric.get(
                'pod',
                '',
            )

            owner_kind = metric.get(
                'owner_kind',
                'Pod',
            )

            owner_name = metric.get(
                'owner_name',
                pod,
            )

            if (
                not isinstance(
                    namespace,
                    str,
                )
                or not isinstance(
                    pod,
                    str,
                )
                or not namespace
                or not pod
            ):
                continue

            if not isinstance(
                owner_kind,
                str,
            ):
                owner_kind = 'Pod'

            if not isinstance(
                owner_name,
                str,
            ):
                owner_name = pod

            if owner_kind == 'ReplicaSet':
                owner_kind = 'Deployment'
                owner_name = self.strip_replicaset_hash(
                    owner_name,
                )

            values[f'{namespace}/{pod}'] = {
                'kind': owner_kind,
                'name': owner_name,
            }

        return values

    def get_pod_qos_map(
        self,
    ) -> dict[str, str]:
        result = self.get_prometheus_result(
            queries.WORKLOAD_QOS_QUERY,
        )

        values: dict[str, str] = {}

        for item in result:
            metric = item.get(
                'metric',
                {},
            )

            if not isinstance(
                metric,
                dict,
            ):
                continue

            namespace = metric.get(
                'namespace',
                '',
            )

            pod = metric.get(
                'pod',
                '',
            )

            qos_class = metric.get(
                'qos_class',
                '',
            )

            if (
                not isinstance(
                    namespace,
                    str,
                )
                or not isinstance(
                    pod,
                    str,
                )
                or not isinstance(
                    qos_class,
                    str,
                )
                or not namespace
                or not pod
                or not qos_class
            ):
                continue

            values[f'{namespace}/{pod}'] = qos_class

        return values

    def infer_workload_owner(
        self,
        pod_name: str,
    ) -> dict[str, str]:
        workload_name = self.strip_pod_suffix(
            pod_name,
        )

        return {
            'kind': 'Workload',
            'name': workload_name,
        }

    def strip_pod_suffix(
        self,
        pod_name: str,
    ) -> str:
        match = re.match(
            r'^(?P<name>.+)-[a-z0-9]{8,10}-[a-z0-9]{5}$',
            pod_name,
        )

        if match:
            return match.group(
                'name',
            )

        match = re.match(
            r'^(?P<name>.+)-[a-z0-9]{5}$',
            pod_name,
        )

        if match:
            return match.group(
                'name',
            )

        return pod_name

    def strip_replicaset_hash(
        self,
        owner_name: str,
    ) -> str:
        return re.sub(
            r'-[a-z0-9]{8,10}$',
            '',
            owner_name,
        )

    def get_quota_status(
        self,
        hard_values: dict[str, float],
        missing_keys: list[str],
    ) -> dict[str, str]:
        if not hard_values:
            return {
                'label': 'Missing',
                'class': 'bg-red-100 text-red-700',
            }

        if missing_keys:
            return {
                'label': 'Partial',
                'class': 'bg-amber-100 text-amber-700',
            }

        return {
            'label': 'Complete',
            'class': 'bg-emerald-100 text-emerald-700',
        }

    def get_highest_quota_percent(
        self,
        hard_values: dict[str, float],
        used_values: dict[str, float],
    ) -> float:
        values = [
            raw_percent(
                used_values.get(
                    key,
                    0,
                ),
                hard_values.get(
                    key,
                    0,
                ),
            )
            for key in REQUIRED_QUOTA_KEYS
        ]

        return max(
            values,
            default=0,
        )

    def get_highest_actual_percent(
        self,
        hard_values: dict[str, float],
        cpu_actual: float,
        memory_actual: float,
        pod_actual: float,
    ) -> float:
        values = [
            raw_percent(
                cpu_actual,
                hard_values.get(
                    'limits.cpu',
                    0,
                ),
            ),
            raw_percent(
                memory_actual,
                hard_values.get(
                    'limits.memory',
                    0,
                ),
            ),
            raw_percent(
                pod_actual,
                hard_values.get(
                    'pods',
                    0,
                ),
            ),
        ]

        return max(
            values,
            default=0,
        )

    def get_tenant_analysis_risk(
        self,
        quota_status: str,
        quota_usage_percent: float,
        actual_usage_percent: float,
    ) -> dict[str, str]:
        if quota_status == 'Missing':
            return {
                'label': 'Critical',
                'class': 'bg-red-100 text-red-700',
            }

        if quota_usage_percent >= 90:
            return {
                'label': 'Critical',
                'class': 'bg-red-100 text-red-700',
            }

        if quota_usage_percent >= 75:
            return {
                'label': 'High',
                'class': 'bg-orange-100 text-orange-700',
            }

        if quota_usage_percent >= 75 and actual_usage_percent < 40:
            return {
                'label': 'Medium',
                'class': 'bg-amber-100 text-amber-700',
            }

        if quota_status == 'Partial':
            return {
                'label': 'Medium',
                'class': 'bg-amber-100 text-amber-700',
            }

        return {
            'label': 'Low',
            'class': 'bg-emerald-100 text-emerald-700',
        }

    def get_tenant_recommendation(
        self,
        quota_status: str,
        missing_keys: list[str],
        quota_usage_percent: float,
        actual_usage_percent: float,
    ) -> str:
        if quota_status == 'Missing':
            return 'Create ResourceQuota'

        if missing_keys:
            return 'Add missing quota keys'

        if quota_usage_percent >= 90:
            if actual_usage_percent < 50:
                return 'Right-size workload requests before increasing quota'

            return 'Review allocation or increase quota'

        if quota_usage_percent >= 75:
            return 'Monitor quota and review allocation'

        if quota_usage_percent >= 75 and actual_usage_percent < 40:
            return 'Right-size requests and limits'

        return 'Quota looks healthy'

    def get_resource_status(
        self,
        cpu_request: float,
        cpu_limit: float,
        memory_request: float,
        memory_limit: float,
    ) -> dict[str, str]:
        missing_request = not cpu_request or not memory_request
        missing_limit = not cpu_limit or not memory_limit

        if missing_request and missing_limit:
            return {
                'label': 'BestEffort',
                'class': 'bg-red-100 text-red-700',
            }

        if missing_request:
            return {
                'label': 'Missing Request',
                'class': 'bg-amber-100 text-amber-700',
            }

        if missing_limit:
            return {
                'label': 'Missing Limit',
                'class': 'bg-amber-100 text-amber-700',
            }

        return {
            'label': 'Complete',
            'class': 'bg-emerald-100 text-emerald-700',
        }

    def get_workload_qos(
        self,
        qos_distribution: dict[str, int],
    ) -> dict[str, str]:
        if not qos_distribution:
            return {
                'label': 'Unknown',
                'class': 'bg-slate-100 text-slate-700',
            }

        if (
            len(
                qos_distribution,
            )
            > 1
        ):
            return {
                'label': 'Mixed',
                'class': 'bg-indigo-100 text-indigo-700',
            }

        qos = next(
            iter(
                qos_distribution.keys(),
            )
        )

        class_map = {
            'Guaranteed': 'bg-emerald-100 text-emerald-700',
            'Burstable': 'bg-blue-100 text-blue-700',
            'BestEffort': 'bg-red-100 text-red-700',
        }

        return {
            'label': qos,
            'class': class_map.get(
                qos,
                'bg-slate-100 text-slate-700',
            ),
        }

    def get_workload_risk(
        self,
        resource_status: str,
        efficiency: float,
        recommendation: str,
    ) -> dict[str, str]:
        if resource_status in [
            'BestEffort',
            'Missing Request',
        ]:
            return {
                'label': 'High',
                'class': 'bg-red-100 text-red-700',
            }

        if 'increase' in recommendation.lower():
            return {
                'label': 'High',
                'class': 'bg-red-100 text-red-700',
            }

        if resource_status in [
            'Missing Limit',
            'Partial',
        ]:
            return {
                'label': 'Medium',
                'class': 'bg-amber-100 text-amber-700',
            }

        if efficiency < 40:
            return {
                'label': 'Medium',
                'class': 'bg-amber-100 text-amber-700',
            }

        return {
            'label': 'Low',
            'class': 'bg-emerald-100 text-emerald-700',
        }

    def get_risk_sort_weight(
        self,
        risk: str,
    ) -> int:
        weights = {
            'High': 0,
            'Critical': 0,
            'Medium': 1,
            'Low': 2,
        }

        return weights.get(
            risk,
            3,
        )

    def get_efficiency_score(
        self,
        cpu_usage: float,
        cpu_request: float,
        memory_usage: float,
        memory_request: float,
    ) -> float:
        cpu_score = safe_percent(
            cpu_usage,
            cpu_request,
        )

        memory_score = safe_percent(
            memory_usage,
            memory_request,
        )

        if not cpu_request and not memory_request:
            return 0

        if cpu_request and memory_request:
            return safe_round(
                (cpu_score + memory_score) / 2,
                1,
            )

        return safe_round(
            cpu_score or memory_score,
            1,
        )

    def get_workload_recommendation(
        self,
        cpu_usage: float,
        cpu_request: float,
        cpu_limit: float,
        memory_usage: float,
        memory_request: float,
        memory_limit: float,
        resource_status: str,
    ) -> str:
        if resource_status == 'BestEffort':
            return 'Review BestEffort workload'

        if not cpu_request and not memory_request:
            return 'Set CPU and memory requests'

        if not cpu_request:
            return 'Set CPU request'

        if not memory_request:
            return 'Set memory request'

        if not memory_limit:
            return 'Set memory limit'

        if not cpu_limit:
            return 'Review CPU limit policy'

        cpu_efficiency = safe_percent(
            cpu_usage,
            cpu_request,
        )

        memory_efficiency = safe_percent(
            memory_usage,
            memory_request,
        )

        if cpu_efficiency < 30 and memory_efficiency < 30:
            return 'Reduce requests'

        if cpu_efficiency < 30:
            return 'Reduce CPU request'

        if memory_efficiency < 30:
            return 'Reduce memory request'

        if memory_efficiency > 90:
            return 'Increase memory request'

        if cpu_efficiency > 90:
            return 'Increase CPU request'

        return 'No action needed'

    def get_headroom_status(
        self,
        headroom: float,
    ) -> dict[str, str]:
        if headroom < 15:
            return {
                'label': 'Critical',
                'class': 'bg-red-100 text-red-700',
            }

        if headroom < 40:
            return {
                'label': 'Watch',
                'class': 'bg-amber-100 text-amber-700',
            }

        return {
            'label': 'Healthy',
            'class': 'bg-emerald-100 text-emerald-700',
        }

    def get_allocation_status(
        self,
        requested: float,
        allocatable: float,
        resource: str,
    ) -> dict[str, str]:
        percent = raw_percent(
            requested,
            allocatable,
        )

        if percent >= 100 and resource == 'cpu':
            return {
                'label': 'CPU limit overcommit',
                'class': 'bg-red-100 text-red-700',
            }

        if percent >= 90 and resource == 'memory':
            return {
                'label': 'Memory near capacity',
                'class': 'bg-orange-100 text-orange-700',
            }

        if percent >= 90:
            return {
                'label': 'Near capacity',
                'class': 'bg-orange-100 text-orange-700',
            }

        if percent >= 75:
            return {
                'label': 'Watch',
                'class': 'bg-amber-100 text-amber-700',
            }

        return {
            'label': 'Healthy',
            'class': 'bg-emerald-100 text-emerald-700',
        }

    def get_usage_risk(
        self,
        percent: float,
    ) -> dict[str, str]:
        if percent >= 90:
            return {
                'label': 'Critical',
                'class': 'bg-red-100 text-red-700',
            }

        if percent >= 75:
            return {
                'label': 'High',
                'class': 'bg-orange-100 text-orange-700',
            }

        if percent >= 60:
            return {
                'label': 'Watch',
                'class': 'bg-amber-100 text-amber-700',
            }

        return {
            'label': 'Healthy',
            'class': 'bg-emerald-100 text-emerald-700',
        }

    def get_pv_status_map(
        self,
    ) -> dict[str, str]:
        result = self.get_prometheus_result(
            queries.PV_STATUS_BY_VOLUME_QUERY,
        )

        values: dict[str, str] = {}

        for item in result:
            metric = item.get(
                'metric',
                {},
            )

            if not isinstance(
                metric,
                dict,
            ):
                continue

            volume = metric.get(
                'persistentvolume',
                '',
            )

            phase = metric.get(
                'phase',
                '',
            )

            if (
                not isinstance(
                    volume,
                    str,
                )
                or not volume
                or not isinstance(
                    phase,
                    str,
                )
                or not phase
            ):
                continue

            value = self.extract_value(
                item,
            )

            if value == 1:
                values[volume] = phase

        return values

    def get_prometheus_status(
        self,
    ) -> dict[str, Any]:
        prometheus = getattr(
            self.utilization_service,
            'prometheus',
            None,
        )

        if prometheus is None:
            prometheus = getattr(
                self.utilization_service,
                'prometheus_service',
                None,
            )

        if prometheus is None:
            return {
                'connected': False,
                'response_time_ms': None,
                'label': 'Prometheus Disconnected',
                'description': 'Prometheus service unavailable',
            }

        start_time = time.perf_counter()

        try:
            if hasattr(
                prometheus,
                'instant_query',
            ):
                prometheus.instant_query(
                    'vector(1)',
                )
            elif hasattr(
                prometheus,
                'query',
            ):
                prometheus.query(
                    'vector(1)',
                )
            else:
                raise RuntimeError(
                    'Prometheus query method unavailable',
                )

        except Exception:
            return {
                'connected': False,
                'response_time_ms': None,
                'label': 'Prometheus Disconnected',
                'description': 'Prometheus query failed',
            }

        elapsed_ms = int(
            (time.perf_counter() - start_time) * 1000,
        )

        if elapsed_ms >= 1500:
            return {
                'connected': True,
                'response_time_ms': elapsed_ms,
                'label': 'Prometheus Degraded',
                'description': 'Prometheus responded slowly.',
            }

        return {
            'connected': True,
            'response_time_ms': elapsed_ms,
            'label': 'Prometheus Connected',
            'description': 'Last query completed successfully.',
        }

    def get_resource_quota_label(
        self,
        key: str,
    ) -> str:
        label_map = {
            'requests.cpu': 'Requests CPU',
            'limits.cpu': 'Limits CPU',
            'requests.memory': 'Requests Memory',
            'limits.memory': 'Limits Memory',
            'pods': 'Pods',
        }

        return label_map.get(
            key,
            key,
        )

    def format_resource_quota_value(
        self,
        key: str,
        value: float,
    ) -> str:
        if key.endswith(
            '.cpu',
        ):
            return self.format_cpu(
                value,
            )

        if key.endswith(
            '.memory',
        ):
            return self.format_memory_bytes(
                value,
            )

        if key == 'pods':
            return f'{safe_round(value, 0):.0f} pods'

        return str(
            safe_round(
                value,
                2,
            )
        )

    def build_resource_quota_items(
        self,
        values: dict[str, float],
    ) -> list[dict[str, str]]:
        return [
            {
                'label': self.get_resource_quota_label(
                    key,
                ),
                'value': self.format_resource_quota_value(
                    key=key,
                    value=value,
                ),
            }
            for key, value in sorted(
                values.items(),
            )
        ]
