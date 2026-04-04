from control_plane.scale_lab import (
    SCALE_LANES,
    build_scale_lab_payload,
    parse_run_status,
    parse_summary_from_logs,
)


def test_parse_summary_from_logs_returns_compact_metrics():
    logs = """
something before
__DEV2PROD_SUMMARY__
{"metrics":{"http_req_duration":{"values":{"avg":42.4,"p(95)":91.7}},"http_req_failed":{"values":{"rate":0.01}},"http_reqs":{"values":{"count":1200}}}}
"""

    assert parse_summary_from_logs(logs) == {
        "p95LatencyMs": 91.7,
        "avgLatencyMs": 42.4,
        "errorRate": 0.01,
        "requestCount": 1200,
    }


def test_parse_run_status_maps_job_state():
    assert parse_run_status({"status": {"active": 1}}) == "running"
    assert parse_run_status({"status": {"succeeded": 1}}) == "completed"
    assert parse_run_status({"status": {"failed": 1}}) == "failed"
    assert parse_run_status({"status": {}}) == "pending"


def test_build_scale_lab_payload_returns_local_mode_without_cluster(monkeypatch):
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)

    payload = build_scale_lab_payload(
        {
            "CLUSTER_NAMESPACE": "dev2prod",
            "WORKLOAD_DEPLOYMENT_NAME": "workload-api",
        }
    )

    assert payload == {
        "enabled": False,
        "mode": "local",
        "lanes": [
            {
                "id": lane,
                "label": config["label"],
                "description": config["description"],
                "concurrency": config["concurrency"],
                "durationSeconds": config["durationSeconds"],
                "replicas": config["replicas"],
            }
            for lane, config in SCALE_LANES.items()
        ],
        "workloadScale": None,
        "runs": [],
    }
