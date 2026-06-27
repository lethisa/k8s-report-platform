# app/analytics/workload/service.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.analytics.capacity.service import (
    get_empty_capacity_payload,
    get_per_page_arg,
    get_positive_int_arg,
    get_query_value,
    get_selected_time_range,
)
from app.analytics.common.context import build_analysis_capacity_service_context


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


def get_workload_analysis_context(
    query_args: Mapping[str, Any],
) -> dict[str, Any]:
    _, _, capacity_service, context = build_analysis_capacity_service_context(
        query_args=query_args,
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

    if capacity_service is None:
        context.update(
            get_empty_capacity_payload(
                selected_namespace=selected_namespace,
                selected_time_range=selected_time_range,
            )
        )

        return context

    tenant_quota_summary = capacity_service.get_tenant_quota_summary(
        selected_namespace=selected_namespace,
    )

    tenant_quota_all_rows = tenant_quota_summary['rows']

    tenant_quota_filtered_rows = filter_tenant_quota_rows(
        rows=tenant_quota_all_rows,
        selected_search=selected_tenant_search,
        selected_quota_status=selected_tenant_quota_status,
        selected_risk=selected_tenant_risk,
    )

    tenant_quota_page = capacity_service.paginate_rows(
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

    workload_mapping_payload = capacity_service.get_workload_mapping_payload(
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

    workload_mapping_page = capacity_service.paginate_rows(
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

    namespace_options = capacity_service.get_all_namespace_options()

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

    governance_findings = capacity_service.get_governance_findings(
        tenant_quota_rows=tenant_quota_all_rows,
        workload_mapping_rows=workload_mapping_all_rows,
    )

    recommendation_cards = capacity_service.get_recommendation_cards(
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
