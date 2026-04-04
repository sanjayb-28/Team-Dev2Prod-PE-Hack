import json
import os
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
SERVICE_ACCOUNT_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
RESOURCE_GROUPS = {
    "deployment": "deployments",
    "replicaset": "replicaSets",
    "pod": "pods",
    "service": "services",
    "experiment": "experiments",
}


def is_cluster_mode() -> bool:
    return bool(os.environ.get("KUBERNETES_SERVICE_HOST"))


def read_service_account_token() -> str:
    with open(SERVICE_ACCOUNT_TOKEN_PATH, encoding="utf-8") as handle:
        return handle.read().strip()


def build_api_base() -> str:
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS", "443")
    return f"https://{host}:{port}"


def load_kubernetes_json(path: str, timeout: float = 2.0) -> dict:
    request = Request(f"{build_api_base()}{path}")
    request.add_header("Authorization", f"Bearer {read_service_account_token()}")
    context = ssl.create_default_context(cafile=SERVICE_ACCOUNT_CA_PATH)

    with urlopen(request, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def load_kubernetes_text(path: str, timeout: float = 2.0) -> str:
    request = Request(f"{build_api_base()}{path}")
    request.add_header("Authorization", f"Bearer {read_service_account_token()}")
    context = ssl.create_default_context(cafile=SERVICE_ACCOUNT_CA_PATH)

    with urlopen(request, timeout=timeout, context=context) as response:
        return response.read().decode("utf-8")


def normalize_deployment(item: dict) -> dict:
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})
    desired = spec.get("replicas", 1)
    ready = status.get("readyReplicas", 0)

    return {
        "kind": "deployment",
        "name": metadata.get("name"),
        "status": "healthy" if desired == ready else "degraded",
        "desiredReplicas": desired,
        "readyReplicas": ready,
        "availableReplicas": status.get("availableReplicas", 0),
        "updatedAt": metadata.get("creationTimestamp"),
    }


def normalize_replica_set(item: dict) -> dict:
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})
    desired = spec.get("replicas", 0)
    ready = status.get("readyReplicas", 0)

    return {
        "kind": "replicaSet",
        "name": metadata.get("name"),
        "status": "healthy" if desired == ready else "degraded",
        "desiredReplicas": desired,
        "readyReplicas": ready,
        "updatedAt": metadata.get("creationTimestamp"),
    }


def normalize_pod(item: dict) -> dict:
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    container_statuses = status.get("containerStatuses", [])
    restarts = sum(container.get("restartCount", 0) for container in container_statuses)
    ready = any(
        condition.get("type") == "Ready" and condition.get("status") == "True"
        for condition in status.get("conditions", [])
    )

    return {
        "kind": "pod",
        "name": metadata.get("name"),
        "status": status.get("phase", "Unknown").lower(),
        "ready": ready,
        "restartCount": restarts,
        "updatedAt": metadata.get("creationTimestamp"),
    }


def normalize_service(item: dict) -> dict:
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})

    return {
        "kind": "service",
        "name": metadata.get("name"),
        "status": "active",
        "type": spec.get("type", "ClusterIP"),
        "clusterIp": spec.get("clusterIP"),
        "ports": [port.get("port") for port in spec.get("ports", [])],
        "updatedAt": metadata.get("creationTimestamp"),
    }


def normalize_event(item: dict) -> dict:
    metadata = item.get("metadata", {})
    involved = item.get("involvedObject", {})

    return {
        "name": metadata.get("name"),
        "type": item.get("type", "Normal"),
        "reason": item.get("reason"),
        "message": item.get("message"),
        "resourceKind": involved.get("kind"),
        "resourceName": involved.get("name"),
        "timestamp": (
            item.get("eventTime")
            or item.get("lastTimestamp")
            or metadata.get("creationTimestamp")
        ),
    }


def normalize_experiment(kind: str, item: dict) -> dict:
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    labels = metadata.get("labels", {})
    experiment_status = status.get("experiment", {})
    container_records = experiment_status.get("containerRecords", [])
    spec = item.get("spec", {})
    phases = {
        str(record.get("phase", "")).strip().lower()
        for record in container_records
        if record.get("phase")
    }
    conditions = {
        str(condition.get("type", "")): str(condition.get("status", "False")).lower() == "true"
        for condition in status.get("conditions", [])
    }

    if conditions.get("Paused"):
        normalized_status = "paused"
    elif conditions.get("AllRecovered"):
        normalized_status = "recovered"
    elif "injected" in phases or experiment_status.get("desiredPhase") == "Run":
        normalized_status = "running"
    elif conditions.get("Selected") or conditions.get("AllInjected"):
        normalized_status = "pending"
    elif metadata.get("creationTimestamp"):
        normalized_status = "pending"
    else:
        normalized_status = "unknown"

    normalized: dict = {
        "kind": "experiment",
        "type": labels.get("dev2prod.io/experiment-type", kind),
        "name": metadata.get("name"),
        "status": normalized_status,
        "target": labels.get("dev2prod.io/target-name")
        or labels.get("app.kubernetes.io/name"),
        "updatedAt": metadata.get("creationTimestamp"),
    }

    duration = spec.get("duration")
    if isinstance(duration, str) and duration.endswith("s") and duration[:-1].isdigit():
        normalized["durationSeconds"] = int(duration[:-1])

    if normalized["type"] == "network-latency":
        latency = spec.get("delay", {}).get("latency")
        if isinstance(latency, str) and latency.endswith("ms") and latency[:-2].isdigit():
            normalized["latencyMs"] = int(latency[:-2])

    if normalized["type"] == "cpu-stress":
        load = spec.get("stressors", {}).get("cpu", {}).get("load")
        if isinstance(load, int):
            normalized["cpuLoad"] = load

    return normalized


def settle_experiment_status(experiment: dict, active_pod_names: set[str]) -> dict:
    if experiment.get("type") != "pod-kill":
        return experiment

    target = str(experiment.get("target") or "").strip()
    if not target:
        return experiment

    if target in active_pod_names:
        return experiment

    next_experiment = dict(experiment)
    next_experiment["status"] = "recovered"
    return next_experiment


def list_local_resources(config: dict) -> dict:
    workload_name = config.get("WORKLOAD_DEPLOYMENT_NAME", "workload-api")
    control_plane_name = config.get("CONTROL_PLANE_DEPLOYMENT_NAME", "control-plane")
    service_name = config.get("WORKLOAD_SERVICE_NAME", "workload-api")

    return {
        "mode": "local",
        "namespace": config["CLUSTER_NAMESPACE"],
        "resources": {
            "deployments": [
                {
                    "kind": "deployment",
                    "name": workload_name,
                    "status": "unknown",
                    "desiredReplicas": 1,
                    "readyReplicas": 0,
                    "availableReplicas": 0,
                    "updatedAt": None,
                },
                {
                    "kind": "deployment",
                    "name": control_plane_name,
                    "status": "healthy",
                    "desiredReplicas": 1,
                    "readyReplicas": 1,
                    "availableReplicas": 1,
                    "updatedAt": None,
                },
            ],
            "replicaSets": [],
            "pods": [],
            "services": [
                {
                    "kind": "service",
                    "name": service_name,
                    "status": "active",
                    "type": "ClusterIP",
                    "clusterIp": None,
                    "ports": [5000],
                    "updatedAt": None,
                }
            ],
            "experiments": [],
        },
        "events": [],
    }


def load_cluster_resources(namespace: str) -> dict:
    deployments = load_kubernetes_json(f"/apis/apps/v1/namespaces/{namespace}/deployments")
    replica_sets = load_kubernetes_json(f"/apis/apps/v1/namespaces/{namespace}/replicasets")
    pods = load_kubernetes_json(f"/api/v1/namespaces/{namespace}/pods")
    services = load_kubernetes_json(f"/api/v1/namespaces/{namespace}/services")
    events = load_kubernetes_json(f"/api/v1/namespaces/{namespace}/events")

    experiments = []
    active_pod_names = {
        item.get("metadata", {}).get("name")
        for item in pods.get("items", [])
        if item.get("metadata", {}).get("name")
    }
    for kind in ("podchaos", "networkchaos", "stresschaos"):
        try:
            response = load_kubernetes_json(
                f"/apis/chaos-mesh.org/v1alpha1/namespaces/{namespace}/{kind}"
            )
        except (HTTPError, URLError):
            continue

        experiments.extend(
            settle_experiment_status(
                normalize_experiment(kind, item),
                active_pod_names,
            )
            for item in response.get("items", [])
        )

    return {
        "mode": "cluster",
        "namespace": namespace,
        "resources": {
            "deployments": [
                normalize_deployment(item) for item in deployments.get("items", [])
            ],
            "replicaSets": [
                normalize_replica_set(item) for item in replica_sets.get("items", [])
            ],
            "pods": [normalize_pod(item) for item in pods.get("items", [])],
            "services": [normalize_service(item) for item in services.get("items", [])],
            "experiments": experiments,
        },
        "events": [normalize_event(item) for item in events.get("items", [])],
    }


def list_namespace_resources(config: dict) -> dict:
    if not is_cluster_mode():
        return list_local_resources(config)

    namespace = config["CLUSTER_NAMESPACE"]
    return load_cluster_resources(namespace)


def normalize_kind(kind: str) -> str:
    return kind.replace("-", "").replace("_", "").lower()


def get_resource_detail(config: dict, kind: str, name: str) -> dict | None:
    payload = list_namespace_resources(config)
    resource_group = RESOURCE_GROUPS.get(normalize_kind(kind))
    if resource_group is None:
        return None

    resources = payload["resources"][resource_group]
    return next((resource for resource in resources if resource.get("name") == name), None)


def get_resource_events(config: dict, kind: str, name: str) -> list[dict]:
    payload = list_namespace_resources(config)
    normalized_kind = normalize_kind(kind)
    experiment_kinds = {"podchaos", "networkchaos", "stresschaos"}

    return [
        event
        for event in payload["events"]
        if event.get("resourceName") == name
        and (
            normalize_kind(event.get("resourceKind", "")) == normalized_kind
            or (
                normalized_kind == "experiment"
                and normalize_kind(event.get("resourceKind", "")) in experiment_kinds
            )
        )
    ]


def get_resource_logs(config: dict, kind: str, name: str) -> dict | None:
    resource = get_resource_detail(config, kind, name)
    if resource is None:
        return None

    normalized_kind = normalize_kind(kind)

    if not is_cluster_mode():
        return {
            "kind": resource.get("kind"),
            "name": name,
            "entries": [],
            "note": (
                "Local mode keeps the stack reachable, but raw pod logs appear after the "
                "cluster log endpoint is connected."
            ),
        }

    if normalized_kind != "pod":
        return {
            "kind": resource.get("kind"),
            "name": name,
            "entries": [],
            "note": "Select a pod to inspect raw container logs.",
        }

    namespace = config["CLUSTER_NAMESPACE"]

    try:
        log_text = load_kubernetes_text(
            f"/api/v1/namespaces/{namespace}/pods/{quote(name)}/log?tailLines=80"
        )
    except (HTTPError, URLError):
        return {
            "kind": resource.get("kind"),
            "name": name,
            "entries": [],
            "note": "Logs are unavailable for this pod right now.",
        }

    entries = [{"line": line} for line in log_text.splitlines()[-80:] if line.strip()]

    return {
        "kind": resource.get("kind"),
        "name": name,
        "entries": entries,
        "note": (
            "Showing the latest lines from this pod."
            if entries
            else "The pod log stream is empty right now."
        ),
    }
