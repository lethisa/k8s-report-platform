from flask import Blueprint, render_template
from flask_login import login_required

from app.dashboard.service import get_cluster_health, get_dashboard_summary, get_recent_activities

dashboard_bp = Blueprint(
    'dashboard',
    __name__,
)


@dashboard_bp.route('/')
@login_required
def index():

    summary = get_dashboard_summary()

    health = get_cluster_health()

    activities = get_recent_activities()

    return render_template(
        'dashboard/index.html',
        cluster_count=summary['cluster_count'],
        node_count=summary['node_count'],
        namespace_count=summary['namespace_count'],
        health=health,
        activities=activities,
    )
