# app/analytics/top_consumers/service.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.analytics.common.base_service import AnalyticsBaseService, raw_percent, safe_round
from app.analytics.common.context import build_analysis_utilization_context
from app.analytics.common.params import (
    ALLOWED_PER_PAGE_VALUES,
    get_allowed_time_ranges,
    get_per_page_arg,
    get_positive_int_arg,
    get_query_value,
    get_selected_time_range,
)
from app.analytics.top_consumers import queries
from app.analytics.utilization.service import UtilizationService
from app.prometheus.exceptions import PrometheusError

RESOURCE_OPTIONS: list[dict[str, str]] = [
    {'value': 'all', 'label': 'All Resources'},
    {'value': 'cpu', 'label': 'CPU'},
    {'value': 'memory', 'label': 'Memory'},
    {'value': 'pods', 'label': 'Pods'},
    {'value': 'pvc', 'label': 'PVC'},
]

SORT_OPTIONS: list[dict[str, str]] = [
    {'value': 'usage_percent', 'label': 'Usage %'},
    {'value': 'usage', 'label': 'Current Usage'},
    {'value': 'risk', 'label': 'Risk'},
    {'value': 'namespace', 'label': 'Namespace'},
    {'value': 'resource', 'label': 'Resource Type'},
]

RESOURCE_LABELS = {
    'cpu': 'CPU',
    'memory': 'Memory',
    'pods': 'Pods',
    'pvc': 'PVC',
}

RESOURCE_ICONS = {
    'cpu': 'cpu',
    'memory': 'memory-stick',
    'pods': 'boxes',
    'pvc': 'database',
}

RESOURCE_BADGE_CLASSES = {
    'cpu': 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
    'memory': 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300',
    'pods': 'bg-violet-50 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300',
    'pvc': 'bg-orange-50 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300',
}

RISK_RANK = {
    'critical': 3,
    'warning': 2,
    'normal': 1,
    'unknown': 0,
}


def get_selected_resource(
    query_args: Mapping[str, Any],
) -> str:
    selected_resource = get_query_value(
        query_args=query_args,
        name='resource',
        default='all',
    )

    allowed_values = {item['value'] for item in RESOURCE_OPTIONS}

    if selected_resource not in allowed_values:
        return 'all'

    return selected_resource


def get_selected_sort(
    query_args: Mapping[str, Any],
) -> str:
    selected_sort = get_query_value(
        query_args=query_args,
        name='sort',
        default='usage_percent',
    )

    allowed_values = {item['value'] for item in SORT_OPTIONS}

    if selected_sort not in allowed_values:
        return 'usage_percent'

    return selected_sort


class TopConsumersService(AnalyticsBaseService):
    def __init__(
        self,
        utilization_service: UtilizationService,
    ) -> None:
        self.utilization_service = utilization_service

    def get_prometheus_status(
        self,
    ) -> dict[str, Any]:
        return self.utilization_service.get_prometheus_status()

    def get_namespace_options(
        self,
    ) -> list[str]:
        result = self.get_prometheus_result(
            queries.NAMESPACE_ACTIVE_QUERY,
        )

        namespaces: set[str] = set()

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

            if (
                isinstance(
                    namespace,
                    str,
                )
                and namespace
            ):
                namespaces.add(
                    namespace,
                )

        return sorted(
            namespaces,
        )

    def get_top_consumers_payload(
        self,
        *,
        selected_namespace: str,
        selected_resource: str,
        selected_search: str,
        selected_sort: str,
        page: int,
        per_page: int,
    ) -> dict[str, Any]:
        cpu_rows = self.get_cpu_consumer_rows(
            selected_namespace=selected_namespace,
        )
        memory_rows = self.get_memory_consumer_rows(
            selected_namespace=selected_namespace,
        )
        pod_rows = self.get_pod_consumer_rows(
            selected_namespace=selected_namespace,
        )
        pvc_rows = self.get_pvc_consumer_rows(
            selected_namespace=selected_namespace,
        )

        all_rows = cpu_rows + memory_rows + pod_rows + pvc_rows
        filtered_rows = self.filter_rows(
            rows=all_rows,
            selected_search=selected_search,
            selected_resource=selected_resource,
        )
        sorted_rows = self.sort_rows(
            rows=filtered_rows,
            selected_sort=selected_sort,
        )

        ranked_rows = []
        for index, row in enumerate(
            sorted_rows,
            start=1,
        ):
            updated_row = dict(
                row,
            )
            updated_row['rank'] = index
            ranked_rows.append(
                updated_row,
            )

        page_payload = self.paginate_consumer_rows(
            rows=ranked_rows,
            page=page,
            per_page=per_page,
        )

        return {
            'has_data': bool(all_rows),
            'message': None,
            'summary': self.get_summary_cards(
                cpu_rows=cpu_rows,
                memory_rows=memory_rows,
                pod_rows=pod_rows,
                pvc_rows=pvc_rows,
            ),
            'overview': self.get_overview_payload(
                cpu_rows=cpu_rows,
                memory_rows=memory_rows,
                pod_rows=pod_rows,
                pvc_rows=pvc_rows,
                selected_namespace=selected_namespace,
            ),
            'rows': page_payload['rows'],
            'pagination': page_payload['pagination'],
            'recommendations': self.build_recommendations(
                rows=all_rows,
            ),
            'total_rows': len(filtered_rows),
        }

    def get_cpu_consumer_rows(
        self,
        selected_namespace: str,
    ) -> list[dict[str, Any]]:
        usage_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.TOP_CPU_CONSUMERS_QUERY,
            namespace_query=queries.TOP_CPU_CONSUMERS_BY_NAMESPACE_QUERY,
        )
        request_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.CPU_REQUEST_BY_CONTAINER_QUERY,
            namespace_query=queries.CPU_REQUEST_BY_CONTAINER_NAMESPACE_QUERY,
        )
        limit_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.CPU_LIMIT_BY_CONTAINER_QUERY,
            namespace_query=queries.CPU_LIMIT_BY_CONTAINER_NAMESPACE_QUERY,
        )

        request_map = self.get_container_value_map(
            query=request_query,
        )
        limit_map = self.get_container_value_map(
            query=limit_query,
        )

        rows: list[dict[str, Any]] = []

        for item in self.get_prometheus_result(usage_query):
            metric = self.get_metric_dict(
                item,
            )
            namespace = get_metric_label(
                metric,
                'namespace',
            )
            pod = get_metric_label(
                metric,
                'pod',
            )
            container = get_metric_label(
                metric,
                'container',
            )

            if not namespace or not pod or not container:
                continue

            key = get_container_key(
                namespace=namespace,
                pod=pod,
                container=container,
            )
            usage = self.extract_value(
                item,
            )
            request = request_map.get(
                key,
                0.0,
            )
            limit = limit_map.get(
                key,
                0.0,
            )
            usage_percent = get_usage_percent(
                usage=usage,
                request=request,
                limit=limit,
            )
            risk = get_usage_risk(
                usage_percent,
            )

            rows.append(
                self.build_consumer_row(
                    namespace=namespace,
                    workload=build_workload_label(
                        primary=container,
                        secondary=pod,
                    ),
                    resource_type='cpu',
                    current_usage=usage,
                    current_display=format_cpu(
                        usage,
                    ),
                    request=request,
                    request_display=format_cpu(
                        request,
                    )
                    if request > 0
                    else '-',
                    limit=limit,
                    limit_display=format_cpu(
                        limit,
                    )
                    if limit > 0
                    else '-',
                    usage_percent=usage_percent,
                    risk=risk,
                    recommendation=get_resource_recommendation(
                        resource_type='cpu',
                        usage_percent=usage_percent,
                        request=request,
                        limit=limit,
                    ),
                    pod=pod,
                    container=container,
                )
            )

        return rows

    def get_memory_consumer_rows(
        self,
        selected_namespace: str,
    ) -> list[dict[str, Any]]:
        usage_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.TOP_MEMORY_CONSUMERS_QUERY,
            namespace_query=queries.TOP_MEMORY_CONSUMERS_BY_NAMESPACE_QUERY,
        )
        request_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.MEMORY_REQUEST_BY_CONTAINER_QUERY,
            namespace_query=queries.MEMORY_REQUEST_BY_CONTAINER_NAMESPACE_QUERY,
        )
        limit_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.MEMORY_LIMIT_BY_CONTAINER_QUERY,
            namespace_query=queries.MEMORY_LIMIT_BY_CONTAINER_NAMESPACE_QUERY,
        )

        request_map = self.get_container_value_map(
            query=request_query,
        )
        limit_map = self.get_container_value_map(
            query=limit_query,
        )

        rows: list[dict[str, Any]] = []

        for item in self.get_prometheus_result(usage_query):
            metric = self.get_metric_dict(
                item,
            )
            namespace = get_metric_label(
                metric,
                'namespace',
            )
            pod = get_metric_label(
                metric,
                'pod',
            )
            container = get_metric_label(
                metric,
                'container',
            )

            if not namespace or not pod or not container:
                continue

            key = get_container_key(
                namespace=namespace,
                pod=pod,
                container=container,
            )
            usage = self.extract_value(
                item,
            )
            request = request_map.get(
                key,
                0.0,
            )
            limit = limit_map.get(
                key,
                0.0,
            )
            usage_percent = get_usage_percent(
                usage=usage,
                request=request,
                limit=limit,
            )
            risk = get_usage_risk(
                usage_percent,
            )

            rows.append(
                self.build_consumer_row(
                    namespace=namespace,
                    workload=build_workload_label(
                        primary=container,
                        secondary=pod,
                    ),
                    resource_type='memory',
                    current_usage=usage,
                    current_display=format_bytes(
                        usage,
                    ),
                    request=request,
                    request_display=format_bytes(
                        request,
                    )
                    if request > 0
                    else '-',
                    limit=limit,
                    limit_display=format_bytes(
                        limit,
                    )
                    if limit > 0
                    else '-',
                    usage_percent=usage_percent,
                    risk=risk,
                    recommendation=get_resource_recommendation(
                        resource_type='memory',
                        usage_percent=usage_percent,
                        request=request,
                        limit=limit,
                    ),
                    pod=pod,
                    container=container,
                )
            )

        return rows

    def get_pod_consumer_rows(
        self,
        selected_namespace: str,
    ) -> list[dict[str, Any]]:
        usage_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.TOP_POD_CONSUMERS_QUERY,
            namespace_query=queries.TOP_POD_CONSUMERS_BY_NAMESPACE_QUERY,
        )
        pod_capacity = self.get_prometheus_scalar(
            queries.POD_CAPACITY_QUERY,
        )

        rows: list[dict[str, Any]] = []

        for item in self.get_prometheus_result(usage_query):
            metric = self.get_metric_dict(
                item,
            )
            namespace = get_metric_label(
                metric,
                'namespace',
            )

            if not namespace:
                continue

            usage = self.extract_value(
                item,
            )
            usage_percent = raw_percent(
                usage,
                pod_capacity,
            )
            risk = get_usage_risk(
                usage_percent,
            )

            rows.append(
                self.build_consumer_row(
                    namespace=namespace,
                    workload=namespace,
                    resource_type='pods',
                    current_usage=usage,
                    current_display=f'{int(usage)} pods',
                    request=0,
                    request_display='-',
                    limit=pod_capacity,
                    limit_display=f'{int(pod_capacity)} pods' if pod_capacity > 0 else '-',
                    usage_percent=usage_percent,
                    risk=risk,
                    recommendation=get_resource_recommendation(
                        resource_type='pods',
                        usage_percent=usage_percent,
                        request=0,
                        limit=pod_capacity,
                    ),
                    pod='',
                    container='',
                )
            )

        return rows

    def get_pvc_consumer_rows(
        self,
        selected_namespace: str,
    ) -> list[dict[str, Any]]:
        usage_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.TOP_PVC_CONSUMERS_QUERY,
            namespace_query=queries.TOP_PVC_CONSUMERS_BY_NAMESPACE_QUERY,
        )
        capacity_query = render_namespace_query(
            namespace=selected_namespace,
            all_query=queries.PVC_CAPACITY_BY_CLAIM_QUERY,
            namespace_query=queries.PVC_CAPACITY_BY_CLAIM_NAMESPACE_QUERY,
        )

        capacity_map = self.get_pvc_value_map(
            query=capacity_query,
        )

        rows: list[dict[str, Any]] = []

        for item in self.get_prometheus_result(usage_query):
            metric = self.get_metric_dict(
                item,
            )
            namespace = get_metric_label(
                metric,
                'namespace',
            )
            pvc_name = get_metric_label(
                metric,
                'persistentvolumeclaim',
            )

            if not namespace or not pvc_name:
                continue

            key = get_pvc_key(
                namespace=namespace,
                pvc_name=pvc_name,
            )
            usage = self.extract_value(
                item,
            )
            capacity = capacity_map.get(
                key,
                0.0,
            )
            usage_percent = raw_percent(
                usage,
                capacity,
            )
            risk = get_usage_risk(
                usage_percent,
            )

            rows.append(
                self.build_consumer_row(
                    namespace=namespace,
                    workload=pvc_name,
                    resource_type='pvc',
                    current_usage=usage,
                    current_display=format_bytes(
                        usage,
                    ),
                    request=0,
                    request_display='-',
                    limit=capacity,
                    limit_display=format_bytes(
                        capacity,
                    )
                    if capacity > 0
                    else '-',
                    usage_percent=usage_percent,
                    risk=risk,
                    recommendation=get_resource_recommendation(
                        resource_type='pvc',
                        usage_percent=usage_percent,
                        request=0,
                        limit=capacity,
                    ),
                    pod='',
                    container='',
                )
            )

        return rows

    def build_consumer_row(
        self,
        *,
        namespace: str,
        workload: str,
        resource_type: str,
        current_usage: float,
        current_display: str,
        request: float,
        request_display: str,
        limit: float,
        limit_display: str,
        usage_percent: float,
        risk: dict[str, str],
        recommendation: str,
        pod: str,
        container: str,
    ) -> dict[str, Any]:
        return {
            'rank': 0,
            'namespace': namespace,
            'workload': workload,
            'pod': pod,
            'container': container,
            'resource_type': resource_type,
            'resource_label': RESOURCE_LABELS.get(
                resource_type,
                resource_type.title(),
            ),
            'resource_icon': RESOURCE_ICONS.get(
                resource_type,
                'activity',
            ),
            'resource_class': RESOURCE_BADGE_CLASSES.get(
                resource_type,
                'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
            ),
            'current_usage': current_usage,
            'current_display': current_display,
            'request': request,
            'request_display': request_display,
            'limit': limit,
            'limit_display': limit_display,
            'usage_percent': safe_round(
                usage_percent,
                1,
            ),
            'usage_bar_percent': min(
                safe_round(
                    usage_percent,
                    1,
                ),
                100,
            ),
            'risk': risk,
            'recommendation': recommendation,
        }

    def get_container_value_map(
        self,
        query: str,
    ) -> dict[str, float]:
        values: dict[str, float] = {}

        for item in self.get_prometheus_result(query):
            metric = self.get_metric_dict(
                item,
            )
            namespace = get_metric_label(
                metric,
                'namespace',
            )
            pod = get_metric_label(
                metric,
                'pod',
            )
            container = get_metric_label(
                metric,
                'container',
            )

            if not namespace or not pod or not container:
                continue

            values[
                get_container_key(
                    namespace=namespace,
                    pod=pod,
                    container=container,
                )
            ] = self.extract_value(
                item,
            )

        return values

    def get_pvc_value_map(
        self,
        query: str,
    ) -> dict[str, float]:
        values: dict[str, float] = {}

        for item in self.get_prometheus_result(query):
            metric = self.get_metric_dict(
                item,
            )
            namespace = get_metric_label(
                metric,
                'namespace',
            )
            pvc_name = get_metric_label(
                metric,
                'persistentvolumeclaim',
            )

            if not namespace or not pvc_name:
                continue

            values[
                get_pvc_key(
                    namespace=namespace,
                    pvc_name=pvc_name,
                )
            ] = self.extract_value(
                item,
            )

        return values

    def get_metric_dict(
        self,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        metric = item.get(
            'metric',
            {},
        )

        if isinstance(
            metric,
            dict,
        ):
            return metric

        return {}

    def get_summary_cards(
        self,
        *,
        cpu_rows: list[dict[str, Any]],
        memory_rows: list[dict[str, Any]],
        pod_rows: list[dict[str, Any]],
        pvc_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cpu_allocatable = self.get_prometheus_scalar(
            queries.CPU_ALLOCATABLE_QUERY,
        )
        memory_allocatable = self.get_prometheus_scalar(
            queries.MEMORY_ALLOCATABLE_QUERY,
        )
        pod_capacity = self.get_prometheus_scalar(
            queries.POD_CAPACITY_QUERY,
        )

        return {
            'highest_cpu': build_summary_card(
                rows=cpu_rows,
                title='Highest CPU Consumer',
                empty_label='No CPU data',
                empty_value='0 cores',
                capacity=cpu_allocatable,
                capacity_text='of cluster allocatable CPU',
            ),
            'highest_memory': build_summary_card(
                rows=memory_rows,
                title='Highest Memory Consumer',
                empty_label='No memory data',
                empty_value='0 B',
                capacity=memory_allocatable,
                capacity_text='of cluster allocatable memory',
            ),
            'highest_pods': build_summary_card(
                rows=pod_rows,
                title='Highest Pod Count',
                empty_label='No pod data',
                empty_value='0 pods',
                capacity=pod_capacity,
                capacity_text='of total pod capacity',
            ),
            'highest_pvc': build_summary_card(
                rows=pvc_rows,
                title='Highest PVC Usage',
                empty_label='No PVC data',
                empty_value='0%',
                capacity=None,
                capacity_text='PVC usage',
                use_usage_percent=True,
            ),
        }

    def get_overview_payload(
        self,
        *,
        cpu_rows: list[dict[str, Any]],
        memory_rows: list[dict[str, Any]],
        pod_rows: list[dict[str, Any]],
        pvc_rows: list[dict[str, Any]],
        selected_namespace: str,
    ) -> dict[str, Any]:
        total_cpu_usage = self.get_prometheus_scalar(
            render_namespace_query(
                namespace=selected_namespace,
                all_query=queries.TOTAL_CPU_USAGE_QUERY,
                namespace_query=queries.TOTAL_CPU_USAGE_BY_NAMESPACE_QUERY,
            )
        )
        total_memory_usage = self.get_prometheus_scalar(
            render_namespace_query(
                namespace=selected_namespace,
                all_query=queries.TOTAL_MEMORY_USAGE_QUERY,
                namespace_query=queries.TOTAL_MEMORY_USAGE_BY_NAMESPACE_QUERY,
            )
        )
        total_running_pods = self.get_prometheus_scalar(
            render_namespace_query(
                namespace=selected_namespace,
                all_query=queries.TOTAL_RUNNING_PODS_QUERY,
                namespace_query=queries.TOTAL_RUNNING_PODS_BY_NAMESPACE_QUERY,
            )
        )
        total_pvc_used = self.get_prometheus_scalar(
            render_namespace_query(
                namespace=selected_namespace,
                all_query=queries.TOTAL_PVC_USED_QUERY,
                namespace_query=queries.TOTAL_PVC_USED_BY_NAMESPACE_QUERY,
            )
        )
        total_pvc_capacity = self.get_prometheus_scalar(
            render_namespace_query(
                namespace=selected_namespace,
                all_query=queries.TOTAL_PVC_CAPACITY_QUERY,
                namespace_query=queries.TOTAL_PVC_CAPACITY_BY_NAMESPACE_QUERY,
            )
        )
        cpu_allocatable = self.get_prometheus_scalar(
            queries.CPU_ALLOCATABLE_QUERY,
        )
        memory_allocatable = self.get_prometheus_scalar(
            queries.MEMORY_ALLOCATABLE_QUERY,
        )
        pod_capacity = self.get_prometheus_scalar(
            queries.POD_CAPACITY_QUERY,
        )

        return {
            'cpu_chart': build_chart_series(
                rows=cpu_rows,
                unit='cores',
            ),
            'memory_chart': build_chart_series(
                rows=memory_rows,
                unit='bytes',
            ),
            'summary': {
                'total_cpu_used': format_cpu(
                    total_cpu_usage,
                ),
                'total_cpu_percent': safe_round(
                    raw_percent(
                        total_cpu_usage,
                        cpu_allocatable,
                    ),
                    1,
                ),
                'total_memory_used': format_bytes(
                    total_memory_usage,
                ),
                'total_memory_percent': safe_round(
                    raw_percent(
                        total_memory_usage,
                        memory_allocatable,
                    ),
                    1,
                ),
                'total_pods': int(
                    total_running_pods,
                ),
                'total_pods_percent': safe_round(
                    raw_percent(
                        total_running_pods,
                        pod_capacity,
                    ),
                    1,
                ),
                'total_pvc_used': format_bytes(
                    total_pvc_used,
                ),
                'total_pvc_percent': safe_round(
                    raw_percent(
                        total_pvc_used,
                        total_pvc_capacity,
                    ),
                    1,
                ),
            },
        }

    def filter_rows(
        self,
        *,
        rows: list[dict[str, Any]],
        selected_search: str,
        selected_resource: str,
    ) -> list[dict[str, Any]]:
        filtered_rows: list[dict[str, Any]] = []

        for row in rows:
            if (
                selected_resource != 'all'
                and row.get(
                    'resource_type',
                )
                != selected_resource
            ):
                continue

            if selected_search:
                haystack = ' '.join(
                    str(
                        row.get(
                            key,
                            '',
                        )
                    )
                    for key in [
                        'namespace',
                        'workload',
                        'pod',
                        'container',
                        'resource_label',
                        'recommendation',
                    ]
                ).lower()

                if selected_search.lower() not in haystack:
                    continue

            filtered_rows.append(
                row,
            )

        return filtered_rows

    def sort_rows(
        self,
        *,
        rows: list[dict[str, Any]],
        selected_sort: str,
    ) -> list[dict[str, Any]]:
        if selected_sort == 'usage':
            return sorted(
                rows,
                key=lambda row: float(row.get('current_usage', 0)),
                reverse=True,
            )

        if selected_sort == 'risk':
            return sorted(
                rows,
                key=lambda row: RISK_RANK.get(
                    str(row.get('risk', {}).get('key', 'unknown')),
                    0,
                ),
                reverse=True,
            )

        if selected_sort == 'namespace':
            return sorted(
                rows,
                key=lambda row: str(row.get('namespace', '')),
            )

        if selected_sort == 'resource':
            return sorted(
                rows,
                key=lambda row: str(row.get('resource_type', '')),
            )

        return sorted(
            rows,
            key=lambda row: float(row.get('usage_percent', 0)),
            reverse=True,
        )

    def paginate_consumer_rows(
        self,
        *,
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

    def build_recommendations(
        self,
        *,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        missing_requests = [row for row in rows if row['resource_type'] in ['cpu', 'memory'] and row['request'] <= 0]
        high_pvc = [row for row in rows if row['resource_type'] == 'pvc' and row['usage_percent'] >= 80]
        high_usage = [row for row in rows if row['resource_type'] in ['cpu', 'memory'] and row['usage_percent'] >= 75]
        namespace_totals: dict[str, float] = {}
        for row in rows:
            namespace = str(row.get('namespace', ''))
            namespace_totals[namespace] = namespace_totals.get(
                namespace,
                0,
            ) + float(row.get('current_usage', 0))

        dominant_namespaces = [namespace for namespace, value in namespace_totals.items() if value > 0 and namespace][
            :2
        ]

        recommendations = [
            {
                'level': 'warning' if missing_requests else 'normal',
                'icon': 'activity',
                'title': 'Add Missing Requests',
                'description': (
                    f'{len(missing_requests)} workloads are missing CPU or memory requests. '
                    'Setting requests improves scheduling and prevents resource contention.'
                )
                if missing_requests
                else 'CPU and memory requests are available for the visible top consumers.',
                'action_label': 'View Missing Requests',
            },
            {
                'level': 'warning' if high_usage else 'normal',
                'icon': 'scale',
                'title': 'Review High Usage Workloads',
                'description': (
                    f'{len(high_usage)} workloads are above the warning threshold. '
                    'Review requests, limits, and workload efficiency.'
                )
                if high_usage
                else 'No high CPU or memory consumers are above the warning threshold.',
                'action_label': 'View High Usage',
            },
            {
                'level': 'warning' if dominant_namespaces else 'normal',
                'icon': 'network',
                'title': 'Investigate Dominant Namespaces',
                'description': (
                    f'{len(dominant_namespaces)} namespaces dominate the visible top consumers. '
                    'Review distribution and apply quotas if needed.'
                )
                if dominant_namespaces
                else 'No dominant namespace pattern detected in the current selection.',
                'action_label': 'View Namespaces',
            },
            {
                'level': 'critical' if high_pvc else 'normal',
                'icon': 'database',
                'title': 'Expand or Clean High PVC Usage',
                'description': (
                    f'{len(high_pvc)} PVCs are using over 80% of their capacity. '
                    'Clean up unused data or expand storage to avoid service disruption.'
                )
                if high_pvc
                else 'PVC usage is within the expected range for the visible consumers.',
                'action_label': 'View High PVCs',
            },
        ]

        return recommendations


def get_top_consumers_context(
    query_args: Mapping[str, Any],
) -> dict[str, Any]:
    _, _, utilization_service, context = build_analysis_utilization_context(
        query_args=query_args,
    )

    selected_namespace = get_query_value(
        query_args=query_args,
        name='namespace',
        default='',
    )
    selected_resource = get_selected_resource(
        query_args=query_args,
    )
    selected_time_range = get_selected_time_range(
        query_args=query_args,
    )
    selected_search = get_query_value(
        query_args=query_args,
        name='search',
        default='',
    )
    selected_sort = get_selected_sort(
        query_args=query_args,
    )
    page = get_positive_int_arg(
        query_args=query_args,
        name='page',
        default=1,
    )
    per_page = get_per_page_arg(
        query_args=query_args,
        name='per_page',
        default=10,
    )

    context.update(
        {
            'selected_namespace': selected_namespace,
            'selected_resource': selected_resource,
            'selected_time_range': selected_time_range,
            'selected_search': selected_search,
            'selected_sort': selected_sort,
            'resource_options': RESOURCE_OPTIONS,
            'sort_options': SORT_OPTIONS,
            'allowed_time_ranges': get_allowed_time_ranges(),
            'allowed_per_page_values': ALLOWED_PER_PAGE_VALUES,
            'namespace_options': [],
            'prometheus_status': {
                'connected': False,
                'label': 'No Cluster',
                'response_time_ms': None,
                'error': None,
            },
            'prometheus_connected': False,
            'consumer_payload': get_empty_top_consumers_payload(
                message='No cluster available. Add a Kubernetes cluster first.',
                page=page,
                per_page=per_page,
            ),
        }
    )

    if utilization_service is None:
        return context

    top_consumers_service = TopConsumersService(
        utilization_service=utilization_service,
    )

    try:
        prometheus_status = top_consumers_service.get_prometheus_status()
    except PrometheusError as exc:
        prometheus_status = {
            'connected': False,
            'label': 'Prometheus Disconnected',
            'response_time_ms': None,
            'error': str(exc),
        }
    except Exception as exc:
        prometheus_status = {
            'connected': False,
            'label': 'Prometheus Error',
            'response_time_ms': None,
            'error': str(exc),
        }

    context['prometheus_status'] = prometheus_status
    context['prometheus_connected'] = bool(
        prometheus_status.get(
            'connected',
            False,
        )
    )

    if not prometheus_status.get(
        'connected',
        False,
    ):
        context['consumer_payload'] = get_empty_top_consumers_payload(
            message=safe_message(
                value=prometheus_status.get(
                    'error',
                ),
                default='Prometheus is not connected for the selected cluster.',
            ),
            page=page,
            per_page=per_page,
        )

        return context

    try:
        namespace_options = top_consumers_service.get_namespace_options()
    except Exception:
        namespace_options = []

    if selected_namespace and selected_namespace not in namespace_options:
        selected_namespace = ''

    context['selected_namespace'] = selected_namespace
    context['namespace_options'] = namespace_options

    try:
        consumer_payload = top_consumers_service.get_top_consumers_payload(
            selected_namespace=selected_namespace,
            selected_resource=selected_resource,
            selected_search=selected_search,
            selected_sort=selected_sort,
            page=page,
            per_page=per_page,
        )
    except PrometheusError as exc:
        consumer_payload = get_empty_top_consumers_payload(
            message=str(
                exc,
            ),
            page=page,
            per_page=per_page,
        )
    except Exception as exc:
        consumer_payload = get_empty_top_consumers_payload(
            message=f'Top consumers query failed: {exc}',
            page=page,
            per_page=per_page,
        )

    context['consumer_payload'] = consumer_payload

    return context


def render_namespace_query(
    *,
    namespace: str,
    all_query: str,
    namespace_query: str,
) -> str:
    if not namespace:
        return all_query

    escaped_namespace = namespace.replace(
        '\\',
        '\\\\',
    ).replace(
        '"',
        '\\"',
    )

    return namespace_query.replace(
        '$namespace',
        escaped_namespace,
    )


def get_metric_label(
    metric: dict[str, Any],
    label: str,
) -> str:
    value = metric.get(
        label,
        '',
    )

    if isinstance(
        value,
        str,
    ):
        return value

    return ''


def get_container_key(
    *,
    namespace: str,
    pod: str,
    container: str,
) -> str:
    return f'{namespace}/{pod}/{container}'


def get_pvc_key(
    *,
    namespace: str,
    pvc_name: str,
) -> str:
    return f'{namespace}/{pvc_name}'


def build_workload_label(
    *,
    primary: str,
    secondary: str,
) -> str:
    if primary and secondary:
        return f'{primary} / {secondary}'

    return primary or secondary or '-'


def get_usage_percent(
    *,
    usage: float,
    request: float,
    limit: float,
) -> float:
    if limit > 0:
        return raw_percent(
            usage,
            limit,
        )

    if request > 0:
        return raw_percent(
            usage,
            request,
        )

    return 0.0


def get_usage_risk(
    percent: float,
) -> dict[str, str]:
    if percent >= 90:
        return {
            'key': 'critical',
            'label': 'Critical',
            'class': 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
        }

    if percent >= 75:
        return {
            'key': 'warning',
            'label': 'Warning',
            'class': 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
        }

    return {
        'key': 'normal',
        'label': 'Normal',
        'class': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
    }


def get_resource_recommendation(
    *,
    resource_type: str,
    usage_percent: float,
    request: float,
    limit: float,
) -> str:
    if resource_type == 'pvc':
        if usage_percent >= 90:
            return 'Clean up or expand PVC'
        if usage_percent >= 75:
            return 'Expand PVC capacity'
        return 'Monitor storage growth'

    if resource_type == 'pods':
        if usage_percent >= 75:
            return 'Review pod capacity'
        return 'Monitor growth'

    if request <= 0:
        if resource_type == 'cpu':
            return 'Add CPU request'
        return 'Add memory request'

    if limit <= 0:
        if resource_type == 'cpu':
            return 'Add CPU limit'
        return 'Add memory limit'

    if usage_percent >= 90:
        if resource_type == 'cpu':
            return 'Increase CPU limit'
        return 'Increase memory limit'

    if usage_percent >= 75:
        if resource_type == 'cpu':
            return 'Increase CPU request/limit'
        return 'Increase memory request/limit'

    return 'Monitor growth'


def build_summary_card(
    *,
    rows: list[dict[str, Any]],
    title: str,
    empty_label: str,
    empty_value: str,
    capacity: float | None,
    capacity_text: str,
    use_usage_percent: bool = False,
) -> dict[str, Any]:
    if not rows:
        return {
            'title': title,
            'label': empty_label,
            'value': empty_value,
            'subtitle': 'No data available',
            'risk': get_usage_risk(0),
        }

    top_row = max(
        rows,
        key=lambda row: float(row.get('current_usage', 0)),
    )

    if use_usage_percent:
        value = f'{float(top_row.get("usage_percent", 0)):.1f}%'
        subtitle = f'{top_row.get("current_display", "-")} of {top_row.get("limit_display", "-")} used'
    else:
        value = str(
            top_row.get(
                'current_display',
                '-',
            )
        )
        percent = raw_percent(
            float(
                top_row.get(
                    'current_usage',
                    0,
                )
            ),
            capacity or 0,
        )
        subtitle = f'{safe_round(percent, 1)}% {capacity_text}'

    return {
        'title': title,
        'label': str(
            top_row.get(
                'workload',
                '-',
            )
        ),
        'value': value,
        'subtitle': subtitle,
        'risk': top_row.get(
            'risk',
            get_usage_risk(0),
        ),
    }


def build_chart_series(
    *,
    rows: list[dict[str, Any]],
    unit: str,
) -> dict[str, Any]:
    top_rows = sorted(
        rows,
        key=lambda row: float(row.get('current_usage', 0)),
        reverse=True,
    )[:10]

    values: list[float] = []

    for row in top_rows:
        value = float(
            row.get(
                'current_usage',
                0,
            )
        )

        if unit == 'bytes':
            value = value / (1024**3)

        values.append(
            safe_round(
                value,
                2,
            )
        )

    return {
        'labels': [
            str(
                row.get(
                    'workload',
                    '-',
                )
            )[:42]
            for row in top_rows
        ],
        'values': values,
    }


def get_empty_top_consumers_payload(
    *,
    message: str,
    page: int,
    per_page: int,
) -> dict[str, Any]:
    return {
        'has_data': False,
        'message': message,
        'summary': {
            'highest_cpu': {
                'title': 'Highest CPU Consumer',
                'label': 'No CPU data',
                'value': '0 cores',
                'subtitle': 'No data available',
                'risk': get_usage_risk(0),
            },
            'highest_memory': {
                'title': 'Highest Memory Consumer',
                'label': 'No memory data',
                'value': '0 B',
                'subtitle': 'No data available',
                'risk': get_usage_risk(0),
            },
            'highest_pods': {
                'title': 'Highest Pod Count',
                'label': 'No pod data',
                'value': '0 pods',
                'subtitle': 'No data available',
                'risk': get_usage_risk(0),
            },
            'highest_pvc': {
                'title': 'Highest PVC Usage',
                'label': 'No PVC data',
                'value': '0%',
                'subtitle': 'No data available',
                'risk': get_usage_risk(0),
            },
        },
        'overview': {
            'cpu_chart': {
                'labels': [],
                'values': [],
            },
            'memory_chart': {
                'labels': [],
                'values': [],
            },
            'summary': {
                'total_cpu_used': '0 cores',
                'total_cpu_percent': 0,
                'total_memory_used': '0 B',
                'total_memory_percent': 0,
                'total_pods': 0,
                'total_pods_percent': 0,
                'total_pvc_used': '0 B',
                'total_pvc_percent': 0,
            },
        },
        'rows': [],
        'pagination': {
            'current_page': page,
            'total_pages': 1,
            'total_items': 0,
            'per_page': per_page,
            'has_prev': False,
            'has_next': False,
            'prev_page': 1,
            'next_page': 1,
        },
        'recommendations': [
            {
                'level': 'warning',
                'icon': 'plug-zap',
                'title': 'Connect Prometheus Metrics',
                'description': 'Top consumer analysis requires Prometheus metrics to calculate CPU, memory, pod, and PVC usage.',
                'action_label': 'Review Prometheus',
            }
        ],
        'total_rows': 0,
    }


def safe_message(
    *,
    value: Any,
    default: str,
) -> str:
    if (
        isinstance(
            value,
            str,
        )
        and value
    ):
        return value

    if value is None:
        return default

    return str(
        value,
    )


def format_cpu(
    value: float,
) -> str:
    return f'{safe_round(value, 2)} cores'


def format_bytes(
    value: float,
) -> str:
    if value <= 0:
        return '0 B'

    units = [
        'B',
        'KiB',
        'MiB',
        'GiB',
        'TiB',
        'PiB',
    ]
    size = float(value)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f'{size:.0f} {units[unit_index]}'

    return f'{size:.2f} {units[unit_index]}'
