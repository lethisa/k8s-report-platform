from flask import render_template

from app.reports import reports_bp


@reports_bp.route('/')
def index():
    return render_template('reports/index.html')


@reports_bp.route('/generate')
def generate():
    return render_template('reports/generate.html')


@reports_bp.route('/templates')
def templates():
    return render_template('reports/templates.html')


@reports_bp.route('/history')
def history():
    return render_template('reports/history.html')
