import control_plane.experiments as experiments


def test_create_experiment_refreshes_network_latency_status(monkeypatch):
    config = {
        "CLUSTER_NAMESPACE": "dev2prod",
        "WORKLOAD_DEPLOYMENT_NAME": "workload-api",
        "WORKLOAD_SERVICE_NAME": "workload-api",
        "CHAOS_MESH_ENABLED": True,
    }

    created_payload = {
        "metadata": {
            "name": "network-latency-a84aa3",
            "creationTimestamp": "2026-04-04T15:31:27Z",
            "labels": {
                "dev2prod.io/experiment-type": "network-latency",
                "dev2prod.io/target-name": "workload-api",
            },
        },
        "spec": {
            "duration": "60s",
            "delay": {"latency": "120ms"},
        },
        "status": {},
    }
    refreshed_payload = {
        "metadata": created_payload["metadata"],
        "spec": created_payload["spec"],
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

    monkeypatch.setattr(experiments, "ensure_chaos_mesh_ready", lambda config: None)
    monkeypatch.setattr(experiments.time, "sleep", lambda _: None)
    monkeypatch.setattr(experiments, "load_json_with_method", lambda path, method, payload: created_payload)
    monkeypatch.setattr(experiments, "read_experiment", lambda namespace, experiment_type, name: refreshed_payload)

    payload = experiments.create_experiment(
        config,
        {
            "type": "network-latency",
            "target": {"kind": "service", "name": "workload-api"},
            "durationSeconds": 60,
            "parameters": {"latencyMs": 120},
        },
    )

    assert payload == {
        "kind": "experiment",
        "type": "network-latency",
        "name": "network-latency-a84aa3",
        "status": "running",
        "targetKind": None,
        "target": "workload-api",
        "updatedAt": "2026-04-04T15:31:27Z",
        "durationSeconds": 60,
        "latencyMs": 120,
    }


def test_create_experiment_refreshes_cpu_stress_status(monkeypatch):
    config = {
        "CLUSTER_NAMESPACE": "dev2prod",
        "WORKLOAD_DEPLOYMENT_NAME": "workload-api",
        "WORKLOAD_SERVICE_NAME": "workload-api",
        "CHAOS_MESH_ENABLED": True,
    }

    created_payload = {
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
            "stressors": {"cpu": {"load": 80}},
        },
        "status": {},
    }
    refreshed_payload = {
        "metadata": created_payload["metadata"],
        "spec": created_payload["spec"],
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

    monkeypatch.setattr(experiments, "ensure_chaos_mesh_ready", lambda config: None)
    monkeypatch.setattr(experiments.time, "sleep", lambda _: None)
    monkeypatch.setattr(experiments, "load_json_with_method", lambda path, method, payload: created_payload)
    monkeypatch.setattr(experiments, "read_experiment", lambda namespace, experiment_type, name: refreshed_payload)

    payload = experiments.create_experiment(
        config,
        {
            "type": "cpu-stress",
            "target": {"kind": "deployment", "name": "workload-api"},
            "durationSeconds": 60,
            "parameters": {"cpuLoad": 80},
        },
    )

    assert payload == {
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
