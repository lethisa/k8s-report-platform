from flask import Blueprint, render_template, request
from flask_login import login_required

from app.cluster.service import get_cluster_summary
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

inventory_bp = Blueprint(
    'inventory',
    __name__,
    url_prefix='/inventory',
)


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
    ).strip()

    page = request.args.get(
        'page',
        1,
        type=int,
    )

    per_page = request.args.get(
        'per_page',
        25,
        type=int,
    )

    allowed_per_page = [
        10,
        25,
        50,
        100,
    ]

    if per_page not in allowed_per_page:
        per_page = 25

    if page < 1:
        page = 1

    data = get_node_inventory(
        cluster_id=cluster_id,
        role=role,
        search=search,
    )

    all_nodes = data.get(
        'nodes',
        [],
    )

    total_items = len(
        all_nodes,
    )

    total_pages = max(
        (total_items + per_page - 1) // per_page,
        1,
    )

    if page > total_pages:
        page = total_pages

    start_index = (page - 1) * per_page

    end_index = start_index + per_page

    data['nodes'] = all_nodes[start_index:end_index]

    pagination = {
        'page': page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'start_item': start_index + 1 if total_items > 0 else 0,
        'end_item': min(
            end_index,
            total_items,
        ),
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1,
        'next_page': page + 1,
        'allowed_per_page': allowed_per_page,
    }

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
        pagination=pagination,
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
