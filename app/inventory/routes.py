from flask import render_template, request
from flask_login import login_required

from app.cluster import get_cluster_summary
from app.inventory import inventory_bp
from app.inventory.service import (
    get_ingress_inventory,
    get_inventory_overview,
    get_namespace_inventory,
    get_node_inventory,
    get_pod_inventory,
    get_service_inventory,
    get_storage_inventory_view,
    get_workload_inventory,
    sync_inventory,
)
from app.models.cluster import Cluster


@inventory_bp.post('/<string:cluster_id>/sync')
def sync(cluster_id: str):

    cluster = Cluster.query.get_or_404(cluster_id)

    sync_inventory(cluster)

    clusters, inventory_summary = get_cluster_summary()

    return render_template(
        'cluster/partials/table.html',
        clusters=clusters,
        inventory_summary=inventory_summary,
    )


@inventory_bp.route('/')
@login_required
def overview():

    overview = get_inventory_overview()

    return render_template(
        'inventory/overview.html',
        overview=overview,
    )


@inventory_bp.route('/nodes')
@login_required
def nodes():

    cluster_id = request.args.get(
        'cluster_id',
        '',
        type=str,
    )

    role = request.args.get(
        'role',
        '',
        type=str,
    )

    search = request.args.get(
        'search',
        '',
        type=str,
    )

    data = get_node_inventory(
        cluster_id=cluster_id,
        role=role,
        search=search,
    )

    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    return render_template(
        'inventory/nodes.html',
        inventory=data,
        clusters=clusters,
        cluster_id=cluster_id,
        role=role,
        selected_cluster_id=cluster_id,
        selected_role=role,
        search=search,
    )


@inventory_bp.route('/namespaces')
@login_required
def namespaces():

    cluster_id = request.args.get(
        'cluster_id',
        '',
        type=str,
    )

    status = request.args.get(
        'status',
        '',
        type=str,
    )

    search = request.args.get(
        'search',
        '',
        type=str,
    )

    data = get_namespace_inventory(
        cluster_id=cluster_id,
        status=status,
        search=search,
    )

    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    return render_template(
        'inventory/namespaces.html',
        inventory=data,
        clusters=clusters,
        selected_cluster_id=cluster_id,
        selected_status=status,
        search=search,
    )


@inventory_bp.route('/workloads')
@login_required
def workloads():

    cluster_id = request.args.get(
        'cluster_id',
        '',
        type=str,
    )

    workload_type = request.args.get(
        'type',
        '',
        type=str,
    )

    status = request.args.get(
        'status',
        '',
        type=str,
    )

    search = request.args.get(
        'search',
        '',
        type=str,
    )

    inventory = get_workload_inventory(
        cluster_id=cluster_id,
        workload_type=workload_type,
        status=status,
        search=search,
    )

    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    return render_template(
        'inventory/workloads.html',
        inventory=inventory,
        clusters=clusters,
        selected_cluster_id=cluster_id,
        selected_type=workload_type,
        selected_status=status,
        search=search,
    )


@inventory_bp.route('/pods')
@login_required
def pods():

    cluster_id = request.args.get(
        'cluster_id',
        '',
        type=str,
    )

    namespace = request.args.get(
        'namespace',
        '',
        type=str,
    )

    status = request.args.get(
        'status',
        '',
        type=str,
    )

    search = request.args.get(
        'search',
        '',
        type=str,
    )

    inventory = get_pod_inventory(
        cluster_id=cluster_id,
        namespace=namespace,
        status=status,
        search=search,
    )

    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    return render_template(
        'inventory/pods.html',
        inventory=inventory,
        clusters=clusters,
        selected_cluster_id=cluster_id,
        selected_namespace=namespace,
        selected_status=status,
        search=search,
    )


@inventory_bp.route('/services')
@login_required
def services():

    cluster_id = request.args.get(
        'cluster_id',
        '',
        type=str,
    )

    namespace = request.args.get(
        'namespace',
        '',
        type=str,
    )

    service_type = request.args.get(
        'type',
        '',
        type=str,
    )

    search = request.args.get(
        'search',
        '',
        type=str,
    )

    inventory = get_service_inventory(
        cluster_id=cluster_id,
        namespace=namespace,
        service_type=service_type,
        search=search,
    )

    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    return render_template(
        'inventory/services.html',
        inventory=inventory,
        clusters=clusters,
        selected_cluster_id=cluster_id,
        selected_namespace=namespace,
        selected_type=service_type,
        search=search,
    )


@inventory_bp.route('/ingresses')
@login_required
def ingresses():

    cluster_id = request.args.get(
        'cluster_id',
        '',
        type=str,
    )

    namespace = request.args.get(
        'namespace',
        '',
        type=str,
    )

    ingress_class = request.args.get(
        'class',
        '',
        type=str,
    )

    search = request.args.get(
        'search',
        '',
        type=str,
    )

    inventory = get_ingress_inventory(
        cluster_id=cluster_id,
        namespace=namespace,
        ingress_class=ingress_class,
        search=search,
    )

    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    return render_template(
        'inventory/ingresses.html',
        inventory=inventory,
        clusters=clusters,
        selected_cluster_id=cluster_id,
        selected_namespace=namespace,
        selected_class=ingress_class,
        search=search,
    )


@inventory_bp.route('/storage')
@login_required
def storage():

    cluster_id = request.args.get(
        'cluster_id',
        '',
        type=str,
    )

    namespace = request.args.get(
        'namespace',
        '',
        type=str,
    )

    storage_type = request.args.get(
        'type',
        '',
        type=str,
    )

    search = request.args.get(
        'search',
        '',
        type=str,
    )

    inventory = get_storage_inventory_view(
        cluster_id=cluster_id,
        namespace=namespace,
        storage_type=storage_type,
        search=search,
    )

    clusters = Cluster.query.order_by(
        Cluster.name,
    ).all()

    return render_template(
        'inventory/storage.html',
        inventory=inventory,
        clusters=clusters,
        selected_cluster_id=cluster_id,
        selected_namespace=namespace,
        selected_type=storage_type,
        search=search,
    )
