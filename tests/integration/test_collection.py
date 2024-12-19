# tests/test_integration.py

import asyncio
import pytest
import logging
from pathlib import Path

from piceli.k8s.k8s_objects.base import K8sObject
from ih_muse import Muse, Config, ClientType, TimestampResolution
from ih_muse.proto import ElementKindRegistration, MetricDefinition
from ih_muse_k8s.collector import KubernetesMetricsCollector
from ih_muse_k8s.config import ElementKind, MetricCode

logging.basicConfig(level=logging.INFO)


@pytest.mark.asyncio
async def test_metrics_collection(
    test_namespace: str,
    deployed_resources: list[K8sObject],
    tmp_path: Path,
) -> None:
    # Set up Muse
    recording_path = tmp_path / "muse_recording.json"
    element_kinds = [
        ElementKindRegistration(ElementKind.POD.value, "Pod", "Kubernetes Pod"),
        ElementKindRegistration(
            ElementKind.DEPLOYMENT.value, "Deployment", "Kubernetes Deployment"
        ),
        ElementKindRegistration(
            ElementKind.CRONJOB.value, "CronJob", "Kubernetes CronJob"
        ),
        ElementKindRegistration(
            ElementKind.NAMESPACE.value, "Namespace", "Kubernetes Namespace"
        ),
    ]
    metric_definitions = [
        MetricDefinition(
            MetricCode.CPU_USAGE.value, "CPU Usage", "CPU usage of the resource"
        ),
        MetricDefinition(
            MetricCode.MEMORY_USAGE.value,
            "Memory Usage",
            "Memory usage of the resource",
        ),
    ]
    muse_config = Config(
        endpoints=["http://localhost:8080"],
        client_type=ClientType.Mock,
        default_resolution=TimestampResolution.Seconds,
        element_kinds=element_kinds,
        metric_definitions=metric_definitions,
        max_reg_elem_retries=3,
        recording_enabled=True,
        recording_path=str(recording_path),
    )
    muse = Muse(muse_config)
    await muse.initialize(timeout=5.0)

    # Pass the test_namespace to filter pods by that namespace
    collector = KubernetesMetricsCollector(muse, namespace_filter=test_namespace)

    # Run the collector briefly
    collection_task = asyncio.create_task(collector.collect_and_send_metrics())
    await asyncio.sleep(10)
    collection_task.cancel()
    try:
        await collection_task
    except asyncio.CancelledError:
        pass

    # Check the recording file
    assert recording_path.exists(), "Recording file was not created"
    content = recording_path.read_text()
    assert "k8s_pod" in content, "Expected pod registrations not found"
    assert (
        "cpu_usage" in content or "memory_usage" in content
    ), "Expected metrics not found in recording"

    raise ValueError(f"{test_namespace=}:\n\n{content}")
