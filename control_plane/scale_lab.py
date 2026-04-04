import json
import secrets
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from control_plane.cluster import (
    SERVICE_ACCOUNT_CA_PATH,
    build_api_base,
    is_cluster_mode,
    load_kubernetes_json,
    load_kubernetes_text,
    read_service_account_token,
)
from control_plane.experiments import ExperimentRequestError


SCALE_LANES = {
    "bronze-baseline": {
        "label": "Bronze baseline",
        "description": "Run a 50-user check against one workload instance.",
        "concurrency": 50,
        "durationSeconds": 20,
        "replicas": 1,
    },
    "silver-scale-out": {
        "label": "Silver scale-out",
        "description": "Scale the workload to two replicas and run a 200-user check.",
        "concurrency": 200,
        "durationSeconds": 30,
        "replicas": 2,
    },
}
JOB_IMAGE = "grafana/k6:0.51.0"
JOB_LABEL_KEY = "dev2prod.io/scale-lane"
JOB_MANAGER_LABEL = "dev2prod.io/managed-by"
JOB_MANAGER_VALUE = "dev2prod-control-plane"
SUMMARY_MARKER = "__DEV2PROD_SUMMARY__"


def scale_lab_ready() -> bool:
    return is_cluster_mode()


def load_json_with_method(
    path: str,
    method: str,
    payload: dict | None = None,
    timeout: float = 4.0,
    content_type: str = "application/json",
) -> dict:
    request = Request(f"{build_api_base()}{path}", method=method.upper())
    request.add_header("Authorization", f"Bearer {read_service_account_token()}")
    request.add_header("Accept", "application/json")

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request.add_header("Content-Type", content_type)

    context = ssl.create_default_context(cafile=SERVICE_ACCOUNT_CA_PATH)

    with urlopen(request, timeout=timeout, context=context, data=data) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def validate_lane(value: object) -> str:
    lane = str(value or "").strip()
    if lane not in SCALE_LANES:
        raise ExperimentRequestError("Choose a valid scale lane.")
    return lane


def get_workload_scale(config: dict) -> dict:
    namespace = config["CLUSTER_NAMESPACE"]
    deployment_name = config["WORKLOAD_DEPLOYMENT_NAME"]
    payload = load_kubernetes_json(
        f"/apis/apps/v1/namespaces/{namespace}/deployments/{quote(deployment_name)}"
    )
    spec = payload.get("spec", {})
    status = payload.get("status", {})
    return {
        "desiredReplicas": spec.get("replicas", 1),
        "readyReplicas": status.get("readyReplicas", 0),
        "availableReplicas": status.get("availableReplicas", 0),
    }


def scale_workload(config: dict, replicas: int):
    namespace = config["CLUSTER_NAMESPACE"]
    deployment_name = config["WORKLOAD_DEPLOYMENT_NAME"]
    load_json_with_method(
        f"/apis/apps/v1/namespaces/{namespace}/deployments/{quote(deployment_name)}/scale",
        "PATCH",
        {"spec": {"replicas": replicas}},
        content_type="application/merge-patch+json",
    )


def wait_for_replicas(config: dict, replicas: int, timeout_seconds: int = 120):
    started_at = time.time()
    while time.time() - started_at < timeout_seconds:
        scale = get_workload_scale(config)
        if (
            scale["desiredReplicas"] == replicas
            and scale["readyReplicas"] >= replicas
            and scale["availableReplicas"] >= replicas
        ):
            return scale
        time.sleep(2)

    raise ExperimentRequestError(
        "The workload did not settle at the requested replica count in time.",
        code="scale_not_ready",
        status_code=504,
    )


def render_k6_script(config: dict, lane: str) -> str:
    lane_config = SCALE_LANES[lane]
    threshold_lines = ""
    if lane == "silver-scale-out":
        threshold_lines = """
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.05'],
  },"""

    return f"""import http from 'k6/http'
import {{ check, sleep }} from 'k6'

export const options = {{
  vus: {lane_config['concurrency']},{threshold_lines}
  duration: '{lane_config['durationSeconds']}s',
}}

const baseUrl = 'http://{config["WORKLOAD_SERVICE_NAME"]}:5000'
const paths = ['/health', '/urls', '/urls?is_active=true']

export default function () {{
  const path = paths[Math.floor(Math.random() * paths.length)]
  const response = http.get(`${{baseUrl}}${{path}}`)

  check(response, {{
    'path returns 200': (result) => result.status === 200,
  }})

  sleep(1)
}}
"""


def build_job_manifest(config: dict, lane: str) -> dict:
    lane_config = SCALE_LANES[lane]
    job_name = f"scale-{lane.split('-')[0]}-{secrets.token_hex(3)}"
    script = render_k6_script(config, lane)
    shell_script = (
        "cat <<'EOF' >/tmp/scale.js\n"
        f"{script}"
        "EOF\n"
        "k6 run --summary-export=/tmp/summary.json /tmp/scale.js\n"
        f"echo '{SUMMARY_MARKER}'\n"
        "cat /tmp/summary.json\n"
    )

    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": job_name,
            "namespace": config["CLUSTER_NAMESPACE"],
            "labels": {
                JOB_LABEL_KEY: lane,
                JOB_MANAGER_LABEL: JOB_MANAGER_VALUE,
                "app.kubernetes.io/name": config["WORKLOAD_DEPLOYMENT_NAME"],
            },
        },
        "spec": {
            "ttlSecondsAfterFinished": 600,
            "backoffLimit": 0,
            "template": {
                "metadata": {
                    "labels": {
                        JOB_LABEL_KEY: lane,
                        JOB_MANAGER_LABEL: JOB_MANAGER_VALUE,
                    }
                },
                "spec": {
                    "restartPolicy": "Never",
                    "containers": [
                        {
                            "name": "k6",
                            "image": JOB_IMAGE,
                            "command": ["/bin/sh", "-lc"],
                            "args": [shell_script],
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "500m", "memory": "512Mi"},
                            },
                        }
                    ],
                },
            },
        },
    }


def parse_run_status(item: dict) -> str:
    status = item.get("status", {})
    if status.get("failed", 0) > 0:
        return "failed"
    if status.get("succeeded", 0) > 0:
        return "completed"
    if status.get("active", 0) > 0:
        return "running"
    return "pending"


def parse_summary_from_logs(text: str) -> dict | None:
    if SUMMARY_MARKER not in text:
        return None

    _, summary = text.split(SUMMARY_MARKER, 1)
    summary = summary.strip()
    if not summary:
        return None

    try:
        payload = json.loads(summary)
    except json.JSONDecodeError:
        return None

    metrics = payload.get("metrics", {})
    duration = metrics.get("http_req_duration", {})
    failed = metrics.get("http_req_failed", {})
    requests = metrics.get("http_reqs", {})

    def metric_value(metric: dict, key: str, fallback: float = 0) -> float:
        if not isinstance(metric, dict):
            return fallback
        if isinstance(metric.get(key), (int, float)):
            return float(metric[key])
        values = metric.get("values", {})
        if isinstance(values, dict) and isinstance(values.get(key), (int, float)):
            return float(values[key])
        return fallback

    return {
        "p95LatencyMs": round(metric_value(duration, "p(95)"), 2),
        "avgLatencyMs": round(metric_value(duration, "avg"), 2),
        "errorRate": round(metric_value(failed, "rate", metric_value(failed, "value")), 4),
        "requestCount": int(metric_value(requests, "count")),
        "requestRatePerSecond": round(metric_value(requests, "rate"), 2),
    }


def list_job_pods(config: dict, job_name: str) -> list[dict]:
    namespace = config["CLUSTER_NAMESPACE"]
    payload = load_kubernetes_json(
        f"/api/v1/namespaces/{namespace}/pods?labelSelector=job-name%3D{quote(job_name)}"
    )
    return payload.get("items", [])


def get_job_summary(config: dict, job_name: str) -> dict | None:
    pods = list_job_pods(config, job_name)
    if not pods:
        return None

    pod_name = pods[0].get("metadata", {}).get("name")
    if not pod_name:
        return None

    try:
        logs = load_kubernetes_text(
            f"/api/v1/namespaces/{config['CLUSTER_NAMESPACE']}/pods/{quote(pod_name)}/log"
        )
    except (HTTPError, URLError):
        return None

    return parse_summary_from_logs(logs)


def normalize_job(config: dict, item: dict) -> dict:
    metadata = item.get("metadata", {})
    labels = metadata.get("labels", {})
    lane = labels.get(JOB_LABEL_KEY, "bronze-baseline")
    lane_config = SCALE_LANES.get(lane, SCALE_LANES["bronze-baseline"])
    normalized = {
        "name": metadata.get("name"),
        "lane": lane,
        "label": lane_config["label"],
        "status": parse_run_status(item),
        "concurrency": lane_config["concurrency"],
        "durationSeconds": lane_config["durationSeconds"],
        "replicas": lane_config["replicas"],
        "createdAt": metadata.get("creationTimestamp"),
    }

    if normalized["status"] in {"completed", "failed"}:
        summary = get_job_summary(config, normalized["name"])
        if summary is not None:
            normalized["summary"] = summary

    return normalized


def list_scale_runs(config: dict) -> list[dict]:
    if not scale_lab_ready():
        return []

    payload = load_kubernetes_json(
        f"/apis/batch/v1/namespaces/{config['CLUSTER_NAMESPACE']}/jobs"
    )
    jobs = []
    for item in payload.get("items", []):
        labels = item.get("metadata", {}).get("labels", {})
        if labels.get(JOB_MANAGER_LABEL) != JOB_MANAGER_VALUE:
            continue
        jobs.append(normalize_job(config, item))

    return sorted(jobs, key=lambda job: str(job.get("createdAt") or ""), reverse=True)


def build_scale_lab_payload(config: dict) -> dict:
    lanes = [
        {
            "id": lane,
            "label": lane_config["label"],
            "description": lane_config["description"],
            "concurrency": lane_config["concurrency"],
            "durationSeconds": lane_config["durationSeconds"],
            "replicas": lane_config["replicas"],
        }
        for lane, lane_config in SCALE_LANES.items()
    ]

    if not scale_lab_ready():
        return {
            "enabled": False,
            "mode": "local",
            "lanes": lanes,
            "workloadScale": None,
            "runs": [],
        }

    return {
        "enabled": True,
        "mode": "cluster",
        "lanes": lanes,
        "workloadScale": get_workload_scale(config),
        "runs": list_scale_runs(config),
    }


def create_scale_run(config: dict, payload: object) -> dict:
    if not scale_lab_ready():
        raise ExperimentRequestError(
            "Scale lab runs are only available in the live cluster.",
            code="scale_lab_unavailable",
            status_code=409,
        )

    if not isinstance(payload, dict):
        raise ExperimentRequestError("Provide a valid scale lab request.")

    lane = validate_lane(payload.get("lane"))
    lane_config = SCALE_LANES[lane]

    active_runs = [
        run
        for run in list_scale_runs(config)
        if run.get("status") in {"running", "pending"}
    ]
    if active_runs:
        raise ExperimentRequestError(
            "Wait for the current scale run to finish before starting another one.",
            code="scale_lab_busy",
            status_code=409,
        )

    scale_workload(config, lane_config["replicas"])
    scale = wait_for_replicas(config, lane_config["replicas"])
    manifest = build_job_manifest(config, lane)

    try:
        load_json_with_method(
            f"/apis/batch/v1/namespaces/{config['CLUSTER_NAMESPACE']}/jobs",
            "POST",
            manifest,
        )
    except HTTPError as error:
        raise ExperimentRequestError(
            "The cluster could not start that scale run.",
            code="scale_lab_failed",
            status_code=502,
        ) from error
    except URLError as error:
        raise ExperimentRequestError(
            "The cluster could not start that scale run.",
            code="scale_lab_failed",
            status_code=502,
        ) from error

    return {
        "name": manifest["metadata"]["name"],
        "lane": lane,
        "label": lane_config["label"],
        "status": "running",
        "concurrency": lane_config["concurrency"],
        "durationSeconds": lane_config["durationSeconds"],
        "replicas": scale["readyReplicas"],
    }
