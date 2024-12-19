# ih_muse_k8s/collector.py
import asyncio
import logging
from typing import Optional, Any
import time

import humanfriendly
from kubernetes import client, config
from kubernetes.client import CustomObjectsApi
from ih_muse import Muse

from ih_muse_k8s.config import ElementKind, MetricCode


def parse_cpu_quantity(quantity_str: str) -> float:
    try:
        if quantity_str.endswith("n"):
            return float(quantity_str[:-1]) / 1e9
        elif quantity_str.endswith("u"):
            return float(quantity_str[:-1]) / 1e6
        elif quantity_str.endswith("m"):
            return float(quantity_str[:-1]) / 1e3
        else:
            return float(quantity_str)
    except ValueError:
        logging.exception(f"Invalid CPU quantity: {quantity_str}")
        return 0.0


def parse_memory_quantity(quantity_str: str) -> int:
    try:
        return humanfriendly.parse_size(quantity_str, binary=True)
    except humanfriendly.InvalidSize:
        logging.exception(f"Invalid memory size: {quantity_str}")
        return 0


def filter_pods_by_namespace(
    pods: list[client.V1Pod], namespace_filter: Optional[str]
) -> list[client.V1Pod]:
    if namespace_filter is None:
        return pods
    return [p for p in pods if p.metadata.namespace == namespace_filter]


class KubernetesMetricsCollector:
    def __init__(self, muse: Muse, namespace_filter: Optional[str] = None):
        self.muse = muse
        self.registered_namespaces: dict[str, str] = {}
        self.registered_elements: dict[str, str] = {}
        self.metric_code_cpu = MetricCode.CPU_USAGE.value
        self.metric_code_memory = MetricCode.MEMORY_USAGE.value
        self.element_kind_namespace = ElementKind.NAMESPACE.value
        self.element_kind_pod = ElementKind.POD.value
        self.namespace_filter = namespace_filter

        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        self.v1 = client.CoreV1Api()
        self.metrics_api = CustomObjectsApi()

    @property
    def resolution_seconds(self) -> float:
        """The poet datastore resolution in seconds"""
        interval_td = self.muse.finest_resolution.to_timedelta()
        return interval_td.total_seconds()

    async def collect_and_send_metrics(self) -> None:
        while True:
            pod_list: client.V1PodList = self.v1.list_pod_for_all_namespaces(
                watch=False
            )
            pods: list[client.V1Pod] = filter_pods_by_namespace(
                pod_list.items, self.namespace_filter
            )
            pod_metrics = self.get_pod_metrics()
            metrics_map = self.build_metrics_map(pod_metrics)
            for pod in pods:
                await self.process_pod(pod, metrics_map)
            await asyncio.sleep(self.resolution_seconds)

    def build_metrics_map(
        self, pod_metrics_data: dict
    ) -> dict[tuple[str, str], dict[str, float]]:
        metrics_map: dict[tuple[str, str], dict[str, float]] = {}
        for item in pod_metrics_data.get("items", []):
            namespace = item["metadata"]["namespace"]
            pod_name = item["metadata"]["name"]
            containers = item["containers"]
            cpu_usage, memory_usage = 0.0, 0.0
            for container in containers:
                usage = container["usage"]
                cpu_usage += parse_cpu_quantity(usage.get("cpu", "0"))
                memory_usage += parse_memory_quantity(usage.get("memory", "0"))
            metrics_map[(namespace, pod_name)] = {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
            }
        return metrics_map

    async def process_pod(
        self, pod: client.V1Pod, metrics_map: dict[tuple[str, str], dict[str, float]]
    ) -> None:
        pod_uid = pod.metadata.uid
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace

        # Ensure namespace is registered
        parent_id = await self.ensure_namespace_registered(namespace)

        # Register the pod if not already registered
        if pod_uid not in self.registered_elements:
            metadata = {"namespace": namespace, "pod_name": pod_name}
            local_elem_id = await self.muse.register_element(
                kind_code=self.element_kind_pod,
                name=f"{namespace}/{pod_name}",
                metadata=metadata,
                parent_id=parent_id,
            )
            self.registered_elements[pod_uid] = local_elem_id
        else:
            local_elem_id = self.registered_elements[pod_uid]

        metrics = metrics_map.get((namespace, pod_name), {})
        cpu_usage = metrics.get("cpu_usage")
        memory_usage = metrics.get("memory_usage")

        if cpu_usage is not None:
            await self.muse.send_metric(local_elem_id, self.metric_code_cpu, cpu_usage)
        if memory_usage is not None:
            await self.muse.send_metric(
                local_elem_id, self.metric_code_memory, memory_usage
            )

    async def ensure_namespace_registered(self, namespace: str) -> str:
        if namespace not in self.registered_namespaces:
            local_elem_id = await self.muse.register_element(
                kind_code=self.element_kind_namespace,
                name=namespace,
                metadata={"namespace": namespace},
            )
            # self.muse.get_remote_element_id(local_elem_id)
            await self.wait_for_remote_elem_id(local_elem_id)
            self.registered_namespaces[namespace] = local_elem_id
        return self.registered_namespaces[namespace]

    def get_pod_metrics(self) -> dict[str, Any]:
        try:
            return self.metrics_api.list_cluster_custom_object(  # type: ignore
                group="metrics.k8s.io", version="v1beta1", plural="pods"
            )
        except Exception:
            logging.exception("Error getting pod metrics")
            return {}

    async def wait_for_remote_elem_id(self, local_elem_id: str) -> int:
        # Wait until the remote_element_id is available or timeout
        # timeout at poet's resolution * 3: enough poet cycles to register an element
        start_time = time.time()
        while time.time() - start_time < self.resolution_seconds * 3:
            remote_elem_id = self.muse.get_remote_element_id(local_elem_id)
            if remote_elem_id is not None:
                return remote_elem_id
            await asyncio.sleep(0.1)  # Sleep for a short duration to retry
            # TODO sleep based in resolution
        else:
            raise RemoteElemIdTimeout(local_elem_id)


class RemoteElemIdTimeout(TimeoutError):
    def __init__(self, local_elem_id: str):
        super().__init__(f"Wait for remote id of {local_elem_id=}")
