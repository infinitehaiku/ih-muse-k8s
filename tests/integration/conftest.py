# conftest.py
import os
import time
from typing import Generator

import pytest
from kubernetes.client.exceptions import ApiException

from piceli.k8s.k8s_client.client import ClientContext
from piceli.k8s.k8s_objects.base import K8sObject
from piceli.k8s.ops import loader
from piceli.k8s.ops.deploy import deploy_op


@pytest.fixture
def ctx() -> ClientContext:
    return ClientContext()


@pytest.fixture
def resources() -> list[K8sObject]:
    """
    Load Kubernetes resources from a YAML file.

    Ensure you have a 'resources' directory with 'deployment.yml'
    containing the Kubernetes objects you want to deploy.
    """
    test_yaml = os.path.join(os.path.dirname(__file__), "resources", "deployment.yml")
    return list(loader.load_resources_from_files([test_yaml]))


@pytest.fixture(scope="function")
def test_namespace(
    request: pytest.FixtureRequest,
    ctx: ClientContext,
) -> Generator[str, None, None]:
    """
    Create a unique namespace for each test function.

    The namespace is created before the test and deleted after the test completes.
    """
    # Generate namespace name based on the test function name
    namespace_name = f"test-{request.node.name.replace('_', '-')}"

    try:
        # If namespace exists, delete it first
        ctx.core_api.delete_namespace(name=namespace_name)

        # Wait for namespace to be fully deleted
        while True:
            try:
                ctx.core_api.read_namespace(name=namespace_name)
                time.sleep(1)
            except ApiException:
                break
    except ApiException:
        # Namespace didn't exist, which is fine
        pass

    # Create new namespace
    namespace_body = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {"name": namespace_name},
    }
    ctx.core_api.create_namespace(body=namespace_body)

    try:
        yield namespace_name
    finally:
        # Clean up namespace after test
        try:
            ctx.core_api.delete_namespace(name=namespace_name)
        except Exception as e:
            print(f"Failed to delete namespace {namespace_name}: {e}")


@pytest.fixture(scope="function")
def deployed_resources(
    ctx: ClientContext, test_namespace: str, resources: list[K8sObject]
) -> list[K8sObject]:
    """
    Deploy resources to the test namespace before the test.

    This fixture ensures that the specified resources are deployed
    and available for the test to use.
    """
    # Deploy resources to the test namespace
    executor = deploy_op.deploy(ctx, resources, test_namespace)
    assert executor.is_done, "Failed to deploy resources"

    return resources
