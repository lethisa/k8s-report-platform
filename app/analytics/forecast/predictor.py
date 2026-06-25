class ForecastPredictor:
    def calculate_growth_rate(
        self,
        values: list[float],
    ) -> float:
        if (
            len(
                values,
            )
            < 2
        ):
            return 0

        first = values[0]
        last = values[-1]

        if first == 0:
            return 0

        return ((last - first) / first) * 100

    def simple_projection(
        self,
        current: float,
        growth_rate: float,
        days: int,
    ) -> float:
        daily_growth = growth_rate / 30

        return current * (1 + (daily_growth / 100) * days)
