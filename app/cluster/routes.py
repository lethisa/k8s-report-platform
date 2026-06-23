from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from app.cluster.forms import ClusterCreateForm, ClusterEditForm
from app.cluster.service import create_cluster, delete_cluster, get_cluster_summary, run_test_cluster, update_cluster
from app.models import Cluster

cluster_bp = Blueprint('cluster', __name__, url_prefix='/clusters')


@cluster_bp.route('/')
@login_required
def list_clusters():

    clusters, inventory_summary = get_cluster_summary()

    return render_template(
        'cluster/list.html',
        clusters=clusters,
        inventory_summary=inventory_summary,
    )


@cluster_bp.route(
    '/add',
    methods=['GET', 'POST'],
)
@login_required
def add_cluster():

    form = ClusterCreateForm()

    if form.validate_on_submit():
        kube_file = form.kubeconfig.data

        if kube_file is None:
            flash(
                'Kubeconfig file is required',
                'danger',
            )

            return render_template(
                'cluster/add.html',
                form=form,
            )

        try:
            kube_content = kube_file.read().decode('utf-8')

            assert form.name.data is not None
            assert form.environment.data is not None
            assert form.kubeconfig.data is not None

            create_cluster(
                name=form.name.data,
                environment=form.environment.data,
                description=form.description.data,
                kubeconfig=kube_content,
            )

            flash(
                'Cluster added successfully',
                'success',
            )

            return redirect(url_for('cluster.list_clusters'))

        except ValueError as exc:
            flash(
                str(exc),
                'danger',
            )

    return render_template(
        'cluster/add.html',
        form=form,
    )


@cluster_bp.route(
    '/<string:cluster_id>/test',
    methods=['POST'],
)
@login_required
def test_cluster(cluster_id):

    cluster = Cluster.query.get_or_404(cluster_id)

    result = run_test_cluster(cluster)

    if result['success']:
        flash(
            'Cluster connected successfully',
            'success',
        )
    else:
        flash(
            result['error'],
            'danger',
        )

    clusters, inventory_summary = get_cluster_summary()

    return render_template(
        'cluster/partials/table.html',
        clusters=clusters,
        inventory_summary=inventory_summary,
    )


@cluster_bp.route(
    '/<string:cluster_id>/edit',
    methods=['GET', 'POST'],
)
@login_required
def edit_cluster(cluster_id):

    cluster = Cluster.query.get_or_404(cluster_id)

    form = ClusterEditForm(obj=cluster)

    if form.validate_on_submit():
        name = form.name.data
        environment = form.environment.data

        assert name is not None
        assert environment is not None

        try:
            update_cluster(
                cluster=cluster,
                name=name,
                environment=environment,
                description=form.description.data,
            )

            flash(
                'Cluster updated successfully',
                'success',
            )

            return redirect(url_for('cluster.list_clusters'))

        except ValueError as exc:
            flash(
                str(exc),
                'danger',
            )

    return render_template(
        'cluster/edit.html',
        form=form,
        cluster=cluster,
    )


@cluster_bp.route(
    '/<string:cluster_id>/delete',
    methods=['POST'],
)
@login_required
def delete_cluster_route(cluster_id):

    cluster = Cluster.query.get_or_404(cluster_id)

    delete_cluster(cluster)

    flash(
        'Cluster deleted successfully',
        'success',
    )

    return redirect(url_for('cluster.list_clusters'))
