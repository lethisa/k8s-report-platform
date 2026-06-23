CPU_CAPACITY = """
sum(
    kube_node_status_capacity{
        resource="cpu"
    }
)
"""

CPU_USAGE = """
sum(
    rate(
        container_cpu_usage_seconds_total{
            container!="",
            container!="POD"
        }[5m]
    )
)
"""

CPU_UTILIZATION = """
(
    sum(
        rate(
            container_cpu_usage_seconds_total{
                container!="",
                container!="POD"
            }[5m]
        )
    )
/
    sum(
        kube_node_status_capacity{
            resource="cpu"
        }
    )
) * 100
"""

MEMORY_CAPACITY = """
sum(
    kube_node_status_capacity{
        resource="memory"
    }
)
"""

MEMORY_USAGE = """
sum(
    container_memory_working_set_bytes{
        container!="",
        container!="POD"
    }
)
"""

MEMORY_UTILIZATION = """
(
    sum(
        container_memory_working_set_bytes{
            container!="",
            container!="POD"
        }
    )
/
    sum(
        kube_node_status_capacity{
            resource="memory"
        }
    )
) * 100
"""

STORAGE_CAPACITY = """
sum(
    kubelet_volume_stats_capacity_bytes
)
"""

STORAGE_USAGE = """
sum(
    kubelet_volume_stats_used_bytes
)
"""

STORAGE_UTILIZATION = """
(
    sum(
        kubelet_volume_stats_used_bytes
    )
/
    sum(
        kubelet_volume_stats_capacity_bytes
    )
) * 100
"""

POD_COUNT = """
count(
    kube_pod_info
)
"""


CPU_UTILIZATION_HISTORY = CPU_UTILIZATION

MEMORY_UTILIZATION_HISTORY = MEMORY_UTILIZATION

STORAGE_UTILIZATION_HISTORY = STORAGE_UTILIZATION

TOP_CPU_CONSUMERS = """
topk(
    10,
    sum by(namespace,pod)(
        rate(
            container_cpu_usage_seconds_total{
                container!="",
                container!="POD"
            }[5m]
        )
    )
)
"""

TOP_MEMORY_CONSUMERS = """
topk(
    10,
    sum by(namespace,pod)(
        container_memory_working_set_bytes{
            container!="",
            container!="POD"
        }
    )
)
"""
