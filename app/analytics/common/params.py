# app/analytics/common/params.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
