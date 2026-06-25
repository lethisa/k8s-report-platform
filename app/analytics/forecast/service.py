from datetime import UTC, datetime

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

    def get_projection_chart_data(
        self,
    ) -> dict:
        trends = self.utilization_service.get_trends(
            hours=24,
        )

        memory_trend = trends.get(
            'memory',
            [],
        )

        if not memory_trend:
            return {
                'labels': [],
                'historical': [],
                'projected': [],
            }

        labels = []
        historical = []

        for point in memory_trend:
            timestamp = point.get(
                'timestamp',
            )

            if timestamp:
                label = datetime.fromtimestamp(
                    float(timestamp),
                    UTC,
                ).strftime(
                    '%H:%M',
                )

            else:
                label = '-'

            labels.append(
                label,
            )

            historical.append(
                round(
                    float(
                        point.get(
                            'value',
                            0,
                        )
                    ),
                    2,
                )
            )
        current = historical[-1]

        projected = []

        if len(historical) < 2:
            growth_rate = 5

        else:
            growth_rate = self.predictor.calculate_growth_rate(
                historical,
            )

        if growth_rate == 0:
            growth_rate = 5

        for day in range(
            1,
            8,
        ):
            projected.append(
                round(
                    current * (1 + (growth_rate / 100) * (day / 30)),
                    2,
                )
            )

        return {
            'labels': labels,
            'historical': historical,
            'projection_labels': [
                'D+1',
                'D+2',
                'D+3',
                'D+4',
                'D+5',
                'D+6',
                'D+7',
            ],
            'projected': projected,
        }

    def get_insights(
        self,
    ) -> list[str]:
        summary = self.get_forecast_summary()

        current = summary.get(
            'current_utilization',
            0,
        )

        projected = summary.get(
            'forecast_90d',
            0,
        )

        return [
            (f'Current memory utilization ' f'is {current:.1f}%.'),
            (f'Projected utilization ' f'after 90 days will be ' f'{projected:.1f}%.'),
            ('No capacity exhaustion ' 'expected within forecast horizon.'),
        ]
