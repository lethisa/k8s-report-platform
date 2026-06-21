from tempfile import NamedTemporaryFile

from kubernetes import config
from kubernetes.client import AppsV1Api, CoreV1Api, NetworkingV1Api, StorageV1Api


class KubernetesClient:
    def __init__(
        self,
        kubeconfig_content: str,
    ):
        self.kubeconfig_content = kubeconfig_content

    def _load_config(self) -> None:

        with NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.yaml',
        ) as temp_file:
            temp_file.write(self.kubeconfig_content)

            temp_file.flush()

            config.load_kube_config(config_file=temp_file.name)

    def core_api(self) -> CoreV1Api:

        self._load_config()

        return CoreV1Api()

    def apps_api(self) -> AppsV1Api:

        self._load_config()

        return AppsV1Api()

    def networking_api(self) -> NetworkingV1Api:

        self._load_config()

        return NetworkingV1Api()

    def storage_api(
        self,
    ) -> StorageV1Api:

        self._load_config()

        return StorageV1Api()

    def connect(self) -> CoreV1Api:
        return self.core_api()
