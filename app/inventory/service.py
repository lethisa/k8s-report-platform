from datetime import UTC, datetime
from typing import cast

from kubernetes.client import AppsV1Api, CoreV1Api, NetworkingV1Api, StorageV1Api, V1NamespaceList, V1Node
from sqlalchemy import func

from app.cluster.service import get_cluster_summary
from app.extensions import db
from app.inventory.collector import (
    get_cluster_version,
    get_ingresses,
    get_nodes,
    get_pods,
    get_services,
    get_storage_inventory,
    get_workloads,
)
from app.kubernetes.client import KubernetesClient
from app.models import (
    Cluster,
    ClusterInventory,
    IngressInventory,
    NamespaceInventory,
    NodeInventory,
    PodInventory,
    ServiceInventory,
    StorageInventory,
    WorkloadInventory,
)


def get_node_role(
    node: V1Node,
) -> str:
    metadata = node.metadata

    if metadata is None:
        return 'unknown'

    labels = metadata.labels or {}

    for key in labels:
        if key.startswith('node-role.kubernetes.io/'):
            return key.split('/')[-1]

    return 'worker'


def save_cluster_info(
    cluster: Cluster,
) -> None:
    ClusterInventory.query.filter_by(
        cluster_id=cluster.id,
    ).delete(
        synchronize_session=False,
    )

    db.session.add(
        ClusterInventory(
            cluster_id=cluster.id,
            kubernetes_version=get_cluster_version(),
        )
    )


def save_nodes(
    cluster: Cluster,
    api: CoreV1Api,
) -> None:
    NodeInventory.query.filter_by(
        cluster_id=cluster.id,
    ).delete(
        synchronize_session=False,
    )

    nodes = get_nodes(api)

    for node in nodes:
        metadata = node.metadata
        status = node.status

        if metadata is None:
            continue

        if status is None:
            continue

        if status.node_info is None:
            continue

        capacity = status.capacity or {}

        cpu_value = capacity.get('cpu')

        try:
            cpu = int(cpu_value) if cpu_value is not None else None
        except (
            ValueError,
            TypeError,
        ):
            cpu = None

        db.session.add(
            NodeInventory(
                cluster_id=cluster.id,
                node_name=metadata.name,
                role=get_node_role(node),
                os_image=status.node_info.os_image,
                kernel_version=status.node_info.kernel_version,
                container_runtime=(status.node_info.container_runtime_version),
                cpu=cpu,
                memory=capacity.get('memory'),
            )
        )


def save_namespaces(
    cluster: Cluster,
    api: CoreV1Api,
) -> None:

    NamespaceInventory.query.filter_by(
        cluster_id=cluster.id,
    ).delete(
        synchronize_session=False,
    )

    namespace_list = cast(
        V1NamespaceList,
        api.list_namespace(),
    )

    namespaces = namespace_list.items or []

    for namespace in namespaces:
        metadata = namespace.metadata

        if metadata is None:
            continue

        db.session.add(
            NamespaceInventory(
                cluster_id=cluster.id,
                namespace=metadata.name,
                status=(namespace.status.phase if namespace.status else None),
            )
        )


def save_workloads(
    cluster: Cluster,
    apps_api: AppsV1Api,
) -> None:

    WorkloadInventory.query.filter_by(
        cluster_id=cluster.id,
    ).delete(
        synchronize_session=False,
    )

    workloads = get_workloads(
        apps_api,
    )

    for workload in workloads:
        db.session.add(
            WorkloadInventory(
                cluster_id=cluster.id,
                namespace=workload['namespace'],
                name=workload['name'],
                workload_type=workload['workload_type'],
                ready=workload['ready'],
                status=workload['status'],
                created_at=workload['created_at'],
            )
        )


def save_pods(
    cluster: Cluster,
    api: CoreV1Api,
) -> None:

    PodInventory.query.filter_by(
        cluster_id=cluster.id,
    ).delete(
        synchronize_session=False,
    )

    pods = get_pods(
        api,
    )

    for pod in pods:
        db.session.add(
            PodInventory(
                cluster_id=cluster.id,
                namespace=pod['namespace'],
                pod_name=pod['pod_name'],
                node_name=pod['node_name'],
                phase=pod['phase'],
                pod_ip=pod['pod_ip'],
                ready=pod['ready'],
                restart_count=pod['restart_count'],
                created_at=pod['created_at'],
            )
        )


def save_services(
    cluster: Cluster,
    api: CoreV1Api,
) -> None:

    ServiceInventory.query.filter_by(
        cluster_id=cluster.id,
    ).delete(
        synchronize_session=False,
    )

    services = get_services(
        api,
    )

    for service in services:
        db.session.add(
            ServiceInventory(
                cluster_id=cluster.id,
                namespace=service['namespace'],
                service_name=service['service_name'],
                service_type=service['service_type'],
                cluster_ip=service['cluster_ip'],
                external_ip=service['external_ip'],
                ports=service['ports'],
                created_at=service['created_at'],
            )
        )


def save_ingresses(
    cluster: Cluster,
    api: NetworkingV1Api,
) -> None:

    IngressInventory.query.filter_by(
        cluster_id=cluster.id,
    ).delete(
        synchronize_session=False,
    )

    ingresses = get_ingresses(
        api,
    )

    for ingress in ingresses:
        db.session.add(
            IngressInventory(
                cluster_id=cluster.id,
                namespace=ingress['namespace'],
                ingress_name=ingress['ingress_name'],
                ingress_class=ingress['ingress_class'],
                host=ingress['host'],
                address=ingress['address'],
                tls_enabled=ingress['tls_enabled'],
                created_at=ingress['created_at'],
            )
        )


def save_storage_inventory(
    cluster: Cluster,
    core_api: CoreV1Api,
    storage_api: StorageV1Api,
) -> None:

    StorageInventory.query.filter_by(
        cluster_id=cluster.id,
    ).delete(
        synchronize_session=False,
    )

    items = get_storage_inventory(
        core_api,
        storage_api,
    )

    for item in items:
        db.session.add(
            StorageInventory(
                cluster_id=cluster.id,
                namespace=item['namespace'],
                name=item['name'],
                storage_type=item['storage_type'],
                storage_class=item['storage_class'],
                capacity=item['capacity'],
                status=item['status'],
                created_at=item['created_at'],
            )
        )


def sync_inventory(
    cluster: Cluster,
) -> None:
    try:
        client = KubernetesClient(
            cluster.kubeconfig,
        )

        core_api = client.core_api()

        apps_api = client.apps_api()

        networking_api = client.networking_api()

        storage_api = client.storage_api()

        save_cluster_info(
            cluster,
        )

        save_nodes(
            cluster,
            core_api,
        )

        save_namespaces(
            cluster,
            core_api,
        )

        save_workloads(
            cluster,
            apps_api,
        )

        save_pods(
            cluster,
            core_api,
        )

        save_services(
            cluster,
            core_api,
        )

        save_ingresses(
            cluster,
            networking_api,
        )

        save_storage_inventory(
            cluster,
            core_api,
            storage_api,
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise


def convert_ki_to_gib(
    value: str | None,
) -> float:

    if not value:
        return 0

    if not value.endswith('Ki'):
        return 0

    try:
        kib = int(
            value.replace(
                'Ki',
                '',
            )
        )

        return round(
            kib / 1024 / 1024,
            1,
        )

    except (
        ValueError,
        TypeError,
    ):
        return 0


def get_inventory_overview():

    clusters, inventory_summary = get_cluster_summary()
    for cluster in clusters:
        cluster.workload_count = WorkloadInventory.query.filter_by(cluster_id=cluster.id).count()

        cluster.pod_count = PodInventory.query.filter_by(cluster_id=cluster.id).count()

        cluster.service_count = ServiceInventory.query.filter_by(cluster_id=cluster.id).count()

        cluster.ingress_count = IngressInventory.query.filter_by(cluster_id=cluster.id).count()

        cluster.storage_count = StorageInventory.query.filter_by(cluster_id=cluster.id).count()

    health = get_inventory_health()
    activities = get_recent_inventory_activity()
    last_sync_human = '-'

    last_sync_human = '-'

    last_sync = health.get('last_sync') if health else None

    if last_sync:
        last_sync_human = last_sync.strftime('%H:%M')

    return {
        'total_clusters': (db.session.query(func.count(ClusterInventory.id)).scalar() or 0),
        'total_nodes': (db.session.query(func.count(NodeInventory.id)).scalar() or 0),
        'total_namespaces': (db.session.query(func.count(NamespaceInventory.id)).scalar() or 0),
        'total_workloads': (db.session.query(func.count(WorkloadInventory.id)).scalar() or 0),
        'total_pods': (db.session.query(func.count(PodInventory.id)).scalar() or 0),
        'total_services': (db.session.query(func.count(ServiceInventory.id)).scalar() or 0),
        'total_ingresses': (db.session.query(func.count(IngressInventory.id)).scalar() or 0),
        'total_storage': (db.session.query(func.count(StorageInventory.id)).scalar() or 0),
        'clusters': clusters,
        'inventory_summary': (inventory_summary),
        'health': health,
        'activities': activities,
        'last_sync_human': last_sync_human,
    }


def get_inventory_health():

    clusters = Cluster.query.all()

    healthy_clusters = 0
    never_synced = 0
    last_sync = None
    connected_clusters = 0

    for cluster in clusters:
        if cluster.status == 'connected':
            connected_clusters += 1
            healthy_clusters += 1

        inventory = ClusterInventory.query.filter_by(cluster_id=cluster.id).first()

        if inventory is None:
            never_synced += 1
            continue

        if last_sync is None or inventory.collected_at > last_sync:
            last_sync = inventory.collected_at

    last_sync_display = '-'

    if last_sync:
        last_sync_display = last_sync.strftime('%d %b %Y %H:%M')

    return {
        'connected_clusters': connected_clusters,
        'healthy_clusters': healthy_clusters,
        'never_synced': never_synced,
        'last_sync': last_sync,
        'last_sync_display': last_sync_display,
    }


def get_recent_inventory_activity():

    inventories = ClusterInventory.query.order_by(ClusterInventory.collected_at.desc()).limit(5).all()

    activities = []

    for inventory in inventories:
        cluster = Cluster.query.get(inventory.cluster_id)

        activities.append(
            {
                'cluster': (cluster.name if cluster else 'Unknown'),
                'collected_at': (inventory.collected_at),
            }
        )

    return activities


def get_node_inventory(
    cluster_id=None,
    role=None,
    search=None,
):

    query = db.session.query(
        NodeInventory,
        Cluster.name.label(
            'cluster_name',
        ),
    ).join(
        Cluster,
        Cluster.id == NodeInventory.cluster_id,
    )

    if cluster_id:
        query = query.filter(NodeInventory.cluster_id == cluster_id)

    if role:
        query = query.filter(NodeInventory.role == role)

    if search:
        query = query.filter(NodeInventory.node_name.ilike(f'%{search}%'))

    nodes = query.order_by(
        Cluster.name,
        NodeInventory.node_name,
    ).all()

    nodes_data = []

    for node, cluster_name in nodes:
        runtime = node.container_runtime or ''

        runtime_display = runtime.split('://')[0] if '://' in runtime else runtime

        nodes_data.append(
            {
                'cluster_name': cluster_name,
                'node_name': node.node_name,
                'role': node.role,
                'cpu': node.cpu,
                'memory_display': (f'{convert_ki_to_gib(node.memory)} GiB'),
                'os_image': node.os_image,
                'runtime_display': runtime_display,
            }
        )

    total_cpu = sum(node.cpu or 0 for node, _ in nodes)

    total_memory = round(
        sum(convert_ki_to_gib(node.memory) for node, _ in nodes),
        1,
    )

    return {
        'total_nodes': len(nodes),
        'total_cpu': total_cpu,
        'total_memory': total_memory,
        'nodes': nodes_data,
    }


def get_namespace_inventory(
    cluster_id=None,
    status=None,
    search=None,
):

    query = db.session.query(
        NamespaceInventory,
        Cluster.name.label(
            'cluster_name',
        ),
    ).join(
        Cluster,
        Cluster.id == NamespaceInventory.cluster_id,
    )

    if cluster_id:
        query = query.filter(NamespaceInventory.cluster_id == cluster_id)

    if status:
        query = query.filter(NamespaceInventory.status == status)

    if search:
        query = query.filter(NamespaceInventory.namespace.ilike(f'%{search}%'))

    namespaces = query.order_by(
        Cluster.name,
        NamespaceInventory.namespace,
    ).all()

    cluster_count = len({cluster_name for _, cluster_name in namespaces})

    status_counts = {}

    for namespace, _ in namespaces:
        status = namespace.status or 'Unknown'

        status_counts[status] = (
            status_counts.get(
                status,
                0,
            )
            + 1
        )

    return {
        'total_namespaces': len(
            namespaces,
        ),
        'total_clusters': cluster_count,
        'active_namespaces': (
            status_counts.get(
                'Active',
                0,
            )
        ),
        'status_counts': status_counts,
        'namespaces': namespaces,
    }


def format_age(
    created_at,
) -> str:

    if not created_at:
        return '-'

    delta = datetime.now(UTC) - created_at

    days = delta.days

    if days > 0:
        return f'{days}d'

    hours = delta.seconds // 3600

    return f'{hours}h'


def get_workload_inventory(
    cluster_id=None,
    workload_type=None,
    status=None,
    search=None,
):

    query = db.session.query(
        WorkloadInventory,
        Cluster.name.label(
            'cluster_name',
        ),
    ).join(
        Cluster,
        Cluster.id == WorkloadInventory.cluster_id,
    )

    if cluster_id:
        query = query.filter(WorkloadInventory.cluster_id == cluster_id)

    if workload_type:
        query = query.filter(WorkloadInventory.workload_type == workload_type)

    if status:
        query = query.filter(WorkloadInventory.status == status)

    if search:
        query = query.filter(WorkloadInventory.name.ilike(f'%{search}%'))

    workloads = query.order_by(
        Cluster.name,
        WorkloadInventory.namespace,
        WorkloadInventory.name,
    ).all()

    type_counts = {}
    status_counts = {}

    deployments = 0
    statefulsets = 0
    daemonsets = 0

    workloads_data = []

    for workload, cluster_name in workloads:
        workload_type = workload.workload_type or 'Unknown'

        status_name = workload.status or 'Unknown'

        type_counts[workload_type] = (
            type_counts.get(
                workload_type,
                0,
            )
            + 1
        )

        status_counts[status_name] = (
            status_counts.get(
                status_name,
                0,
            )
            + 1
        )

        if workload_type == 'Deployment':
            deployments += 1

        elif workload_type == 'StatefulSet':
            statefulsets += 1

        elif workload_type == 'DaemonSet':
            daemonsets += 1

        workloads_data.append(
            {
                'cluster_name': cluster_name,
                'namespace': workload.namespace,
                'name': workload.name,
                'type': workload_type,
                'ready': workload.ready,
                'status': status_name,
                'age': format_age(
                    workload.created_at,
                ),
            }
        )

    return {
        'total_workloads': len(workloads),
        'deployments': deployments,
        'statefulsets': statefulsets,
        'daemonsets': daemonsets,
        'type_counts': type_counts,
        'status_counts': status_counts,
        'workloads': workloads_data,
    }


def get_pod_inventory(
    cluster_id=None,
    namespace=None,
    status=None,
    search=None,
):

    query = db.session.query(
        PodInventory,
        Cluster.name.label(
            'cluster_name',
        ),
    ).join(
        Cluster,
        Cluster.id == PodInventory.cluster_id,
    )

    if cluster_id:
        query = query.filter(PodInventory.cluster_id == cluster_id)

    if namespace:
        query = query.filter(PodInventory.namespace == namespace)

    if status:
        query = query.filter(PodInventory.phase == status)

    if search:
        query = query.filter(PodInventory.pod_name.ilike(f'%{search}%'))

    pods = query.order_by(
        Cluster.name,
        PodInventory.namespace,
        PodInventory.pod_name,
    ).all()

    namespace_query = db.session.query(
        PodInventory.namespace,
    ).distinct()

    if cluster_id:
        namespace_query = namespace_query.filter(PodInventory.cluster_id == cluster_id)

    namespaces = sorted([ns for (ns,) in namespace_query.all() if ns])

    status_counts = {}

    status_query = db.session.query(
        PodInventory.phase,
    ).distinct()

    if cluster_id:
        status_query = status_query.filter(PodInventory.cluster_id == cluster_id)

    for (phase,) in status_query.all():
        phase = phase or 'Unknown'

        status_counts[phase] = 0

    pod_data = []

    running = 0
    pending = 0
    failed = 0

    for pod, cluster_name in pods:
        phase = pod.phase or 'Unknown'

        if phase == 'Running':
            running += 1

        elif phase == 'Pending':
            pending += 1

        elif phase == 'Failed':
            failed += 1

        pod_data.append(
            {
                'cluster_name': cluster_name,
                'namespace': pod.namespace,
                'name': pod.pod_name,
                'node': pod.node_name,
                'ready': pod.ready,
                'restarts': pod.restart_count,
                'ip': pod.pod_ip,
                'status': phase,
                'age': format_age(
                    pod.created_at,
                ),
            }
        )

    return {
        'total_pods': len(pods),
        'running': running,
        'pending': pending,
        'failed': failed,
        'status_counts': status_counts,
        'namespaces': namespaces,
        'pods': pod_data,
    }


def get_service_inventory(
    cluster_id=None,
    namespace=None,
    service_type=None,
    search=None,
):

    query = db.session.query(
        ServiceInventory,
        Cluster.name.label(
            'cluster_name',
        ),
    ).join(
        Cluster,
        Cluster.id == ServiceInventory.cluster_id,
    )

    if cluster_id:
        query = query.filter(ServiceInventory.cluster_id == cluster_id)

    if namespace:
        query = query.filter(ServiceInventory.namespace == namespace)

    if service_type:
        query = query.filter(ServiceInventory.service_type == service_type)

    if search:
        query = query.filter(ServiceInventory.service_name.ilike(f'%{search}%'))

    services = query.order_by(
        Cluster.name,
        ServiceInventory.namespace,
        ServiceInventory.service_name,
    ).all()

    namespace_query = db.session.query(
        ServiceInventory.namespace,
    ).distinct()

    if cluster_id:
        namespace_query = namespace_query.filter(ServiceInventory.cluster_id == cluster_id)

    namespaces = sorted([ns for (ns,) in namespace_query.all() if ns])

    services_data = []

    cluster_ip_count = 0
    node_port_count = 0
    load_balancer_count = 0

    service_types = {
        'ClusterIP': 0,
        'NodePort': 0,
        'LoadBalancer': 0,
    }

    for service, cluster_name in services:
        service_type = service.service_type or 'Unknown'

        if service_type in service_types:
            service_types[service_type] += 1

        if service_type == 'ClusterIP':
            cluster_ip_count += 1

        elif service_type == 'NodePort':
            node_port_count += 1

        elif service_type == 'LoadBalancer':
            load_balancer_count += 1

        services_data.append(
            {
                'cluster_name': cluster_name,
                'namespace': service.namespace,
                'service_name': service.service_name,
                'service_type': service_type,
                'cluster_ip': (service.cluster_ip or '-'),
                'external_ip': (service.external_ip or '-'),
                'ports': (service.ports or '-'),
                'age': format_age(
                    service.created_at,
                ),
            }
        )

    return {
        'total_services': len(services),
        'cluster_ip': cluster_ip_count,
        'node_port': node_port_count,
        'load_balancer': load_balancer_count,
        'namespaces': namespaces,
        'service_types': service_types,
        'services': services_data,
    }


def get_ingress_inventory(
    cluster_id=None,
    namespace=None,
    ingress_class=None,
    search=None,
):

    query = db.session.query(
        IngressInventory,
        Cluster.name.label(
            'cluster_name',
        ),
    ).join(
        Cluster,
        Cluster.id == IngressInventory.cluster_id,
    )

    if cluster_id:
        query = query.filter(IngressInventory.cluster_id == cluster_id)

    if namespace:
        query = query.filter(IngressInventory.namespace == namespace)

    if ingress_class:
        query = query.filter(IngressInventory.ingress_class == ingress_class)

    if search:
        query = query.filter(IngressInventory.ingress_name.ilike(f'%{search}%'))

    ingresses = query.order_by(
        Cluster.name,
        IngressInventory.namespace,
        IngressInventory.ingress_name,
    ).all()

    namespace_query = db.session.query(
        IngressInventory.namespace,
    ).distinct()

    if cluster_id:
        namespace_query = namespace_query.filter(IngressInventory.cluster_id == cluster_id)

    namespaces = sorted([ns for (ns,) in namespace_query.all() if ns])

    ingress_data = []

    tls_enabled = 0
    hosts = set()
    classes = set()

    for ingress, cluster_name in ingresses:
        if ingress.tls_enabled:
            tls_enabled += 1

        if ingress.host:
            hosts.add(
                ingress.host,
            )

        if ingress.ingress_class:
            classes.add(
                ingress.ingress_class,
            )

        ingress_data.append(
            {
                'cluster_name': cluster_name,
                'namespace': ingress.namespace,
                'name': ingress.ingress_name,
                'class': ingress.ingress_class or '-',
                'host': ingress.host or '-',
                'address': ingress.address or '-',
                'tls': ingress.tls_enabled,
                'age': format_age(
                    ingress.created_at,
                ),
            }
        )

    return {
        'total_ingresses': len(ingresses),
        'tls_enabled': tls_enabled,
        'total_hosts': len(hosts),
        'ingress_classes': len(classes),
        'namespaces': namespaces,
        'ingresses': ingress_data,
        'total_namespaces': len(namespaces),
    }


def get_storage_inventory_view(
    cluster_id=None,
    namespace=None,
    storage_type=None,
    search=None,
):

    query = db.session.query(
        StorageInventory,
        Cluster.name.label(
            'cluster_name',
        ),
    ).join(
        Cluster,
        Cluster.id == StorageInventory.cluster_id,
    )

    if cluster_id:
        query = query.filter(StorageInventory.cluster_id == cluster_id)

    if namespace:
        query = query.filter(StorageInventory.namespace == namespace)

    if storage_type:
        query = query.filter(StorageInventory.storage_type == storage_type)

    if search:
        query = query.filter(StorageInventory.name.ilike(f'%{search}%'))

    items = query.order_by(
        Cluster.name,
        StorageInventory.storage_type,
        StorageInventory.name,
    ).all()

    namespace_query = db.session.query(
        StorageInventory.namespace,
    ).distinct()

    if cluster_id:
        namespace_query = namespace_query.filter(StorageInventory.cluster_id == cluster_id)

    namespaces = sorted([ns for (ns,) in namespace_query.all() if ns])

    data = []

    storage_classes = 0
    persistent_volumes = 0
    persistent_volume_claims = 0

    storage_types = {
        'StorageClass': 0,
        'PersistentVolume': 0,
        'PersistentVolumeClaim': 0,
    }

    for item, cluster_name in items:
        if item.storage_type == 'StorageClass':
            storage_classes += 1

        elif item.storage_type == 'PersistentVolume':
            persistent_volumes += 1

        elif item.storage_type == 'PersistentVolumeClaim':
            persistent_volume_claims += 1

        data.append(
            {
                'cluster_name': cluster_name,
                'namespace': item.namespace or '-',
                'name': item.name,
                'type': item.storage_type,
                'storage_class': (item.storage_class or '-'),
                'capacity': (item.capacity or '-'),
                'status': (item.status or '-'),
                'age': format_age(
                    item.created_at,
                ),
            }
        )

    return {
        'total_storage': len(items),
        'storage_classes': storage_classes,
        'persistent_volumes': persistent_volumes,
        'persistent_volume_claims': persistent_volume_claims,
        'namespaces': namespaces,
        'storage_types': storage_types,
        'storage_items': data,
    }
