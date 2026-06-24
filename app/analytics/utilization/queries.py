CPU_CAPACITY = """
sum(
    kube_node_status_capacity{
        resource="cpu"
    }
)
-
sum(
    kube_node_status_capacity{
        resource="cpu"
    }
    * on(node)
    group_left(role)
    kube_node_role{
        role="control-plane"
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
(
    sum(
        kube_node_status_capacity{
            resource="cpu"
        }
    )
    -
    sum(
        kube_node_status_capacity{
            resource="cpu"
        }
        * on(node)
        group_left(role)
        kube_node_role{
            role="control-plane"
        }
    )
)
) * 100
"""

MEMORY_CAPACITY = """
sum(
    kube_node_status_capacity{
        resource="memory"
    }
)
-
sum(
    kube_node_status_capacity{
        resource="memory"
    }
    * on(node)
    group_left(role)
    kube_node_role{
        role="control-plane"
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
(
    sum(
        kube_node_status_capacity{
            resource="memory"
        }
    )
    -
    sum(
        kube_node_status_capacity{
            resource="memory"
        }
        * on(node)
        group_left(role)
        kube_node_role{
            role="control-plane"
        }
    )
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
    kube_pod_status_phase{
        phase="Running"
    }
)
"""

POD_CAPACITY = """
sum(
    kube_node_status_capacity{
        resource="pods"
    }
)
-
sum(
    kube_node_status_capacity{
        resource="pods"
    }
    * on(node)
    group_left(role)
    kube_node_role{
        role="control-plane"
    }
)
"""

POD_UTILIZATION = """
(
    count(
        kube_pod_status_phase{
            phase="Running"
        }
    )
/
(
    sum(
        kube_node_status_capacity{
            resource="pods"
        }
    )
    -
    sum(
        kube_node_status_capacity{
            resource="pods"
        }
        * on(node)
        group_left(role)
        kube_node_role{
            role="control-plane"
        }
    )
)
) * 100
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

KUBERNETES_VERSION = """
kubernetes_build_info
"""

TOTAL_NODES = """
count(
    kube_node_info
)
"""

MASTER_NODES = """
count(
    kube_node_role{
        role="control-plane"
    }
)
"""

WORKER_NODES = """
count(
    kube_node_info
)
-
count(
    kube_node_role{
        role="control-plane"
    }
)
"""
