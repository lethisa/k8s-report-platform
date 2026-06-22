from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from app.models.cluster import Cluster
from app.prometheus.exceptions import (
    PrometheusError,
)
from app.prometheus.forms import (
    PrometheusConfigForm,
)
from app.prometheus.service import (
    PrometheusService,
)

bp = Blueprint(
    'prometheus',
    __name__,
    url_prefix='/prometheus',
)


@bp.route(
    '/cluster/<string:cluster_id>',
    methods=['GET', 'POST'],
)
def configuration(cluster_id: str):

    cluster = Cluster.query.get_or_404(cluster_id)

    form = PrometheusConfigForm()

    if request.method == 'POST':
        print('===== POST RECEIVED =====')
        print(request.form)

    current_app.logger.warning('PROMETHEUS CONFIG POST')

    if request.method == 'POST':
        print('========== POST ==========')
        print(request.form)

        print(
            'FORM VALID:',
            form.validate(),
        )

        print(
            'FORM ERRORS:',
            form.errors,
        )

    if form.validate_on_submit():
        print('SAVE CONFIG CALLED')

        config = PrometheusService.save_config(
            cluster,
            form,
        )

        print(f'SAVED CONFIG={config.id}')

        flash(
            'Prometheus configuration saved',
            'success',
        )

        return redirect(
            url_for(
                'prometheus.configuration',
                cluster_id=cluster.id,
            )
        )

    if request.method == 'POST':
        print('===== FORM INVALID =====')
        print(form.errors)

    config = cluster.prometheus_config

    if request.method == 'GET' and config:
        form.endpoint.data = config.endpoint
        form.auth_type.data = config.auth_type
        form.username.data = config.username
        form.password.data = config.password
        form.bearer_token.data = config.bearer_token
        form.timeout.data = config.timeout
        form.verify_ssl.data = config.verify_ssl

    return render_template(
        'prometheus/configuration.html',
        cluster=cluster,
        form=form,
    )


@bp.route(
    '/cluster/<string:cluster_id>/test',
    methods=['POST'],
)
def test_connection(
    cluster_id: str,
):

    cluster = Cluster.query.get_or_404(cluster_id)

    try:
        service = PrometheusService(cluster)

        result = service.test_connection()

        return jsonify(result)

    except PrometheusError as exc:
        return jsonify(
            {
                'success': False,
                'error': str(exc),
            }
        ), 400
