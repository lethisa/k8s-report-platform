from flask import render_template

from app.analytics import analytics_bp


@analytics_bp.route('/')
def overview():
    return render_template('analytics/overview.html')


@analytics_bp.route('/utilization')
def utilization():
    return render_template('analytics/utilization.html')


@analytics_bp.route('/capacity')
def capacity():
    return render_template('analytics/capacity.html')


@analytics_bp.route('/forecasting')
def forecasting():
    return render_template('analytics/forecasting.html')


@analytics_bp.route('/consumers')
def consumers():
    return render_template('analytics/consumers.html')


@analytics_bp.route('/anomalies')
def anomalies():
    return render_template('analytics/anomalies.html')
