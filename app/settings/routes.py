from flask import Blueprint, render_template

bp = Blueprint(
    'settings',
    __name__,
    url_prefix='/settings',
)


@bp.route('/')
@bp.route('/general')
def general():
    return render_template('settings/general.html')


@bp.route('/reports')
def reports():
    return render_template('settings/reports.html')


@bp.route('/system-info')
def system_info():
    return render_template('settings/system_info.html')


@bp.route('/prometheus')
def prometheus():
    return render_template('settings/prometheus.html')
