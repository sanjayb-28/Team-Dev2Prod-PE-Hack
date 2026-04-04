from control_plane.cluster import (
    get_resource_events,
    normalize_experiment,
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
        "target": "workload-api",
        "updatedAt": "2026-04-04T15:10:00Z",
        "durationSeconds": 60,
        "latencyMs": 120,
    }


def test_settle_experiment_status_marks_old_pod_kills_recovered():
    payload = {
        "kind": "experiment",
        "type": "pod-kill",
        "name": "pod-kill-3eacfc",
        "status": "running",
        "target": "workload-api-old-pod",
        "updatedAt": "2026-04-04T14:59:32Z",
    }

    assert settle_experiment_status(payload, {"workload-api-new-pod"}) == {
        "kind": "experiment",
        "type": "pod-kill",
        "name": "pod-kill-3eacfc",
        "status": "recovered",
        "target": "workload-api-old-pod",
        "updatedAt": "2026-04-04T14:59:32Z",
    }


def test_settle_experiment_status_keeps_live_pod_kills_running():
    payload = {
        "kind": "experiment",
        "type": "pod-kill",
        "name": "pod-kill-3eacfc",
        "status": "running",
        "target": "workload-api-live-pod",
        "updatedAt": "2026-04-04T14:59:32Z",
    }

    assert settle_experiment_status(payload, {"workload-api-live-pod"})["status"] == "running"


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
                },
                {
                    "resourceKind": "Pod",
                    "resourceName": "workload-api-abc123",
                    "reason": "Started",
                },
            ],
        },
    )

    assert get_resource_events(config, "experiment", "pod-kill-3eacfc") == [
        {
            "resourceKind": "PodChaos",
            "resourceName": "pod-kill-3eacfc",
            "reason": "Applied",
        }
    ]
