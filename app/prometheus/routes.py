from uuid import UUID

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

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
    '/cluster/<uuid:cluster_id>',
    methods=['GET', 'POST'],
)
def configuration(
    cluster_id: UUID,
):

    cluster = Cluster.query.get_or_404(cluster_id)

    form = PrometheusConfigForm()

    if form.validate_on_submit():
        PrometheusService.save_config(
            cluster,
            form,
        )

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
    '/cluster/<int:cluster_id>/test',
    methods=['POST'],
)
def test_connection(
    cluster_id: int,
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
