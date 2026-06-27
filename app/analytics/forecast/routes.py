# app/analytics/forecast/routes.py

from __future__ import annotations

from flask import render_template, request
from flask_login import login_required

from app.analytics.forecast.service import get_forecast_analysis_context


@login_required
def forecast() -> str:
    context = get_forecast_analysis_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/forecast/index.html',
        **context,
    )


@login_required
def forecast_section() -> str:
    context = get_forecast_analysis_context(
        query_args=request.args,
    )

    return render_template(
        'analytics/forecast/partials/_forecast_section.html',
        **context,
    )
