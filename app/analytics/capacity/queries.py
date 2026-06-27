# app/analytics/capacity/queries.py

NAMESPACE_ACTIVE_QUERY = 'kube_namespace_status_phase{phase="Active"}'

CPU_REQUESTS_TOTAL_QUERY = (
    'sum(kube_pod_container_resource_requests{resource="cpu",unit="core"})'
)

CPU_LIMITS_TOTAL_QUERY = (
    'sum(kube_pod_container_resource_limits{resource="cpu",unit="core"})'
)

MEMORY_REQUESTS_TOTAL_QUERY = (
    'sum(kube_pod_container_resource_requests{resource="memory",unit="byte"})'
)

MEMORY_LIMITS_TOTAL_QUERY = (
    'sum(kube_pod_container_resource_limits{resource="memory",unit="byte"})'
)

CURRENT_PODS_QUERY = 'sum(kube_pod_status_phase{phase=~"Running|Pending"})'

CPU_PEAK_QUERY_TEMPLATE = (
    'max_over_time(('
    'sum(rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m]))'
    ')[__TIME_RANGE__:5m])'
)

MEMORY_PEAK_QUERY_TEMPLATE = (
    'max_over_time(('
    'sum(container_memory_working_set_bytes{container!="",image!=""})'
    ')[__TIME_RANGE__:5m])'
)

NODE_VAR_FILESYSTEM_SIZE_QUERY = (
    'node_filesystem_size_bytes{'
    'mountpoint="/var",'
    'fstype!~"tmpfs|overlay|squashfs|nsfs|proc|sysfs|devtmpfs"'
    '}'
)

NODE_VAR_FILESYSTEM_AVAILABLE_QUERY = (
    'node_filesystem_avail_bytes{'
    'mountpoint="/var",'
    'fstype!~"tmpfs|overlay|squashfs|nsfs|proc|sysfs|devtmpfs"'
    '}'
)

PV_CAPACITY_QUERY = 'sum(kube_persistentvolume_capacity_bytes)'

PV_COUNT_QUERY = 'count(kube_persistentvolume_capacity_bytes)'

PV_STATUS_QUERY = (
    'sum by(phase)('
    'kube_persistentvolume_status_phase == 1'
    ')'
)

PV_DETAIL_CAPACITY_QUERY = 'kube_persistentvolume_capacity_bytes'

PV_DETAIL_STATUS_QUERY = 'kube_persistentvolume_status_phase == 1'

PV_INFO_QUERY = 'kube_persistentvolume_info'

PV_CAPACITY_BY_VOLUME_QUERY = 'kube_persistentvolume_capacity_bytes'

PV_STATUS_BY_VOLUME_QUERY = 'kube_persistentvolume_status_phase == 1'

PV_RECLAIM_POLICY_QUERY = 'kube_persistentvolume_reclaim_policy'

PVC_INFO_QUERY = 'kube_persistentvolumeclaim_info'

PVC_REQUESTED_TOTAL_QUERY = (
    'sum(kube_persistentvolumeclaim_resource_requests_storage_bytes)'
)

PVC_COUNT_QUERY = 'count(kube_persistentvolumeclaim_info)'

PVC_STATUS_QUERY = (
    'sum by(phase)('
    'kube_persistentvolumeclaim_status_phase == 1'
    ')'
)

PVC_USED_TOTAL_QUERY = 'sum(kubelet_volume_stats_used_bytes)'

PVC_AVAILABLE_TOTAL_QUERY = 'sum(kubelet_volume_stats_available_bytes)'

PVC_CAPACITY_TOTAL_QUERY = 'sum(kubelet_volume_stats_capacity_bytes)'

PVC_REQUESTED_BY_CLAIM_QUERY = (
    'sum by(namespace,persistentvolumeclaim)('
    'kube_persistentvolumeclaim_resource_requests_storage_bytes'
    ')'
)

PVC_USED_BY_CLAIM_QUERY = (
    'sum by(namespace,persistentvolumeclaim)('
    'kubelet_volume_stats_used_bytes'
    ')'
)

PVC_AVAILABLE_BY_CLAIM_QUERY = (
    'sum by(namespace,persistentvolumeclaim)('
    'kubelet_volume_stats_available_bytes'
    ')'
)

PVC_CAPACITY_BY_CLAIM_QUERY = (
    'sum by(namespace,persistentvolumeclaim)('
    'kubelet_volume_stats_capacity_bytes'
    ')'
)

PVC_STATUS_BY_CLAIM_QUERY = 'kube_persistentvolumeclaim_status_phase == 1'

TENANT_QUOTA_HARD_QUERY = (
    'sum by(namespace,resource)('
    'kube_resourcequota{type="hard",'
    'resource=~"requests.cpu|limits.cpu|requests.memory|limits.memory|pods"}'
    ')'
)

TENANT_QUOTA_USED_QUERY = (
    'sum by(namespace,resource)('
    'kube_resourcequota{type="used",'
    'resource=~"requests.cpu|limits.cpu|requests.memory|limits.memory|pods"}'
    ')'
)

TENANT_CPU_ACTUAL_QUERY = (
    'sum by(namespace)('
    'rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m])'
    ')'
)

TENANT_MEMORY_ACTUAL_QUERY = (
    'sum by(namespace)('
    'container_memory_working_set_bytes{container!="",image!=""}'
    ')'
)

TENANT_POD_ACTUAL_QUERY = (
    'sum by(namespace)('
    'kube_pod_status_phase{phase=~"Running|Pending"}'
    ')'
)

WORKLOAD_CPU_REQUESTS_QUERY = (
    'sum by(namespace,pod)('
    'kube_pod_container_resource_requests{resource="cpu",unit="core"}'
    ')'
)

WORKLOAD_CPU_LIMITS_QUERY = (
    'sum by(namespace,pod)('
    'kube_pod_container_resource_limits{resource="cpu",unit="core"}'
    ')'
)

WORKLOAD_CPU_AVG_QUERY = (
    'sum by(namespace,pod)('
    'rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m])'
    ')'
)

WORKLOAD_CPU_PEAK_QUERY_TEMPLATE = (
    'max by(namespace,pod)('
    'max_over_time(('
    'sum by(namespace,pod)('
    'rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m])'
    ')'
    ')[__TIME_RANGE__:5m])'
    ')'
)

WORKLOAD_MEMORY_REQUESTS_QUERY = (
    'sum by(namespace,pod)('
    'kube_pod_container_resource_requests{resource="memory",unit="byte"}'
    ')'
)

WORKLOAD_MEMORY_LIMITS_QUERY = (
    'sum by(namespace,pod)('
    'kube_pod_container_resource_limits{resource="memory",unit="byte"}'
    ')'
)

WORKLOAD_MEMORY_AVG_QUERY = (
    'sum by(namespace,pod)('
    'container_memory_working_set_bytes{container!="",image!=""}'
    ')'
)

WORKLOAD_MEMORY_PEAK_QUERY_TEMPLATE = (
    'max by(namespace,pod)('
    'max_over_time(('
    'sum by(namespace,pod)('
    'container_memory_working_set_bytes{container!="",image!=""}'
    ')'
    ')[__TIME_RANGE__:5m])'
    ')'
)

WORKLOAD_POD_OWNER_QUERY = 'kube_pod_owner'

WORKLOAD_QOS_QUERY = 'kube_pod_status_qos_class == 1'
