# app/analytics/capacity/service.py

from __future__ import annotations

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

    def get_all_namespace_options(
        self,
    ) -> list[str]:
        active_namespaces = self.get_prometheus_vector_map(
            query=queries.NAMESPACE_ACTIVE_QUERY,
            label='namespace',
        )

        return sorted(namespace for namespace in active_namespaces.keys() if namespace)

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
