# ih_muse_k8s/config.py

from enum import StrEnum


class ElementKind(StrEnum):
    NAMESPACE = "k8s_namespace"
    POD = "k8s_pod"
    DEPLOYMENT = "k8s_deployment"
    CRONJOB = "k8s_cronjob"


class MetricCode(StrEnum):
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
