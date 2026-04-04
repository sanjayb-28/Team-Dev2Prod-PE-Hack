import control_plane
from control_plane import create_app


def test_control_plane_health_returns_ok():
    app = create_app()

    with app.test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_cluster_status_reports_locked_scope(monkeypatch):
    monkeypatch.setenv("CLUSTER_NAME", "dev2prod-cluster")
    monkeypatch.setenv("CLUSTER_NAMESPACE", "demo")
    monkeypatch.setenv("WORKLOAD_API_URL", "https://workload.dev2prod.test")
    monkeypatch.setenv("CHAOS_MESH_ENABLED", "true")

    app = create_app()

    def healthy_workload(base_url, timeout=1.0):
        assert base_url == "https://workload.dev2prod.test"
        return {"status": "healthy"}

    monkeypatch.setattr(control_plane, "get_workload_status", healthy_workload)

    with app.test_client() as client:
        response = client.get("/api/cluster/status")

    assert response.status_code == 200
    assert response.get_json() == {
        "data": {
            "clusterName": "dev2prod-cluster",
            "namespace": "demo",
            "provider": "digitalocean",
            "mode": "local",
            "scopeLocked": True,
            "controlPlane": {"status": "healthy"},
            "workload": {"status": "healthy"},
            "chaosMesh": {"status": "ready"},
            "workloadScope": {
                "deploymentName": "workload-api",
                "serviceName": "workload-api",
                "podPrefix": "workload-api-",
            },
        }
    }


def test_cluster_status_surfaces_unreachable_workload(monkeypatch):
    monkeypatch.delenv("CHAOS_MESH_ENABLED", raising=False)

    app = create_app()

    def unreachable_workload(base_url, timeout=1.0):
        return {
            "status": "unreachable",
            "message": "Health check is unavailable.",
        }

    monkeypatch.setattr(control_plane, "get_workload_status", unreachable_workload)

    with app.test_client() as client:
        response = client.get("/api/cluster/status")

    payload = response.get_json()["data"]
    assert response.status_code == 200
    assert payload["scopeLocked"] is True
    assert payload["workload"] == {
        "status": "unreachable",
        "message": "Health check is unavailable.",
    }
    assert payload["chaosMesh"] == {"status": "unavailable"}
    assert payload["workloadScope"]["deploymentName"] == "workload-api"


def test_resources_return_local_scope_when_not_in_cluster(monkeypatch):
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    monkeypatch.setenv("WORKLOAD_DEPLOYMENT_NAME", "dev2prod-api")
    monkeypatch.setenv("CONTROL_PLANE_DEPLOYMENT_NAME", "dev2prod-control")
    monkeypatch.setenv("WORKLOAD_SERVICE_NAME", "dev2prod-service")

    app = create_app()

    with app.test_client() as client:
        response = client.get("/api/resources")

    payload = response.get_json()["data"]
    assert response.status_code == 200
    assert payload["mode"] == "local"
    assert payload["namespace"] == "dev2prod"
    assert payload["resources"]["deployments"][0]["name"] == "dev2prod-api"
    assert payload["resources"]["deployments"][1]["name"] == "dev2prod-control"
    assert payload["resources"]["services"][0]["name"] == "dev2prod-service"
    assert payload["resources"]["pods"] == []
    assert payload["events"] == []


def test_resources_return_cluster_payload(monkeypatch):
    monkeypatch.setenv("CLUSTER_NAMESPACE", "demo")

    app = create_app()

    def fake_resources(config):
        assert config["CLUSTER_NAMESPACE"] == "demo"
        return {
            "mode": "cluster",
            "namespace": "demo",
            "resources": {
                "deployments": [{"name": "dev2prod-api", "kind": "deployment"}],
                "replicaSets": [],
                "pods": [{"name": "dev2prod-api-123", "kind": "pod"}],
                "services": [{"name": "dev2prod-service", "kind": "service"}],
                "experiments": [{"name": "latency-test", "kind": "experiment"}],
            },
            "events": [{"name": "api-ready", "reason": "Ready"}],
        }

    monkeypatch.setattr(control_plane, "list_namespace_resources", fake_resources)

    with app.test_client() as client:
        response = client.get("/api/resources")

    payload = response.get_json()["data"]
    assert response.status_code == 200
    assert payload["mode"] == "cluster"
    assert payload["resources"]["deployments"][0]["name"] == "dev2prod-api"
    assert payload["resources"]["pods"][0]["name"] == "dev2prod-api-123"
    assert payload["resources"]["experiments"][0]["name"] == "latency-test"
    assert payload["events"][0]["reason"] == "Ready"


def test_resource_detail_returns_named_resource(monkeypatch):
    app = create_app()

    def fake_resource_detail(config, kind, name):
        assert kind == "deployment"
        assert name == "dev2prod-api"
        return {"kind": "deployment", "name": "dev2prod-api", "status": "healthy"}

    monkeypatch.setattr(control_plane, "get_resource_detail", fake_resource_detail)

    with app.test_client() as client:
        response = client.get("/api/resources/deployment/dev2prod-api")

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "kind": "deployment",
        "name": "dev2prod-api",
        "status": "healthy",
    }


def test_resource_detail_returns_not_found(monkeypatch):
    app = create_app()

    monkeypatch.setattr(control_plane, "get_resource_detail", lambda config, kind, name: None)

    with app.test_client() as client:
        response = client.get("/api/resources/pod/missing-pod")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_resource_events_return_filtered_items(monkeypatch):
    app = create_app()

    def fake_resource_events(config, kind, name):
        assert kind == "pod"
        assert name == "dev2prod-api-123"
        return [
            {
                "name": "pod-ready",
                "reason": "Ready",
                "resourceKind": "Pod",
                "resourceName": "dev2prod-api-123",
            }
        ]

    monkeypatch.setattr(control_plane, "get_resource_events", fake_resource_events)

    with app.test_client() as client:
        response = client.get("/api/resources/pod/dev2prod-api-123/events")

    assert response.status_code == 200
    assert response.get_json()["data"] == [
        {
            "name": "pod-ready",
            "reason": "Ready",
            "resourceKind": "Pod",
            "resourceName": "dev2prod-api-123",
        }
    ]


def test_resource_logs_return_payload(monkeypatch):
    app = create_app()

    def fake_resource_logs(config, kind, name):
        assert kind == "pod"
        assert name == "dev2prod-api-123"
        return {
            "kind": "pod",
            "name": "dev2prod-api-123",
            "entries": [{"line": "ready to serve traffic"}],
            "note": "Showing the latest lines from this pod.",
        }

    monkeypatch.setattr(control_plane, "get_resource_logs", fake_resource_logs)

    with app.test_client() as client:
        response = client.get("/api/resources/pod/dev2prod-api-123/logs")

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "kind": "pod",
        "name": "dev2prod-api-123",
        "entries": [{"line": "ready to serve traffic"}],
        "note": "Showing the latest lines from this pod.",
    }


def test_list_experiments_returns_payload(monkeypatch):
    monkeypatch.setenv("CHAOS_MESH_ENABLED", "true")
    app = create_app()

    monkeypatch.setattr(
        control_plane,
        "list_experiments",
        lambda config: [
            {
                "name": "pod-kill-run",
                "type": "pod-kill",
                "status": "running",
                "target": "workload-api",
            }
        ],
    )

    with app.test_client() as client:
        response = client.get("/api/experiments")

    assert response.status_code == 200
    assert response.get_json()["data"] == [
        {
            "name": "pod-kill-run",
            "type": "pod-kill",
            "status": "running",
            "target": "workload-api",
        }
    ]


def test_create_experiment_returns_created_payload(monkeypatch):
    monkeypatch.setenv("CHAOS_MESH_ENABLED", "true")
    app = create_app()

    def fake_create_experiment(config, payload):
        assert payload == {
            "type": "pod-kill",
            "target": {"kind": "deployment", "name": "workload-api"},
            "durationSeconds": 30,
            "parameters": {},
        }
        return {
            "name": "pod-kill-run",
            "type": "pod-kill",
            "status": "running",
            "target": "workload-api",
        }

    monkeypatch.setattr(control_plane, "create_experiment", fake_create_experiment)

    with app.test_client() as client:
        response = client.post(
            "/api/experiments",
            json={
                "type": "pod-kill",
                "target": {"kind": "deployment", "name": "workload-api"},
                "durationSeconds": 30,
                "parameters": {},
            },
        )

    assert response.status_code == 201
    assert response.get_json()["data"]["name"] == "pod-kill-run"


def test_create_experiment_returns_validation_error(monkeypatch):
    app = create_app()

    def fake_create_experiment(config, payload):
        raise control_plane.ExperimentRequestError(
            "Fault tooling is not ready in this cluster yet.",
            code="chaos_mesh_unavailable",
            status_code=409,
        )

    monkeypatch.setattr(control_plane, "create_experiment", fake_create_experiment)

    with app.test_client() as client:
        response = client.post("/api/experiments", json={"type": "pod-kill"})

    assert response.status_code == 409
    assert response.get_json()["error"] == {
        "code": "chaos_mesh_unavailable",
        "message": "Fault tooling is not ready in this cluster yet.",
    }


def test_cancel_experiment_returns_payload(monkeypatch):
    monkeypatch.setenv("CHAOS_MESH_ENABLED", "true")
    app = create_app()

    def fake_cancel_experiment(config, name):
        assert name == "pod-kill-run"
        return {
            "name": "pod-kill-run",
            "type": "pod-kill",
            "status": "cancelled",
        }

    monkeypatch.setattr(control_plane, "cancel_experiment", fake_cancel_experiment)

    with app.test_client() as client:
        response = client.post("/api/experiments/pod-kill-run/cancel")

    assert response.status_code == 200
    assert response.get_json()["data"] == {
        "name": "pod-kill-run",
        "type": "pod-kill",
        "status": "cancelled",
    }


def test_scale_lab_returns_payload(monkeypatch):
    app = create_app()

    monkeypatch.setattr(
        control_plane,
        "build_scale_lab_payload",
        lambda config: {
            "enabled": True,
            "mode": "cluster",
            "lanes": [
                {
                    "id": "bronze-baseline",
                    "label": "Bronze baseline",
                    "concurrency": 50,
                    "durationSeconds": 20,
                    "replicas": 1,
                }
            ],
            "workloadScale": {"desiredReplicas": 1, "readyReplicas": 1, "availableReplicas": 1},
            "runs": [],
        },
    )

    with app.test_client() as client:
        response = client.get("/api/scale-lab")

    assert response.status_code == 200
    assert response.get_json()["data"]["enabled"] is True
    assert response.get_json()["data"]["lanes"][0]["id"] == "bronze-baseline"


def test_scale_lab_run_returns_created_payload(monkeypatch):
    app = create_app()

    def fake_create_scale_run(config, payload):
        assert payload == {"lane": "silver-scale-out"}
        return {
            "name": "scale-silver-a1b2c3",
            "lane": "silver-scale-out",
            "label": "Silver scale-out",
            "status": "running",
            "concurrency": 200,
            "durationSeconds": 30,
            "replicas": 2,
        }

    monkeypatch.setattr(control_plane, "create_scale_run", fake_create_scale_run)

    with app.test_client() as client:
        response = client.post("/api/scale-lab/runs", json={"lane": "silver-scale-out"})

    assert response.status_code == 201
    assert response.get_json()["data"]["name"] == "scale-silver-a1b2c3"


def test_scale_lab_run_returns_validation_error(monkeypatch):
    app = create_app()

    def fake_create_scale_run(config, payload):
        raise control_plane.ExperimentRequestError(
            "Scale lab runs are only available in the live cluster.",
            code="scale_lab_unavailable",
            status_code=409,
        )

    monkeypatch.setattr(control_plane, "create_scale_run", fake_create_scale_run)

    with app.test_client() as client:
        response = client.post("/api/scale-lab/runs", json={"lane": "bronze-baseline"})

    assert response.status_code == 409
    assert response.get_json()["error"] == {
        "code": "scale_lab_unavailable",
        "message": "Scale lab runs are only available in the live cluster.",
    }


def test_stream_returns_cluster_snapshot(monkeypatch):
    app = create_app()

    monkeypatch.setattr(
        control_plane,
        "get_workload_status",
        lambda base_url, timeout=1.0: {"status": "healthy"},
    )
    monkeypatch.setattr(
        control_plane,
        "list_namespace_resources",
        lambda config: {
            "mode": "local",
            "namespace": "dev2prod",
            "resources": {"deployments": [], "replicaSets": [], "pods": [], "services": [], "experiments": []},
            "events": [],
        },
    )

    with app.test_client() as client:
        response = client.get("/api/stream?once=1")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert "event: cluster_snapshot" in body
    assert '"status": {"clusterName": "dev2prod-local"' in body
    assert '"workloadScope": {"deploymentName": "workload-api"' in body


def test_control_plane_adds_client_origin_header(monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_ALLOWED_ORIGIN", "http://127.0.0.1:5173")

    app = create_app()

    with app.test_client() as client:
        response = client.get("/api/resources")

    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
