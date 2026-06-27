# app/analytics/storage/service.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.analytics.capacity.service import (
    ALLOWED_TIME_RANGE_VALUES,
    build_capacity_service_for_query,
    get_empty_capacity_payload,
    get_per_page_arg,
    get_positive_int_arg,
    get_query_value,
    get_selected_time_range,
)


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


def get_selected_storage_tab(
    query_args: Mapping[str, Any],
) -> str:
    selected_storage_tab = get_query_value(
        query_args=query_args,
        name='storage_tab',
        default='pvc',
    )

    if selected_storage_tab not in [
        'pvc',
        'pv',
    ]:
        return 'pvc'

    return selected_storage_tab


def get_storage_analysis_context(
    query_args: Mapping[str, Any],
) -> dict[str, Any]:
    _, _, capacity_service, context = build_capacity_service_for_query(
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

    selected_storage_node = get_query_value(
        query_args=query_args,
        name='storage_node',
        default='',
    )

    selected_storage_tab = get_selected_storage_tab(
        query_args=query_args,
    )

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

    context.update(
        {
            'selected_namespace': selected_namespace,
            'selected_time_range': selected_time_range,
            'selected_storage_node': selected_storage_node,
            'selected_storage_tab': selected_storage_tab,
            'selected_pvc_search': selected_pvc_search,
            'selected_pvc_status': selected_pvc_status,
            'selected_pvc_storage_class': selected_pvc_storage_class,
            'selected_pv_search': selected_pv_search,
            'selected_pv_status': selected_pv_status,
            'selected_pv_storage_class': selected_pv_storage_class,
            'allowed_time_ranges': get_allowed_time_ranges(),
            'allowed_time_range_values': ALLOWED_TIME_RANGE_VALUES,
            'namespace_options': [],
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

    storage_summary = capacity_service.get_storage_capacity_summary(
        selected_namespace=selected_namespace,
        selected_node=selected_storage_node,
        selected_pvc_search=selected_pvc_search,
        selected_pvc_status=selected_pvc_status,
        selected_pvc_storage_class=selected_pvc_storage_class,
        pvc_page=get_positive_int_arg(
            query_args=query_args,
            name='pvc_page',
            default=1,
        ),
        pvc_per_page=get_per_page_arg(
            query_args=query_args,
            name='pvc_per_page',
            default=10,
        ),
        selected_pv_search=selected_pv_search,
        selected_pv_status=selected_pv_status,
        selected_pv_storage_class=selected_pv_storage_class,
        pv_page=get_positive_int_arg(
            query_args=query_args,
            name='pv_page',
            default=1,
        ),
        pv_per_page=get_per_page_arg(
            query_args=query_args,
            name='pv_per_page',
            default=10,
        ),
    )

    namespace_options = capacity_service.get_all_namespace_options()

    context.update(
        {
            'storage_summary': storage_summary,
            'namespace_options': namespace_options,
        }
    )

    return context
