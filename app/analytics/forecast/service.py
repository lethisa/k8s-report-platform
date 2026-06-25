from app.analytics.forecast.predictor import (
    ForecastPredictor,
)
from app.analytics.utilization.service import (
    UtilizationService,
)


class ForecastService:
    def __init__(
        self,
        utilization_service: UtilizationService,
    ) -> None:
        self.utilization_service = utilization_service

        self.predictor = ForecastPredictor()

    def get_forecast_summary(
        self,
    ) -> dict:
        summary = self.utilization_service.get_summary()

        memory_usage = summary.get(
            'memory_usage',
            0,
        )

        memory_capacity = summary.get(
            'memory_capacity',
            0,
        )

        current_utilization = ((memory_usage / memory_capacity) * 100) if memory_capacity else 0

        return {
            'current_utilization': round(
                current_utilization,
                2,
            ),
            'forecast_30d': round(
                current_utilization * 1.05,
                2,
            ),
            'forecast_60d': round(
                current_utilization * 1.10,
                2,
            ),
            'forecast_90d': round(
                current_utilization * 1.15,
                2,
            ),
            'growth_rate': 5,
        }
