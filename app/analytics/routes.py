from flask import Blueprint, current_app, render_template, request
from flask_login import login_required

from app.analytics.capacity.routes import capacity
from app.analytics.forecast import ForecastService
from app.analytics.overview.service import get_analytics_overview
from app.analytics.storage.routes import storage
from app.analytics.utilization.routes import (
    utilization,
    utilization_node_detail,
    utilization_trend,
)
from app.analytics.utilization.service import (
    UtilizationService,
    get_selected_cluster,
    get_utilization_clusters,
)
from app.analytics.workload.routes import workload
from app.prometheus.service import PrometheusService

analytics_bp = Blueprint(
    'analytics',
    __name__,
    url_prefix='/analytics',
)


@analytics_bp.route('/')
@login_required
def overview() -> str:
    analytics = get_analytics_overview()

    return render_template(
        'analytics/overview.html',
        analytics=analytics,
    )


analytics_bp.add_url_rule(
    '/utilization',
    endpoint='utilization',
    view_func=utilization,
)

analytics_bp.add_url_rule(
    '/utilization/node-detail',
    endpoint='utilization_node_detail',
    view_func=utilization_node_detail,
)

analytics_bp.add_url_rule(
    '/utilization/trend',
    endpoint='utilization_trend',
    view_func=utilization_trend,
)

analytics_bp.add_url_rule(
    '/capacity',
    view_func=capacity,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/storage',
    view_func=storage,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/workload',
    view_func=workload,
    methods=[
        'GET',
    ],
)


@analytics_bp.route(
    '/forecast',
)
@login_required
def forecast():
    clusters = get_utilization_clusters()

    cluster_id = request.args.get(
        'cluster_id',
    )

    cluster = get_selected_cluster(
        cluster_id,
    )

    if not cluster:
        return render_template(
            'analytics/forecast.html',
            clusters=[],
            forecast_summary={},
            error='No cluster configured',
        )

    try:
        prometheus = PrometheusService(
            cluster,
        )

        utilization_service = UtilizationService(
            prometheus,
        )

        forecast_service = ForecastService(
            utilization_service,
        )

        forecast_summary = forecast_service.get_forecast_summary()
        forecast_insights = forecast_service.get_insights()
        projection_data = forecast_service.get_projection_chart_data()

        error = None

    except Exception as exc:
        current_app.logger.exception(
            exc,
        )

        forecast_summary = {}

        projection_data = {
            'labels': [],
            'historical': [],
            'projection_labels': [],
            'projected': [],
        }

        forecast_insights = []

        error = (
            'Unable to connect to Prometheus. '
            'Please verify endpoint, credentials, '
            'SSL configuration, and network connectivity.'
        )

    return render_template(
        'analytics/forecast.html',
        clusters=clusters,
        cluster=cluster,
        forecast_summary=forecast_summary,
        projection_data=projection_data,
        forecast_insights=forecast_insights,
        error=error,
    )


@analytics_bp.route('/consumers')
@login_required
def consumers() -> str:
    return render_template(
        'analytics/consumers.html',
    )


@analytics_bp.route('/anomalies')
@login_required
def anomalies() -> str:
    return render_template(
        'analytics/anomalies.html',
    )
