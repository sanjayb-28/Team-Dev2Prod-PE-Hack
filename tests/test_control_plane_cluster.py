from datetime import datetime

from control_plane.cluster import (
    get_experiment_logs,
    get_resource_events,
    list_cluster_experiments,
    normalize_experiment,
    should_prune_experiment,
    settle_experiment_status,
)


def test_normalize_experiment_uses_product_type_and_running_status():
    payload = {
        "metadata": {
            "name": "pod-kill-3eacfc",
            "creationTimestamp": "2026-04-04T14:59:32Z",
            "labels": {
                "dev2prod.io/experiment-type": "pod-kill",
                "dev2prod.io/target-name": "workload-api-abc123",
                "app.kubernetes.io/name": "workload-api",
            },
        },
        "status": {
            "conditions": [
                {"type": "Selected", "status": "True"},
                {"type": "AllInjected", "status": "True"},
                {"type": "AllRecovered", "status": "False"},
            ],
            "experiment": {
                "desiredPhase": "Run",
                "containerRecords": [{"phase": "Injected"}],
            },
        },
    }

    assert normalize_experiment("podchaos", payload) == {
        "kind": "experiment",
        "type": "pod-kill",
        "name": "pod-kill-3eacfc",
        "status": "running",
        "targetKind": None,
        "target": "workload-api-abc123",
        "updatedAt": "2026-04-04T14:59:32Z",
    }


def test_normalize_experiment_marks_recovered_runs():
    payload = {
        "metadata": {
            "name": "latency-run",
            "creationTimestamp": "2026-04-04T15:10:00Z",
            "labels": {},
        },
        "status": {
            "conditions": [
                {"type": "AllRecovered", "status": "True"},
            ],
            "experiment": {
                "desiredPhase": "Stop",
                "containerRecords": [{"phase": "Recovered"}],
            },
        },
    }

    assert normalize_experiment("networkchaos", payload)["status"] == "recovered"


def test_normalize_experiment_captures_network_latency_details():
    payload = {
        "metadata": {
            "name": "latency-run",
            "creationTimestamp": "2026-04-04T15:10:00Z",
            "labels": {
                "dev2prod.io/experiment-type": "network-latency",
                "dev2prod.io/target-name": "workload-api",
            },
        },
        "spec": {
            "duration": "60s",
            "delay": {
                "latency": "120ms",
            },
        },
        "status": {},
    }

    assert normalize_experiment("networkchaos", payload) == {
        "kind": "experiment",
        "type": "network-latency",
        "name": "latency-run",
        "status": "pending",
        "targetKind": None,
        "target": "workload-api",
        "updatedAt": "2026-04-04T15:10:00Z",
        "durationSeconds": 60,
        "latencyMs": 120,
    }


def test_normalize_experiment_captures_cpu_stress_details():
    payload = {
        "metadata": {
            "name": "cpu-stress-025e18",
            "creationTimestamp": "2026-04-04T15:59:17Z",
            "labels": {
                "dev2prod.io/experiment-type": "cpu-stress",
                "dev2prod.io/target-kind": "deployment",
                "dev2prod.io/target-name": "workload-api",
            },
        },
        "spec": {
            "duration": "60s",
            "stressors": {
                "cpu": {"load": 80},
            },
        },
        "status": {
            "conditions": [
                {"type": "Selected", "status": "True"},
                {"type": "AllInjected", "status": "True"},
            ],
            "experiment": {
                "desiredPhase": "Run",
                "containerRecords": [{"phase": "Injected"}],
            },
        },
    }

    assert normalize_experiment("stresschaos", payload) == {
        "kind": "experiment",
        "type": "cpu-stress",
        "name": "cpu-stress-025e18",
        "status": "running",
        "targetKind": "deployment",
        "target": "workload-api",
        "updatedAt": "2026-04-04T15:59:17Z",
        "durationSeconds": 60,
        "cpuLoad": 80,
    }


def test_settle_experiment_status_marks_old_pod_kills_recovered():
    payload = {
        "kind": "experiment",
        "type": "pod-kill",
        "name": "pod-kill-3eacfc",
        "status": "running",
        "targetKind": None,
        "target": "workload-api-old-pod",
        "updatedAt": "2026-04-04T14:59:32Z",
    }

    assert settle_experiment_status(payload, {"workload-api-new-pod"}) == {
        "kind": "experiment",
        "type": "pod-kill",
        "name": "pod-kill-3eacfc",
        "status": "recovered",
        "targetKind": None,
        "target": "workload-api-old-pod",
        "updatedAt": "2026-04-04T14:59:32Z",
    }


def test_settle_experiment_status_keeps_live_pod_kills_running():
    payload = {
        "kind": "experiment",
        "type": "pod-kill",
        "name": "pod-kill-3eacfc",
        "status": "running",
        "targetKind": None,
        "target": "workload-api-live-pod",
        "updatedAt": "2026-04-04T14:59:32Z",
    }

    assert settle_experiment_status(payload, {"workload-api-live-pod"})["status"] == "running"


def test_should_prune_experiment_after_grace_period():
    payload = {
        "kind": "experiment",
        "type": "network-latency",
        "name": "network-latency-a84aa3",
        "status": "recovered",
        "targetKind": "service",
        "target": "workload-api",
        "updatedAt": "2026-04-04T15:31:27Z",
        "durationSeconds": 60,
    }

    assert should_prune_experiment(
        payload,
        now=datetime.fromisoformat("2026-04-04T15:36:00+00:00"),
    )


def test_should_not_prune_recent_recovered_experiment():
    payload = {
        "kind": "experiment",
        "type": "network-latency",
        "name": "network-latency-a84aa3",
        "status": "recovered",
        "targetKind": "service",
        "target": "workload-api",
        "updatedAt": "2026-04-04T15:31:27Z",
        "durationSeconds": 60,
    }

    assert not should_prune_experiment(
        payload,
        now=datetime.fromisoformat("2026-04-04T15:33:00+00:00"),
    )


def test_list_cluster_experiments_prunes_completed_runs(monkeypatch):
    deleted_paths: list[str] = []

    def fake_load_kubernetes_json(path: str):
        if "networkchaos" not in path:
            return {"items": []}

        return {
            "items": [
                {
                    "metadata": {
                        "name": "network-latency-a84aa3",
                        "creationTimestamp": "2026-04-04T15:31:27Z",
                        "labels": {
                            "dev2prod.io/experiment-type": "network-latency",
                            "dev2prod.io/target-kind": "service",
                            "dev2prod.io/target-name": "workload-api",
                        },
                    },
                    "spec": {
                        "duration": "60s",
                        "delay": {"latency": "120ms"},
                    },
                    "status": {
                        "conditions": [
                            {"type": "AllRecovered", "status": "True"},
                        ],
                        "experiment": {
                            "containerRecords": [{"phase": "Recovered"}],
                        },
                    },
                }
            ]
        }

    monkeypatch.setattr(
        "control_plane.cluster.load_kubernetes_json",
        fake_load_kubernetes_json,
    )
    monkeypatch.setattr(
        "control_plane.cluster.delete_kubernetes_resource",
        lambda path: deleted_paths.append(path),
    )
    monkeypatch.setattr(
        "control_plane.cluster.should_prune_experiment",
        lambda experiment, now=None: True,
    )

    experiments = list_cluster_experiments("dev2prod", {"workload-api-live-pod"})

    assert experiments == []
    assert deleted_paths == [
        "/apis/chaos-mesh.org/v1alpha1/namespaces/dev2prod/networkchaos/network-latency-a84aa3"
    ]


def test_get_experiment_logs_uses_latest_workload_pod(monkeypatch):
    config = {
        "CLUSTER_NAMESPACE": "dev2prod",
        "WORKLOAD_DEPLOYMENT_NAME": "workload-api",
    }
    resource = {
        "kind": "experiment",
        "name": "network-latency-a84aa3",
        "targetKind": "service",
        "target": "workload-api",
    }
    pods = [
        {"name": "workload-api-old", "updatedAt": "2026-04-04T15:30:00Z"},
        {"name": "workload-api-new", "updatedAt": "2026-04-04T15:31:00Z"},
    ]

    monkeypatch.setattr(
        "control_plane.cluster.read_pod_logs",
        lambda namespace, pod_name: [{"line": f"log from {pod_name}"}],
    )

    assert get_experiment_logs(config, resource, pods) == {
        "kind": "experiment",
        "name": "network-latency-a84aa3",
        "entries": [{"line": "log from workload-api-new"}],
        "note": "Showing the latest lines from workload pod workload-api-new.",
    }


def test_get_experiment_logs_falls_back_after_pod_kill(monkeypatch):
    config = {
        "CLUSTER_NAMESPACE": "dev2prod",
        "WORKLOAD_DEPLOYMENT_NAME": "workload-api",
    }
    resource = {
        "kind": "experiment",
        "name": "pod-kill-3eacfc",
        "targetKind": "pod",
        "target": "workload-api-old",
    }
    pods = [
        {"name": "workload-api-new", "updatedAt": "2026-04-04T15:31:00Z"},
    ]

    monkeypatch.setattr(
        "control_plane.cluster.read_pod_logs",
        lambda namespace, pod_name: [{"line": f"log from {pod_name}"}],
    )

    assert get_experiment_logs(config, resource, pods) == {
        "kind": "experiment",
        "name": "pod-kill-3eacfc",
        "entries": [{"line": "log from workload-api-new"}],
        "note": "Showing the latest lines from the replacement workload pod workload-api-new.",
    }


def test_get_resource_events_matches_chaos_resource_kinds(monkeypatch):
    config = {"CLUSTER_NAMESPACE": "dev2prod"}

    monkeypatch.setattr(
        "control_plane.cluster.list_namespace_resources",
        lambda current_config: {
            "mode": "cluster",
            "namespace": "dev2prod",
            "resources": {
                "deployments": [],
                "replicaSets": [],
                "pods": [],
                "services": [],
                "experiments": [],
            },
            "events": [
                {
                    "resourceKind": "PodChaos",
                    "resourceName": "pod-kill-3eacfc",
                    "reason": "Applied",
                    "timestamp": "2026-04-04T15:00:00Z",
                },
                {
                    "resourceKind": "PodNetworkChaos",
                    "resourceName": "pod-kill-3eacfc",
                    "reason": "Recovered",
                    "timestamp": "2026-04-04T15:01:00Z",
                },
                {
                    "resourceKind": "Pod",
                    "resourceName": "workload-api-abc123",
                    "reason": "Started",
                    "timestamp": "2026-04-04T14:59:00Z",
                },
            ],
        },
    )

    assert get_resource_events(config, "experiment", "pod-kill-3eacfc") == [
        {
            "resourceKind": "PodNetworkChaos",
            "resourceName": "pod-kill-3eacfc",
            "reason": "Recovered",
            "timestamp": "2026-04-04T15:01:00Z",
        },
        {
            "resourceKind": "PodChaos",
            "resourceName": "pod-kill-3eacfc",
            "reason": "Applied",
            "timestamp": "2026-04-04T15:00:00Z",
        }
    ]
