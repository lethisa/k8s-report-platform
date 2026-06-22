from flask import render_template
from flask_login import login_required

from app.analytics import analytics_bp
from app.analytics.overview.service import get_analytics_overview


@analytics_bp.route('/')
@login_required
def overview():

    analytics = get_analytics_overview()

    return render_template(
        'analytics/overview.html',
        analytics=analytics,
    )


@analytics_bp.route('/utilization')
@login_required
def utilization():
    return render_template('analytics/utilization.html')


@analytics_bp.route('/capacity')
@login_required
def capacity():
    return render_template('analytics/capacity.html')


@analytics_bp.route('/forecasting')
@login_required
def forecasting():
    return render_template('analytics/forecasting.html')


@analytics_bp.route('/consumers')
@login_required
def consumers():
    return render_template('analytics/consumers.html')


@analytics_bp.route('/anomalies')
@login_required
def anomalies():
    return render_template('analytics/anomalies.html')
