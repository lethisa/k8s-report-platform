from typing import cast

from kubernetes.client import V1NodeList
from kubernetes.client.rest import ApiException

from app.kubernetes.client import KubernetesClient


def test_cluster_connection(
    kubeconfig_content: str,
) -> dict:

    try:
        api = KubernetesClient(kubeconfig_content).connect()

        nodes = cast(
            V1NodeList,
            api.list_node(),
        )

        return {
            'success': True,
            'node_count': len(nodes.items or []),
            'error': None,
        }

    except ApiException as ex:
        return {
            'success': False,
            'node_count': 0,
            'error': str(ex),
        }

    except Exception as ex:
        return {
            'success': False,
            'node_count': 0,
            'error': str(ex),
        }
