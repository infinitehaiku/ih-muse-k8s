# tests/test_helpers.py

from kubernetes.client import V1Pod, V1ObjectMeta

from ih_muse_k8s.collector import (
    filter_pods_by_namespace,
    parse_cpu_quantity,
    parse_memory_quantity,
)


def test_parse_cpu_quantity() -> None:
    assert parse_cpu_quantity("100m") == 0.1
    assert parse_cpu_quantity("1") == 1.0
    assert parse_cpu_quantity("100u") == 0.0001
    assert parse_cpu_quantity("invalid") == 0.0


def test_parse_memory_quantity() -> None:
    assert parse_memory_quantity("128Mi") == 134217728
    assert parse_memory_quantity("128M") == 134217728
    assert parse_memory_quantity("invalid") == 0


def test_filter_pods_by_namespace() -> None:
    pod1 = V1Pod(metadata=V1ObjectMeta(name="pod1", namespace="test-ns"))
    pod2 = V1Pod(metadata=V1ObjectMeta(name="pod2", namespace="other-ns"))
    pods = [pod1, pod2]

    filtered = filter_pods_by_namespace(pods, "test-ns")
    assert len(filtered) == 1
    assert filtered[0].metadata.name == "pod1"

    all_pods = filter_pods_by_namespace(pods, None)
    assert len(all_pods) == 2
