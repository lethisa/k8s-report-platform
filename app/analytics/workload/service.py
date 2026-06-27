# app/analytics/workload/service.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.analytics.capacity import queries
from app.analytics.capacity.service import (
    ALLOWED_PER_PAGE_VALUES,
    CapacityService,
    get_empty_capacity_payload,
    get_per_page_arg,
    get_positive_int_arg,
    get_query_value,
    get_selected_time_range,
)
from app.analytics.common.base_service import (
    AnalyticsBaseService,
    bytes_to_gib,
    raw_percent,
    safe_percent,
    safe_round,
)
from app.analytics.common.context import build_analysis_utilization_context
from app.analytics.utilization.service import UtilizationService

REQUIRED_QUOTA_KEYS = [
    'requests.cpu',
    'limits.cpu',
    'requests.memory',
    'limits.memory',
    'pods',
]


def get_allowed_time_ranges() -> list[dict[str, str]]:
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


def filter_tenant_quota_rows(
    rows: list[dict[str, Any]],
    selected_search: str = '',
    selected_quota_status: str = '',
    selected_risk: str = '',
) -> list[dict[str, Any]]:
    filtered_rows: list[dict[str, Any]] = []

    for row in rows:
        if (
            selected_search
            and selected_search.lower()
            not in str(
                row.get(
                    'namespace',
                    '',
                )
            ).lower()
        ):
            continue

        if (
            selected_quota_status
            and row.get(
                'quota_status',
                {},
            ).get(
                'label',
            )
            != selected_quota_status
        ):
            continue

        if (
            selected_risk
            and row.get(
                'risk',
                {},
            ).get(
                'label',
            )
            != selected_risk
        ):
            continue

        filtered_rows.append(
            row,
        )

    return filtered_rows


def filter_workload_rows(
    rows: list[dict[str, Any]],
    selected_search: str = '',
    selected_type: str = '',
    selected_resource_status: str = '',
    selected_qos: str = '',
    selected_risk: str = '',
) -> list[dict[str, Any]]:
    filtered_rows: list[dict[str, Any]] = []

    for row in rows:
        if selected_search:
            haystack = (f"{row.get('workload', '')} " f"{row.get('namespace', '')}").lower()

            if selected_search.lower() not in haystack:
                continue

        if (
            selected_type
            and row.get(
                'type',
            )
            != selected_type
        ):
            continue

        if (
            selected_resource_status
            and row.get(
                'resource_status',
                {},
            ).get(
                'label',
            )
            != selected_resource_status
        ):
            continue

        if (
            selected_qos
            and row.get(
                'qos',
                {},
            ).get(
                'label',
            )
            != selected_qos
        ):
            continue

        if (
            selected_risk
            and row.get(
                'risk',
                {},
            ).get(
                'label',
            )
            != selected_risk
        ):
            continue

        filtered_rows.append(
            row,
        )

    return filtered_rows


class WorkloadAnalysisService(AnalyticsBaseService):
    def __init__(
        self,
        utilization_service: UtilizationService,
    ) -> None:
        self.utilization_service = utilization_service
        self.capacity_service = CapacityService(
            utilization_service,
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

            rows.append(
                {
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

    def get_workload_mapping_payload(
        self,
        selected_namespace: str,
        time_range: str,
    ) -> dict[str, Any]:
        return self.capacity_service.get_workload_mapping_payload(
            selected_namespace=selected_namespace,
            time_range=time_range,
        )

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

    def get_governance_findings(
        self,
        tenant_quota_rows: list[dict[str, Any]],
        workload_mapping_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self.capacity_service.get_governance_findings(
            tenant_quota_rows=tenant_quota_rows,
            workload_mapping_rows=workload_mapping_rows,
        )

    def get_recommendation_cards(
        self,
        capacity_summary: dict[str, dict[str, float]],
        tenant_quota_rows: list[dict[str, Any]],
        workload_mapping_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self.capacity_service.get_recommendation_cards(
            capacity_summary=capacity_summary,
            tenant_quota_rows=tenant_quota_rows,
            workload_mapping_rows=workload_mapping_rows,
        )


def get_workload_analysis_context(
    query_args: Mapping[str, Any],
) -> dict[str, Any]:
    _, _, utilization_service, context = build_analysis_utilization_context(
        query_args=query_args,
    )

    workload_service: WorkloadAnalysisService | None = None

    if utilization_service is not None:
        workload_service = WorkloadAnalysisService(
            utilization_service,
        )

    selected_namespace = get_query_value(
        query_args=query_args,
        name='namespace',
        default='',
    )

    selected_time_range = get_selected_time_range(
        query_args=query_args,
    )

    selected_tenant_search = get_query_value(
        query_args=query_args,
        name='tenant_search',
        default='',
    )

    selected_tenant_quota_status = get_query_value(
        query_args=query_args,
        name='tenant_quota_status',
        default='',
    )

    selected_tenant_risk = get_query_value(
        query_args=query_args,
        name='tenant_risk',
        default='',
    )

    selected_workload_search = get_query_value(
        query_args=query_args,
        name='workload_search',
        default='',
    )

    selected_workload_type = get_query_value(
        query_args=query_args,
        name='workload_type',
        default='',
    )

    selected_workload_resource_status = get_query_value(
        query_args=query_args,
        name='workload_resource_status',
        default='',
    )

    selected_workload_qos = get_query_value(
        query_args=query_args,
        name='workload_qos',
        default='',
    )

    selected_workload_risk = get_query_value(
        query_args=query_args,
        name='workload_risk',
        default='',
    )

    context.update(
        {
            'selected_namespace': selected_namespace,
            'selected_time_range': selected_time_range,
            'selected_tenant_search': selected_tenant_search,
            'selected_tenant_quota_status': selected_tenant_quota_status,
            'selected_tenant_risk': selected_tenant_risk,
            'selected_workload_search': selected_workload_search,
            'selected_workload_type': selected_workload_type,
            'selected_workload_resource_status': selected_workload_resource_status,
            'selected_workload_qos': selected_workload_qos,
            'selected_workload_risk': selected_workload_risk,
            'allowed_time_ranges': get_allowed_time_ranges(),
            'namespace_options': [],
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
            'recommendation_cards': [],
            'governance_findings': [],
        }
    )

    if workload_service is None:
        context.update(
            get_empty_capacity_payload(
                selected_namespace=selected_namespace,
                selected_time_range=selected_time_range,
            )
        )

        return context

    prometheus_status = workload_service.get_prometheus_status()

    context['prometheus_status'] = prometheus_status
    context['prometheus_connected'] = bool(
        prometheus_status.get(
            'connected',
            False,
        )
    )

    tenant_quota_summary = workload_service.get_tenant_quota_summary(
        selected_namespace=selected_namespace,
    )

    tenant_quota_all_rows = tenant_quota_summary['rows']

    tenant_quota_filtered_rows = filter_tenant_quota_rows(
        rows=tenant_quota_all_rows,
        selected_search=selected_tenant_search,
        selected_quota_status=selected_tenant_quota_status,
        selected_risk=selected_tenant_risk,
    )

    tenant_quota_page = workload_service.paginate_rows(
        rows=tenant_quota_filtered_rows,
        page=get_positive_int_arg(
            query_args=query_args,
            name='quota_page',
            default=1,
        ),
        per_page=get_per_page_arg(
            query_args=query_args,
            name='quota_per_page',
            default=10,
        ),
    )

    tenant_quota_summary['rows'] = tenant_quota_page['rows']
    tenant_quota_summary['pagination'] = tenant_quota_page['pagination']

    workload_mapping_payload = workload_service.get_workload_mapping_payload(
        selected_namespace=selected_namespace,
        time_range=selected_time_range,
    )

    workload_mapping_all_rows = workload_mapping_payload['rows']

    workload_mapping_filtered_rows = filter_workload_rows(
        rows=workload_mapping_all_rows,
        selected_search=selected_workload_search,
        selected_type=selected_workload_type,
        selected_resource_status=selected_workload_resource_status,
        selected_qos=selected_workload_qos,
        selected_risk=selected_workload_risk,
    )

    workload_mapping_page = workload_service.paginate_rows(
        rows=workload_mapping_filtered_rows,
        page=get_positive_int_arg(
            query_args=query_args,
            name='workload_page',
            default=1,
        ),
        per_page=get_per_page_arg(
            query_args=query_args,
            name='workload_per_page',
            default=10,
        ),
    )

    workload_mapping_payload['rows'] = workload_mapping_page['rows']
    workload_mapping_payload['pagination'] = workload_mapping_page['pagination']
    workload_mapping_payload['workload_type_options'] = sorted(
        {
            row.get(
                'type',
                '',
            )
            for row in workload_mapping_all_rows
            if row.get(
                'type',
            )
        }
    )
    workload_mapping_payload['resource_status_options'] = sorted(
        {
            row.get(
                'resource_status',
                {},
            ).get(
                'label',
                '',
            )
            for row in workload_mapping_all_rows
            if row.get(
                'resource_status',
            )
        }
    )
    workload_mapping_payload['qos_options'] = sorted(
        {
            row.get(
                'qos',
                {},
            ).get(
                'label',
                '',
            )
            for row in workload_mapping_all_rows
            if row.get(
                'qos',
            )
        }
    )
    workload_mapping_payload['risk_options'] = sorted(
        {
            row.get(
                'risk',
                {},
            ).get(
                'label',
                '',
            )
            for row in workload_mapping_all_rows
            if row.get(
                'risk',
            )
        }
    )

    namespace_options = workload_service.get_all_namespace_options()

    quota_status_options = sorted(
        {
            row.get(
                'quota_status',
                {},
            ).get(
                'label',
                '',
            )
            for row in tenant_quota_all_rows
            if row.get(
                'quota_status',
            )
        }
    )

    tenant_risk_options = sorted(
        {
            row.get(
                'risk',
                {},
            ).get(
                'label',
                '',
            )
            for row in tenant_quota_all_rows
            if row.get(
                'risk',
            )
        }
    )

    governance_findings = workload_service.get_governance_findings(
        tenant_quota_rows=tenant_quota_all_rows,
        workload_mapping_rows=workload_mapping_all_rows,
    )

    recommendation_cards = workload_service.get_recommendation_cards(
        capacity_summary={
            'cpu': {
                'headroom': 100,
            },
            'memory': {
                'headroom': 100,
            },
            'pods': {
                'headroom': 100,
            },
        },
        tenant_quota_rows=tenant_quota_all_rows,
        workload_mapping_rows=workload_mapping_all_rows,
    )

    context.update(
        {
            'namespace_options': namespace_options,
            'tenant_quota_summary': tenant_quota_summary,
            'tenant_quota_rows': tenant_quota_all_rows,
            'quota_status_options': quota_status_options,
            'tenant_risk_options': tenant_risk_options,
            'workload_mapping_payload': workload_mapping_payload,
            'workload_mapping_rows': workload_mapping_all_rows,
            'governance_findings': governance_findings,
            'recommendation_cards': recommendation_cards,
        }
    )

    return context
