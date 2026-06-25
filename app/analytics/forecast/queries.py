CPU_UTILIZATION_HISTORY = """
100 *
(
    sum(
        rate(
            container_cpu_usage_seconds_total{
                container!="",
                image!=""
            }[1h]
        )
    )
)
/
sum(
    kube_node_status_capacity{
        resource="cpu"
    }
)
"""

MEMORY_UTILIZATION_HISTORY = """
100 *
sum(
    container_memory_working_set_bytes{
        container!="",
        image!=""
    }
)
/
sum(
    kube_node_status_capacity{
        resource="memory"
    }
)
"""

STORAGE_UTILIZATION_HISTORY = """
100 *
(
    sum(
        kubelet_volume_stats_used_bytes
    )
)
/
(
    sum(
        kubelet_volume_stats_capacity_bytes
    )
)
"""
