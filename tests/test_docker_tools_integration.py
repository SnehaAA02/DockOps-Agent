"""
Integration tests for docker_tools — these use a REAL Docker daemon, not
mocks. They spin up a disposable container, exercise every tool against it,
and tear it down afterward.

Requirements to run:
    - Docker installed and the daemon running
    - Network access to pull `alpine:latest` (~5 MB) the first time

If Docker isn't available on PATH, the whole module is skipped rather than
failed, so `pytest` still passes cleanly on a machine without Docker (e.g.
a laptop that only has the agent code checked out, not a full dev setup).
On GitHub Actions' ubuntu-latest runners, Docker is preinstalled, so these
run for real in CI on every push.
"""

from __future__ import annotations

import shutil
import subprocess
import time
import uuid

import pytest

from dockops_agent.tools.docker_tools import (
    container_logs,
    container_stats,
    list_containers,
    list_images,
    start_container,
    stop_container,
)

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="Docker is not installed / not on PATH — skipping integration tests.",
)

TEST_IMAGE = "alpine:latest"


@pytest.fixture(scope="module")
def test_container():
    """Starts a real, disposable Alpine container that idles and logs a
    heartbeat, so logs/stats/stop/start all have something real to act on.
    Tears it down unconditionally at the end of the module."""
    name = f"dockops-agent-test-{uuid.uuid4().hex[:8]}"

    subprocess.run(["docker", "pull", TEST_IMAGE], check=True, capture_output=True)
    subprocess.run(
        [
            "docker", "run", "-d", "--name", name,
            TEST_IMAGE,
            "sh", "-c", "while true; do echo heartbeat; sleep 1; done",
        ],
        check=True,
        capture_output=True,
    )
    time.sleep(1)  # give it a moment to emit at least one log line

    yield name

    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)


def test_list_containers_finds_running_container(test_container):
    result = list_containers.invoke({"show_all": False})
    assert test_container in result


def test_list_containers_all_includes_stopped(test_container):
    stop_container.invoke({"container_name": test_container})
    time.sleep(1)
    try:
        result = list_containers.invoke({"show_all": True})
        assert test_container in result
    finally:
        start_container.invoke({"container_name": test_container})
        time.sleep(1)


def test_container_logs_returns_real_output(test_container):
    result = container_logs.invoke({"container_name": test_container, "tail_lines": 5})
    assert "heartbeat" in result


def test_stop_and_start_container_roundtrip(test_container):
    stop_result = stop_container.invoke({"container_name": test_container})
    assert test_container in stop_result

    ps_after_stop = list_containers.invoke({"show_all": False})
    assert test_container not in ps_after_stop

    start_result = start_container.invoke({"container_name": test_container})
    assert test_container in start_result
    time.sleep(1)

    ps_after_start = list_containers.invoke({"show_all": False})
    assert test_container in ps_after_start


def test_container_stats_includes_running_container(test_container):
    result = container_stats.invoke({})
    assert test_container in result


def test_list_images_includes_pulled_image(test_container):
    result = list_images.invoke({})
    assert "alpine" in result.lower()


def test_container_logs_rejects_invalid_name():
    result = container_logs.invoke({"container_name": "bad; rm -rf /", "tail_lines": 5})
    assert "not a valid Docker container" in result


def test_actions_on_nonexistent_container_fail_gracefully():
    result = start_container.invoke({"container_name": "definitely-does-not-exist-12345"})
    assert "Docker command failed" in result
