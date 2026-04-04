from control_plane.cluster import get_resource_events, normalize_experiment


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
