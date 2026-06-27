# app/analytics/forecast/service.py

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import sqrt
from statistics import mean
from typing import Any

from app.analytics.common.base_service import AnalyticsBaseService
from app.analytics.common.context import build_analysis_utilization_context
from app.analytics.common.params import get_query_value
from app.analytics.forecast import queries
from app.analytics.utilization.service import UtilizationService
from app.models import Cluster
from app.prometheus.exceptions import PrometheusError
from app.prometheus.service import PrometheusService

WARNING_THRESHOLD = 75.0
CRITICAL_THRESHOLD = 90.0


HISTORY_WINDOW_OPTIONS: list[dict[str, str]] = [
    {
        'value': '7d',
        'label': 'Last 7 Days',
    },
    {
        'value': '30d',
        'label': 'Last 30 Days',
    },
    {
        'value': '90d',
        'label': 'Last 90 Days',
    },
]


FORECAST_HORIZON_OPTIONS: list[dict[str, str]] = [
    {
        'value': '7d',
        'label': 'Next 7 Days',
    },
    {
        'value': '30d',
        'label': 'Next 30 Days',
    },
    {
        'value': '90d',
        'label': 'Next 90 Days',
    },
    {
        'value': '180d',
        'label': 'Next 180 Days',
    },
    {
        'value': '365d',
        'label': 'Next 365 Days',
    },
]


RESOURCE_OPTIONS: list[dict[str, str]] = [
    {
        'value': 'all',
        'label': 'All Resources',
    },
    {
        'value': 'cpu',
        'label': 'CPU',
    },
    {
        'value': 'memory',
        'label': 'Memory',
    },
    {
        'value': 'storage',
        'label': 'Storage',
    },
    {
        'value': 'pods',
        'label': 'Pods',
    },
]


@dataclass(frozen=True)
class ForecastResourceDefinition:
    key: str
    label: str
    unit: str
    icon: str
    description: str
    usage_query: str
    capacity_query: str


@dataclass(frozen=True)
class ForecastPoint:
    timestamp: datetime
    value: float


class ForecastAnalysisService(AnalyticsBaseService):
    def __init__(
        self,
        utilization_service: UtilizationService,
        cluster: Cluster,
    ) -> None:
        self.utilization_service = utilization_service
        self.cluster = cluster
        self.prometheus = PrometheusService(cluster)

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

    def get_forecast_analysis(
        self,
        *,
        namespace: str,
        history_window: str,
        forecast_horizon: str,
        resource: str,
    ) -> dict[str, Any]:
        history_days = _parse_days(
            history_window,
            default=30,
        )
        horizon_days = _parse_days(
            forecast_horizon,
            default=90,
        )

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=history_days)
        step = _select_range_step(history_days)

        definitions = _get_resource_definitions(namespace)

        if resource != 'all':
            definitions = [definition for definition in definitions if definition.key == resource]

        items: list[dict[str, Any]] = []

        for definition in definitions:
            items.append(
                self._build_resource_forecast(
                    definition=definition,
                    start_time=start_time,
                    end_time=end_time,
                    step=step,
                    horizon_days=horizon_days,
                ),
            )

        summary = _build_summary(items)

        return {
            'has_data': any(item['has_data'] for item in items),
            'message': None,
            'namespace': namespace,
            'history_window': history_window,
            'forecast_horizon': forecast_horizon,
            'history_days': history_days,
            'horizon_days': horizon_days,
            'generated_at': end_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'items': items,
            'summary': summary,
            'chart': _build_chart_payload(items),
            'recommendations': _build_recommendations(items),
        }

    def _build_resource_forecast(
        self,
        *,
        definition: ForecastResourceDefinition,
        start_time: datetime,
        end_time: datetime,
        step: str,
        horizon_days: int,
    ) -> dict[str, Any]:
        raw_points = self._query_range(
            query=definition.usage_query,
            start_time=start_time,
            end_time=end_time,
            step=step,
        )
        daily_points = _daily_average(raw_points)

        capacity = self._query_instant(
            query=definition.capacity_query,
        )

        forecast_result = _calculate_forecast(
            values=daily_points,
            horizon_days=horizon_days,
        )

        current_value = forecast_result['current_value']
        projected_value = forecast_result['projected_value']
        slope_per_day = forecast_result['slope_per_day']

        current_percent = _percentage(
            current_value,
            capacity,
        )
        projected_percent = _percentage(
            projected_value,
            capacity,
        )

        warning_eta = _calculate_eta(
            current_value=current_value,
            slope_per_day=slope_per_day,
            capacity=capacity,
            threshold=WARNING_THRESHOLD,
        )
        critical_eta = _calculate_eta(
            current_value=current_value,
            slope_per_day=slope_per_day,
            capacity=capacity,
            threshold=CRITICAL_THRESHOLD,
        )

        status = _resolve_status(projected_percent)

        return {
            'key': definition.key,
            'label': definition.label,
            'unit': definition.unit,
            'icon': definition.icon,
            'description': definition.description,
            'has_data': len(daily_points) >= 2 and capacity > 0,
            'status': status,
            'status_label': status.title(),
            'capacity': capacity,
            'capacity_display': _format_value(
                capacity,
                definition.unit,
            ),
            'current_value': current_value,
            'current_display': _format_value(
                current_value,
                definition.unit,
            ),
            'projected_value': projected_value,
            'projected_display': _format_value(
                projected_value,
                definition.unit,
            ),
            'growth_per_day': slope_per_day,
            'growth_per_week': slope_per_day * 7,
            'growth_display': _format_growth(
                slope_per_day,
                definition.unit,
            ),
            'current_percent': round(
                current_percent,
                2,
            ),
            'projected_percent': round(
                projected_percent,
                2,
            ),
            'warning_eta': warning_eta,
            'critical_eta': critical_eta,
            'confidence': forecast_result['confidence'],
            'confidence_reason': forecast_result['confidence_reason'],
            'historical_points': [
                {
                    'date': point.timestamp.strftime('%Y-%m-%d'),
                    'value': point.value,
                    'percent': round(
                        _percentage(
                            point.value,
                            capacity,
                        ),
                        2,
                    ),
                }
                for point in daily_points
            ],
            'forecast_points': [
                {
                    'date': point.timestamp.strftime('%Y-%m-%d'),
                    'value': point.value,
                    'percent': round(
                        _percentage(
                            point.value,
                            capacity,
                        ),
                        2,
                    ),
                }
                for point in forecast_result['forecast_points']
            ],
        }

    def _query_range(
        self,
        *,
        query: str,
        start_time: datetime,
        end_time: datetime,
        step: str,
    ) -> list[ForecastPoint]:
        try:
            result = self.prometheus.range_query(
                query=query,
                start=_to_prometheus_time(start_time),
                end=_to_prometheus_time(end_time),
                step=step,
            )
        except Exception:
            return []

        return _extract_range_points(result)

    def _query_instant(
        self,
        *,
        query: str,
    ) -> float:
        try:
            result = self.prometheus.instant_query(
                query=query,
            )
        except Exception:
            return 0.0

        return _extract_instant_value(result)


def get_forecast_analysis_context(
    query_args: Mapping[str, Any],
) -> dict[str, Any]:
    _, selected_cluster, utilization_service, context = build_analysis_utilization_context(
        query_args=query_args,
    )

    cluster = selected_cluster or context.get(
        'cluster',
    )

    selected_namespace = get_query_value(
        query_args=query_args,
        name='namespace',
        default='',
    )
    selected_history_window = _normalize_option(
        get_query_value(
            query_args=query_args,
            name='history_window',
            default='30d',
        ),
        '30d',
        {item['value'] for item in HISTORY_WINDOW_OPTIONS},
    )
    selected_forecast_horizon = _normalize_option(
        get_query_value(
            query_args=query_args,
            name='forecast_horizon',
            default='90d',
        ),
        '90d',
        {item['value'] for item in FORECAST_HORIZON_OPTIONS},
    )
    selected_resource = _normalize_option(
        get_query_value(
            query_args=query_args,
            name='resource',
            default='all',
        ),
        'all',
        {item['value'] for item in RESOURCE_OPTIONS},
    )

    context.update(
        {
            'selected_namespace': selected_namespace,
            'selected_history_window': selected_history_window,
            'selected_forecast_horizon': selected_forecast_horizon,
            'selected_resource': selected_resource,
            'history_window_options': HISTORY_WINDOW_OPTIONS,
            'forecast_horizon_options': FORECAST_HORIZON_OPTIONS,
            'resource_options': RESOURCE_OPTIONS,
            'namespace_options': [],
            'prometheus_status': {
                'connected': False,
                'label': 'No Cluster',
                'response_time_ms': None,
                'error': None,
            },
            'prometheus_connected': False,
            'forecast_payload': _empty_payload(
                message='No cluster available. Add a Kubernetes cluster first.',
            ),
        }
    )

    if utilization_service is None or cluster is None:
        return context

    try:
        prometheus_status = utilization_service.get_prometheus_status()
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
        context['forecast_payload'] = _empty_payload(
            message=_safe_message(
                value=prometheus_status.get(
                    'error',
                ),
                default='Prometheus is not connected for the selected cluster.',
            ),
        )

        return context

    try:
        forecast_service = ForecastAnalysisService(
            utilization_service=utilization_service,
            cluster=cluster,
        )
    except PrometheusError as exc:
        context['forecast_payload'] = _empty_payload(
            message=str(exc),
        )

        return context
    except Exception as exc:
        context['forecast_payload'] = _empty_payload(
            message=f'Forecast service initialization failed: {exc}',
        )

        return context

    try:
        namespace_options = forecast_service.get_namespace_options()
    except PrometheusError:
        namespace_options = []
    except Exception:
        namespace_options = []

    context['namespace_options'] = namespace_options

    try:
        forecast_payload = forecast_service.get_forecast_analysis(
            namespace=selected_namespace,
            history_window=selected_history_window,
            forecast_horizon=selected_forecast_horizon,
            resource=selected_resource,
        )
    except PrometheusError as exc:
        forecast_payload = _empty_payload(
            message=str(exc),
        )
    except Exception as exc:
        forecast_payload = _empty_payload(
            message=f'Forecast query failed: {exc}',
        )

    context['forecast_payload'] = forecast_payload

    return context


def _get_resource_definitions(
    namespace: str,
) -> list[ForecastResourceDefinition]:
    return [
        ForecastResourceDefinition(
            key='cpu',
            label='CPU',
            unit='cores',
            icon='cpu',
            description='Projected CPU usage growth compared with worker-node allocatable CPU.',
            usage_query=_render_namespace_query(
                namespace=namespace,
                all_query=queries.CPU_USAGE_QUERY,
                namespace_query=queries.CPU_USAGE_BY_NAMESPACE_QUERY,
            ),
            capacity_query=queries.CPU_WORKER_CAPACITY_QUERY,
        ),
        ForecastResourceDefinition(
            key='memory',
            label='Memory',
            unit='bytes',
            icon='memory-stick',
            description='Projected memory working set growth compared with worker-node allocatable memory.',
            usage_query=_render_namespace_query(
                namespace=namespace,
                all_query=queries.MEMORY_USAGE_QUERY,
                namespace_query=queries.MEMORY_USAGE_BY_NAMESPACE_QUERY,
            ),
            capacity_query=queries.MEMORY_WORKER_CAPACITY_QUERY,
        ),
        ForecastResourceDefinition(
            key='storage',
            label='Storage',
            unit='bytes',
            icon='database',
            description='Projected PVC storage growth compared with PVC capacity.',
            usage_query=_render_namespace_query(
                namespace=namespace,
                all_query=queries.STORAGE_USAGE_QUERY,
                namespace_query=queries.STORAGE_USAGE_BY_NAMESPACE_QUERY,
            ),
            capacity_query=_render_namespace_query(
                namespace=namespace,
                all_query=queries.STORAGE_CAPACITY_QUERY,
                namespace_query=queries.STORAGE_CAPACITY_BY_NAMESPACE_QUERY,
            ),
        ),
        ForecastResourceDefinition(
            key='pods',
            label='Pods',
            unit='count',
            icon='boxes',
            description='Projected running pod growth compared with worker-node pod capacity.',
            usage_query=_render_namespace_query(
                namespace=namespace,
                all_query=queries.POD_USAGE_QUERY,
                namespace_query=queries.POD_USAGE_BY_NAMESPACE_QUERY,
            ),
            capacity_query=queries.POD_WORKER_CAPACITY_QUERY,
        ),
    ]


def _render_namespace_query(
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


def _calculate_forecast(
    *,
    values: list[ForecastPoint],
    horizon_days: int,
) -> dict[str, Any]:
    if len(values) < 2:
        current_value = values[-1].value if values else 0.0

        return {
            'current_value': current_value,
            'projected_value': current_value,
            'slope_per_day': 0.0,
            'forecast_points': [],
            'confidence': 'Low',
            'confidence_reason': 'Not enough historical data points.',
        }

    start = values[0].timestamp

    x_values = [
        max(
            (point.timestamp - start).total_seconds() / 86400,
            0.0,
        )
        for point in values
    ]
    y_values = [point.value for point in values]

    slope, intercept = _linear_regression(
        x_values=x_values,
        y_values=y_values,
    )

    current_value = max(
        y_values[-1],
        0.0,
    )
    last_x = x_values[-1]

    forecast_points: list[ForecastPoint] = []

    for day in range(1, horizon_days + 1):
        forecast_timestamp = values[-1].timestamp + timedelta(days=day)
        forecast_x = last_x + day
        forecast_value = max(
            (slope * forecast_x) + intercept,
            0.0,
        )

        forecast_points.append(
            ForecastPoint(
                timestamp=forecast_timestamp,
                value=forecast_value,
            ),
        )

    projected_value = forecast_points[-1].value if forecast_points else current_value

    confidence, confidence_reason = _calculate_confidence(
        values=y_values,
        points_count=len(values),
    )

    return {
        'current_value': current_value,
        'projected_value': projected_value,
        'slope_per_day': slope,
        'forecast_points': forecast_points,
        'confidence': confidence,
        'confidence_reason': confidence_reason,
    }


def _linear_regression(
    *,
    x_values: list[float],
    y_values: list[float],
) -> tuple[float, float]:
    x_avg = mean(x_values)
    y_avg = mean(y_values)

    numerator = sum(
        (x_value - x_avg) * (y_value - y_avg)
        for x_value, y_value in zip(
            x_values,
            y_values,
            strict=True,
        )
    )
    denominator = sum((x_value - x_avg) ** 2 for x_value in x_values)

    if denominator == 0:
        return 0.0, y_avg

    slope = numerator / denominator
    intercept = y_avg - (slope * x_avg)

    return slope, intercept


def _calculate_confidence(
    *,
    values: list[float],
    points_count: int,
) -> tuple[str, str]:
    if points_count < 7:
        return 'Low', 'Less than 7 daily data points available.'

    avg_value = mean(values)

    if avg_value <= 0:
        return 'Low', 'Average historical value is zero or unavailable.'

    variance = mean(
        [(value - avg_value) ** 2 for value in values],
    )
    std_dev = sqrt(variance)
    coefficient_of_variation = std_dev / avg_value

    if points_count >= 30 and coefficient_of_variation <= 0.25:
        return 'High', 'Historical data is sufficient and relatively stable.'

    if points_count >= 14 and coefficient_of_variation <= 0.60:
        return 'Medium', 'Historical data is usable with moderate variance.'

    return 'Low', 'Historical data is noisy or too limited.'


def _calculate_eta(
    *,
    current_value: float,
    slope_per_day: float,
    capacity: float,
    threshold: float,
) -> dict[str, Any]:
    if capacity <= 0:
        return {
            'label': 'N/A',
            'days': None,
            'date': None,
        }

    threshold_value = capacity * (threshold / 100)

    if current_value >= threshold_value:
        return {
            'label': 'Reached',
            'days': 0,
            'date': datetime.now(UTC).strftime('%Y-%m-%d'),
        }

    if slope_per_day <= 0:
        return {
            'label': 'Not projected',
            'days': None,
            'date': None,
        }

    days = int((threshold_value - current_value) / slope_per_day)

    if days < 0:
        days = 0

    target_date = datetime.now(UTC) + timedelta(days=days)

    return {
        'label': f'{days} days',
        'days': days,
        'date': target_date.strftime('%Y-%m-%d'),
    }


def _build_summary(
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    warning_items = [item for item in items if item['status'] == 'warning']
    critical_items = [item for item in items if item['status'] == 'critical']

    highest_projected = None

    if items:
        highest_projected = max(
            items,
            key=lambda item: item['projected_percent'],
        )

    return {
        'total_resources': len(items),
        'warning_count': len(warning_items),
        'critical_count': len(critical_items),
        'highest_projected_label': (highest_projected['label'] if highest_projected is not None else 'N/A'),
        'highest_projected_percent': (highest_projected['projected_percent'] if highest_projected is not None else 0),
        'nearest_warning': _find_nearest_eta(
            items=items,
            eta_key='warning_eta',
        ),
        'nearest_critical': _find_nearest_eta(
            items=items,
            eta_key='critical_eta',
        ),
    }


def _find_nearest_eta(
    *,
    items: list[dict[str, Any]],
    eta_key: str,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []

    for item in items:
        eta = item[eta_key]

        if eta['days'] is None:
            continue

        candidates.append(
            {
                'resource': item['label'],
                'label': eta['label'],
                'days': eta['days'],
                'date': eta['date'],
            },
        )

    if not candidates:
        return {
            'resource': None,
            'label': 'Not projected',
            'days': None,
            'date': None,
        }

    return min(
        candidates,
        key=lambda candidate: candidate['days'],
    )


def _build_chart_payload(
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    datasets = []

    for item in items:
        historical = item['historical_points']
        forecast = item['forecast_points']

        labels = [point['date'] for point in historical] + [point['date'] for point in forecast]

        historical_values = [point['percent'] for point in historical] + [None for _ in forecast]

        forecast_values = [None for _ in historical] + [point['percent'] for point in forecast]

        datasets.append(
            {
                'key': item['key'],
                'label': item['label'],
                'labels': labels,
                'historical': historical_values,
                'forecast': forecast_values,
            },
        )

    return {
        'datasets': datasets,
        'warning_threshold': WARNING_THRESHOLD,
        'critical_threshold': CRITICAL_THRESHOLD,
    }


def _build_recommendations(
    items: list[dict[str, Any]],
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []

    for item in items:
        if item['projected_percent'] >= CRITICAL_THRESHOLD:
            recommendations.append(
                {
                    'level': 'critical',
                    'title': f'{item["label"]} capacity risk is critical',
                    'description': (
                        f'{item["label"]} is projected to reach '
                        f'{item["projected_percent"]}% usage. '
                        'Plan capacity expansion or reduce resource usage.'
                    ),
                },
            )
        elif item['projected_percent'] >= WARNING_THRESHOLD:
            recommendations.append(
                {
                    'level': 'warning',
                    'title': f'{item["label"]} usage is approaching warning level',
                    'description': (
                        f'{item["label"]} is projected to reach '
                        f'{item["projected_percent"]}% usage. '
                        'Review workload growth, requests, limits, and capacity headroom.'
                    ),
                },
            )

    if not recommendations:
        recommendations.append(
            {
                'level': 'normal',
                'title': 'No immediate capacity risk detected',
                'description': (
                    'Projected resource growth is still within the normal capacity range. '
                    'Keep monitoring trend stability and workload changes.'
                ),
            },
        )

    return recommendations


def _extract_range_points(
    result: Any,
) -> list[ForecastPoint]:
    prometheus_result = _get_prometheus_result_list(result)
    aggregated: dict[int, float] = {}

    for series in prometheus_result:
        values = series.get('values', [])

        for item in values:
            if len(item) < 2:
                continue

            try:
                timestamp = int(float(item[0]))
                value = float(item[1])
            except (TypeError, ValueError):
                continue

            aggregated[timestamp] = (
                aggregated.get(
                    timestamp,
                    0.0,
                )
                + value
            )

    return [
        ForecastPoint(
            timestamp=datetime.fromtimestamp(
                timestamp,
                UTC,
            ),
            value=value,
        )
        for timestamp, value in sorted(aggregated.items())
    ]


def _extract_instant_value(
    result: Any,
) -> float:
    prometheus_result = _get_prometheus_result_list(result)
    total = 0.0

    for series in prometheus_result:
        value = series.get('value')

        if not value or len(value) < 2:
            continue

        try:
            total += float(value[1])
        except (TypeError, ValueError):
            continue

    return total


def _get_prometheus_result_list(
    result: Any,
) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return result

    if not isinstance(result, dict):
        return []

    data = result.get('data')

    if isinstance(data, dict):
        prometheus_result = data.get('result', [])

        if isinstance(prometheus_result, list):
            return prometheus_result

    prometheus_result = result.get('result', [])

    if isinstance(prometheus_result, list):
        return prometheus_result

    return []


def _daily_average(
    points: list[ForecastPoint],
) -> list[ForecastPoint]:
    grouped: dict[str, list[float]] = {}

    for point in points:
        date_key = point.timestamp.strftime('%Y-%m-%d')
        grouped.setdefault(
            date_key,
            [],
        ).append(point.value)

    daily_points: list[ForecastPoint] = []

    for date_key, values in sorted(grouped.items()):
        timestamp = datetime.strptime(
            date_key,
            '%Y-%m-%d',
        ).replace(tzinfo=UTC)

        daily_points.append(
            ForecastPoint(
                timestamp=timestamp,
                value=mean(values),
            ),
        )

    return daily_points


def _select_range_step(
    history_days: int,
) -> str:
    if history_days <= 7:
        return '1h'

    if history_days <= 30:
        return '6h'

    return '12h'


def _parse_days(
    value: str | None,
    *,
    default: int,
) -> int:
    if value is None:
        return default

    try:
        return int(value.replace('d', ''))
    except ValueError:
        return default


def _normalize_option(
    value: str | None,
    default: str,
    allowed_values: set[str],
) -> str:
    if value in allowed_values:
        return value

    return default


def _percentage(
    value: float,
    capacity: float,
) -> float:
    if capacity <= 0:
        return 0.0

    return max(
        (value / capacity) * 100,
        0.0,
    )


def _resolve_status(
    projected_percent: float,
) -> str:
    if projected_percent >= CRITICAL_THRESHOLD:
        return 'critical'

    if projected_percent >= WARNING_THRESHOLD:
        return 'warning'

    return 'normal'


def _format_value(
    value: float,
    unit: str,
) -> str:
    if unit == 'bytes':
        return _format_bytes(value)

    if unit == 'cores':
        return f'{value:.2f} cores'

    if unit == 'count':
        return f'{value:.0f}'

    return f'{value:.2f}'


def _format_growth(
    slope_per_day: float,
    unit: str,
) -> str:
    weekly_growth = slope_per_day * 7

    if unit == 'bytes':
        return f'{_format_bytes(weekly_growth)} / week'

    if unit == 'cores':
        return f'{weekly_growth:.2f} cores / week'

    if unit == 'count':
        return f'{weekly_growth:.0f} pods / week'

    return f'{weekly_growth:.2f} / week'


def _format_bytes(
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


def _to_prometheus_time(
    value: datetime,
) -> str:
    return str(value.timestamp())


def _safe_message(
    *,
    value: Any,
    default: str,
) -> str:
    if isinstance(
        value,
        str,
    ) and value:
        return value

    if value is None:
        return default

    return str(
        value,
    )


def _empty_payload(
    *,
    message: str,
) -> dict[str, Any]:
    return {
        'has_data': False,
        'message': message,
        'namespace': '',
        'history_window': '30d',
        'forecast_horizon': '90d',
        'history_days': 30,
        'horizon_days': 90,
        'generated_at': None,
        'items': [],
        'summary': {
            'total_resources': 0,
            'warning_count': 0,
            'critical_count': 0,
            'highest_projected_label': 'N/A',
            'highest_projected_percent': 0,
            'nearest_warning': {
                'resource': None,
                'label': 'Not projected',
                'days': None,
                'date': None,
            },
            'nearest_critical': {
                'resource': None,
                'label': 'Not projected',
                'days': None,
                'date': None,
            },
        },
        'chart': {
            'datasets': [],
            'warning_threshold': WARNING_THRESHOLD,
            'critical_threshold': CRITICAL_THRESHOLD,
        },
        'recommendations': [],
    }
