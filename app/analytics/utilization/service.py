from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.analytics.utilization import queries
from app.prometheus.service import (
    PrometheusService,
)


class UtilizationService:
    def __init__(
        self,
        prometheus: PrometheusService,
    ) -> None:
        self.prometheus = prometheus

    @staticmethod
    def _extract_scalar(
        response: dict[str, Any],
    ) -> float:
        try:
            result = response['data']['result']

            if not result:
                return 0.0

            return float(result[0]['value'][1])

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ):
            return 0.0

    @staticmethod
    def _extract_consumers(
        response: dict[str, Any],
    ) -> list[dict[str, str | float]]:
        results = response.get(
            'data',
            {},
        ).get(
            'result',
            [],
        )

        consumers: list[dict[str, str | float]] = []

        for item in results:
            metric = item.get(
                'metric',
                {},
            )

            try:
                value = float(item['value'][1])
            except (
                KeyError,
                IndexError,
                TypeError,
                ValueError,
            ):
                value = 0.0

            consumers.append(
                {
                    'namespace': metric.get(
                        'namespace',
                        '-',
                    ),
                    'pod': metric.get(
                        'pod',
                        '-',
                    ),
                    'value': value,
                }
            )

        return consumers

    @staticmethod
    def _extract_series(
        response: dict[str, Any],
    ) -> list[dict[str, float]]:
        try:
            results = response['data']['result']

            if not results:
                return []

            values = results[0]['values']

            return [
                {
                    'timestamp': float(item[0]),
                    'value': float(item[1]),
                }
                for item in values
            ]

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ):
            return []

    def _query_series(
        self,
        query: str,
        hours: int = 24,
        step: str = '1h',
    ) -> list[dict[str, float]]:
        end = datetime.now(
            UTC,
        )

        start = end - timedelta(
            hours=hours,
        )

        response = self.prometheus.range_query(
            query=query,
            start=start.isoformat(),
            end=end.isoformat(),
            step=step,
        )

        return self._extract_series(
            response,
        )

    def _query_scalar(
        self,
        query: str,
    ) -> float:
        response = self.prometheus.instant_query(
            query,
        )

        return round(
            self._extract_scalar(response),
            2,
        )

    def get_cpu_capacity(
        self,
    ) -> float:
        return self._query_scalar(
            queries.CPU_CAPACITY,
        )

    def get_cpu_usage(
        self,
    ) -> float:
        return self._query_scalar(
            queries.CPU_USAGE,
        )

    def get_cpu_utilization(
        self,
    ) -> float:
        return self._query_scalar(
            queries.CPU_UTILIZATION,
        )

    def get_memory_capacity(
        self,
    ) -> float:
        return self._query_scalar(
            queries.MEMORY_CAPACITY,
        )

    def get_memory_usage(
        self,
    ) -> float:
        return self._query_scalar(
            queries.MEMORY_USAGE,
        )

    def get_memory_utilization(
        self,
    ) -> float:
        return self._query_scalar(
            queries.MEMORY_UTILIZATION,
        )

    def get_storage_capacity(
        self,
    ) -> float:
        return self._query_scalar(
            queries.STORAGE_CAPACITY,
        )

    def get_storage_usage(
        self,
    ) -> float:
        return self._query_scalar(
            queries.STORAGE_USAGE,
        )

    def get_storage_utilization(
        self,
    ) -> float:
        return self._query_scalar(
            queries.STORAGE_UTILIZATION,
        )

    def get_pod_count(
        self,
    ) -> int:
        return int(
            self._query_scalar(
                queries.POD_COUNT,
            )
        )

    def get_pod_capacity(
        self,
    ) -> int:
        return int(
            self._query_scalar(
                queries.POD_CAPACITY,
            )
        )

    def get_pod_utilization(
        self,
    ) -> float:
        return self._query_scalar(
            queries.POD_UTILIZATION,
        )

    def get_total_nodes(
        self,
    ) -> int:
        return int(
            self._query_scalar(
                queries.TOTAL_NODES,
            )
        )

    def get_master_nodes(
        self,
    ) -> int:
        return int(
            self._query_scalar(
                queries.MASTER_NODES,
            )
        )

    def get_worker_nodes(
        self,
    ) -> int:
        return int(
            self._query_scalar(
                queries.WORKER_NODES,
            )
        )

    def get_kubernetes_version(
        self,
    ) -> str:
        response = self.prometheus.instant_query(
            queries.KUBERNETES_VERSION,
        )

        try:
            result = response['data']['result']

            if not result:
                return '-'

            return result[0]['metric'].get(
                'git_version',
                '-',
            )

        except (
            KeyError,
            IndexError,
            TypeError,
        ):
            return '-'

    def get_cpu_trend(
        self,
        hours: int = 24,
    ) -> list[dict[str, float]]:
        return self._query_series(
            queries.CPU_UTILIZATION_HISTORY,
            hours,
        )

    def get_memory_trend(
        self,
        hours: int = 24,
    ) -> list[dict[str, float]]:
        return self._query_series(
            queries.MEMORY_UTILIZATION_HISTORY,
            hours,
        )

    def get_storage_trend(
        self,
        hours: int = 24,
    ) -> list[dict[str, float]]:
        return self._query_series(
            queries.STORAGE_UTILIZATION_HISTORY,
            hours,
        )

    def get_trends(
        self,
        hours: int = 24,
    ) -> dict[
        str,
        list[dict[str, float]],
    ]:
        return {
            'cpu': self.get_cpu_trend(
                hours,
            ),
            'memory': self.get_memory_trend(
                hours,
            ),
            'storage': self.get_storage_trend(
                hours,
            ),
        }

    def get_summary(
        self,
    ) -> dict[str, int | float]:
        return {
            'cpu_capacity': self.get_cpu_capacity(),
            'cpu_usage': self.get_cpu_usage(),
            'cpu_utilization': self.get_cpu_utilization(),
            'memory_capacity': self.get_memory_capacity(),
            'memory_usage': self.get_memory_usage(),
            'memory_utilization': self.get_memory_utilization(),
            'storage_capacity': self.get_storage_capacity(),
            'storage_usage': self.get_storage_usage(),
            'storage_utilization': self.get_storage_utilization(),
            'pod_count': self.get_pod_count(),
            'pod_capacity': self.get_pod_capacity(),
            'pod_utilization': self.get_pod_utilization(),
        }

    def get_summary_table(
        self,
    ) -> list[dict[str, str | float]]:
        return [
            {
                'resource': 'CPU',
                'capacity': self.get_cpu_capacity(),
                'usage': self.get_cpu_usage(),
                'utilization': self.get_cpu_utilization(),
            },
            {
                'resource': 'Memory',
                'capacity': self.get_memory_capacity(),
                'usage': self.get_memory_usage(),
                'utilization': self.get_memory_utilization(),
            },
            {
                'resource': 'Storage',
                'capacity': self.get_storage_capacity(),
                'usage': self.get_storage_usage(),
                'utilization': self.get_storage_utilization(),
            },
            {
                'resource': 'Pods',
                'capacity': self.get_pod_capacity(),
                'usage': self.get_pod_count(),
                'utilization': self.get_pod_utilization(),
            },
        ]

    def get_top_cpu_consumers(
        self,
    ) -> list[dict[str, str | float]]:
        response = self.prometheus.instant_query(
            queries.TOP_CPU_CONSUMERS,
        )

        return self._extract_consumers(
            response,
        )

    def get_top_memory_consumers(
        self,
    ) -> list[dict[str, str | float]]:
        response = self.prometheus.instant_query(
            queries.TOP_MEMORY_CONSUMERS,
        )

        return self._extract_consumers(
            response,
        )

    def get_cluster_info(
        self,
        summary: dict[str, int | float],
    ) -> dict[str, int | float | str]:
        return {
            'kubernetes_version': self.get_kubernetes_version(),
            'total_nodes': self.get_total_nodes(),
            'worker_nodes': self.get_worker_nodes(),
            'master_nodes': self.get_master_nodes(),
            'cpu_capacity': summary['cpu_capacity'],
            'memory_capacity': summary['memory_capacity'],
            'pod_capacity': summary['pod_capacity'],
        }
