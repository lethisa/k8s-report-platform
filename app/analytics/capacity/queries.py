# app/analytics/capacity/queries.py

from __future__ import annotations

NAMESPACE_ACTIVE_QUERY = """
kube_namespace_status_phase{phase="Active"} == 1
"""


CURRENT_PODS_QUERY = """
count(kube_pod_info)
"""


CPU_REQUESTS_TOTAL_QUERY = """
sum(
  kube_pod_container_resource_requests{
    resource="cpu",
    unit="core",
    namespace!="",
    pod!=""
  }
)
"""


CPU_LIMITS_TOTAL_QUERY = """
sum(
  kube_pod_container_resource_limits{
    resource="cpu",
    unit="core",
    namespace!="",
    pod!=""
  }
)
"""


MEMORY_REQUESTS_TOTAL_QUERY = """
sum(
  kube_pod_container_resource_requests{
    resource="memory",
    unit="byte",
    namespace!="",
    pod!=""
  }
)
"""


MEMORY_LIMITS_TOTAL_QUERY = """
sum(
  kube_pod_container_resource_limits{
    resource="memory",
    unit="byte",
    namespace!="",
    pod!=""
  }
)
"""


CPU_PEAK_QUERY_TEMPLATE = """
max_over_time(
  sum(
    rate(container_cpu_usage_seconds_total{
      namespace!="",
      container!="",
      image!="",
      pod!=""
    }[5m])
  )[__TIME_RANGE__:5m]
)
"""


MEMORY_PEAK_QUERY_TEMPLATE = """
max_over_time(
  sum(
    container_memory_working_set_bytes{
      namespace!="",
      container!="",
      image!="",
      pod!=""
    }
  )[__TIME_RANGE__:5m]
)
"""
