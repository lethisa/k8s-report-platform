from app.analytics.utilization.service import (
    UtilizationService,
)


def bytes_to_gib(
    value: float,
) -> float:
    return round(
        value / 1024**3,
        2,
    )


class CapacityService:
    def __init__(
        self,
        utilization_service: UtilizationService,
    ) -> None:
        self.utilization_service = utilization_service

    def get_capacity_summary(
        self,
    ) -> dict:
        summary = self.utilization_service.get_summary()

        cpu_capacity = summary.get(
            'cpu_capacity',
            0,
        )

        cpu_usage = summary.get(
            'cpu_usage',
            0,
        )

        memory_capacity = summary.get(
            'memory_capacity',
            0,
        )

        memory_usage = summary.get(
            'memory_usage',
            0,
        )

        storage_capacity = summary.get(
            'storage_capacity',
            0,
        )

        storage_usage = summary.get(
            'storage_usage',
            0,
        )

        pod_capacity = summary.get(
            'pod_capacity',
            0,
        )

        pod_usage = summary.get(
            'pod_count',
            0,
        )

        cpu_available = cpu_capacity - cpu_usage

        memory_available = memory_capacity - memory_usage

        storage_available = storage_capacity - storage_usage

        pod_available = pod_capacity - pod_usage

        return {
            'cpu': {
                'capacity': round(
                    cpu_capacity,
                    2,
                ),
                'used': round(
                    cpu_usage,
                    2,
                ),
                'available': round(
                    cpu_available,
                    2,
                ),
                'headroom': (cpu_available / cpu_capacity * 100) if cpu_capacity else 0,
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
                'headroom': (memory_available / memory_capacity * 100) if memory_capacity else 0,
            },
            'storage': {
                'capacity': bytes_to_gib(
                    storage_capacity,
                ),
                'used': bytes_to_gib(
                    storage_usage,
                ),
                'available': bytes_to_gib(
                    storage_available,
                ),
                'headroom': (storage_available / storage_capacity * 100) if storage_capacity else 0,
            },
            'pods': {
                'capacity': pod_capacity,
                'used': pod_usage,
                'available': pod_available,
                'headroom': (pod_available / pod_capacity * 100) if pod_capacity else 0,
            },
        }
