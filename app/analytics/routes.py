from flask import Blueprint, render_template
from flask_login import login_required

from app.analytics.capacity.routes import capacity
from app.analytics.forecast.routes import (
    forecast,
    forecast_section,
)
from app.analytics.overview.service import get_analytics_overview
from app.analytics.storage.routes import (
    storage,
    storage_filesystem_summary,
    storage_persistent_summary,
)
from app.analytics.top_consumers.routes import (
    top_consumers,
    top_consumers_section,
    top_consumers_table,
)
from app.analytics.utilization.routes import (
    utilization,
    utilization_node_detail,
    utilization_trend,
)
from app.analytics.workload.routes import (
    workload,
    workload_resource_mapping,
    workload_tenant_quota,
)

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
    endpoint='capacity',
    view_func=capacity,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/storage',
    endpoint='storage',
    view_func=storage,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/storage/filesystem-summary',
    endpoint='storage_filesystem_summary',
    view_func=storage_filesystem_summary,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/storage/persistent-summary',
    endpoint='storage_persistent_summary',
    view_func=storage_persistent_summary,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/workload',
    endpoint='workload',
    view_func=workload,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/workload/tenant-quota',
    endpoint='workload_tenant_quota',
    view_func=workload_tenant_quota,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/workload/resource-mapping',
    endpoint='workload_resource_mapping',
    view_func=workload_resource_mapping,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/forecast',
    endpoint='forecast',
    view_func=forecast,
    methods=[
        'GET',
    ],
)

analytics_bp.add_url_rule(
    '/forecast/section',
    endpoint='forecast_section',
    view_func=forecast_section,
    methods=[
        'GET',
    ],
)


analytics_bp.add_url_rule(
    '/top-consumers',
    endpoint='top_consumers',
    view_func=top_consumers,
    methods=['GET'],
)

analytics_bp.add_url_rule(
    '/top-consumers/section',
    endpoint='top_consumers_section',
    view_func=top_consumers_section,
    methods=['GET'],
)

analytics_bp.add_url_rule(
    '/top-consumers/table',
    endpoint='top_consumers_table',
    view_func=top_consumers_table,
    methods=['GET'],
)


@analytics_bp.route('/anomalies')
@login_required
def anomalies() -> str:
    return render_template(
        'analytics/anomalies.html',
    )
