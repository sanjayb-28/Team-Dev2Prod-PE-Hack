import json
import re
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from control_plane.cluster import (
    build_api_base,
    is_cluster_mode,
    list_cluster_experiments,
    load_kubernetes_json,
    normalize_experiment,
    read_service_account_token,
    SERVICE_ACCOUNT_CA_PATH,
)


EXPERIMENT_RESOURCE_TYPES = {
    "pod-kill": {"kind": "PodChaos", "resource": "podchaos"},
    "network-latency": {"kind": "NetworkChaos", "resource": "networkchaos"},
    "cpu-stress": {"kind": "StressChaos", "resource": "stresschaos"},
}
ALLOWED_TARGET_KINDS = {"deployment", "service", "pod"}


class ExperimentRequestError(Exception):
    def __init__(self, message: str, code: str = "validation_failed", status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def chaos_mesh_ready(config: dict) -> bool:
    return bool(config.get("CHAOS_MESH_ENABLED")) and is_cluster_mode()


def ensure_chaos_mesh_ready(config: dict):
    if chaos_mesh_ready(config):
        return

    raise ExperimentRequestError(
        "Fault tooling is not ready in this cluster yet.",
        code="chaos_mesh_unavailable",
        status_code=409,
    )


def load_json_with_method(path: str, method: str, payload: dict | None = None, timeout: float = 3.0) -> dict:
    request = Request(f"{build_api_base()}{path}", method=method.upper())
    request.add_header("Authorization", f"Bearer {read_service_account_token()}")
    request.add_header("Accept", "application/json")

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request.add_header("Content-Type", "application/json")

    import ssl

    context = ssl.create_default_context(cafile=SERVICE_ACCOUNT_CA_PATH)

    with urlopen(request, timeout=timeout, context=context, data=data) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def normalize_target_kind(value: object) -> str:
    return str(value or "").strip().replace("-", "").replace("_", "").lower()


def validate_experiment_type(value: object) -> str:
    experiment_type = str(value or "").strip()
    if experiment_type not in EXPERIMENT_RESOURCE_TYPES:
        raise ExperimentRequestError("Choose one of the supported fault types.")
    return experiment_type


def validate_duration_seconds(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExperimentRequestError("Choose a valid duration.")
    if value < 15 or value > 300:
        raise ExperimentRequestError("Choose a duration between 15 and 300 seconds.")
    return value


def validate_target(config: dict, value: object) -> dict:
    if not isinstance(value, dict):
        raise ExperimentRequestError("Choose a resource in the locked scope.")

    kind = normalize_target_kind(value.get("kind"))
    name = str(value.get("name") or "").strip()
    if kind not in ALLOWED_TARGET_KINDS or not name:
        raise ExperimentRequestError("Choose a resource in the locked scope.")

    workload_name = config.get("WORKLOAD_DEPLOYMENT_NAME", "workload-api")
    workload_service = config.get("WORKLOAD_SERVICE_NAME", "workload-api")

    if kind == "deployment" and name == workload_name:
        return {"kind": kind, "name": name}
    if kind == "service" and name == workload_service:
        return {"kind": kind, "name": name}
    if kind == "pod" and name.startswith(f"{workload_name}-"):
        return {"kind": kind, "name": name}

    raise ExperimentRequestError("Choose a resource in the locked scope.")


def validate_parameters(experiment_type: str, value: object) -> dict:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ExperimentRequestError("Provide valid settings for this fault.")

    if experiment_type == "network-latency":
        latency_ms = value.get("latencyMs", 120)
        if isinstance(latency_ms, bool) or not isinstance(latency_ms, int):
            raise ExperimentRequestError("Choose a valid latency value.")
        if latency_ms < 20 or latency_ms > 2000:
            raise ExperimentRequestError("Choose a latency between 20 and 2000 milliseconds.")
        return {"latencyMs": latency_ms}

    if experiment_type == "cpu-stress":
        cpu_load = value.get("cpuLoad", 80)
        if isinstance(cpu_load, bool) or not isinstance(cpu_load, int):
            raise ExperimentRequestError("Choose a valid CPU load.")
        if cpu_load < 20 or cpu_load > 100:
            raise ExperimentRequestError("Choose a CPU load between 20 and 100 percent.")
        return {"cpuLoad": cpu_load}

    return {}


def build_selector(namespace: str, target: dict, workload_name: str) -> dict:
    if target["kind"] == "pod":
        return {"pods": {namespace: [target["name"]]}}

    return {
        "namespaces": [namespace],
        "labelSelectors": {"app.kubernetes.io/name": workload_name},
    }


def build_metadata_name(experiment_type: str) -> str:
    suffix = secrets.token_hex(3)
    slug = re.sub(r"[^a-z0-9-]+", "-", experiment_type.lower()).strip("-")
    return f"{slug}-{suffix}"


def build_experiment_manifest(config: dict, experiment_type: str, target: dict, duration_seconds: int, parameters: dict) -> dict:
    namespace = config["CLUSTER_NAMESPACE"]
    workload_name = config.get("WORKLOAD_DEPLOYMENT_NAME", "workload-api")
    selector = build_selector(namespace, target, workload_name)
    metadata_name = build_metadata_name(experiment_type)

    metadata = {
        "name": metadata_name,
        "namespace": namespace,
        "labels": {
            "app.kubernetes.io/name": workload_name,
            "app.kubernetes.io/managed-by": "dev2prod-control-plane",
            "dev2prod.io/experiment-type": experiment_type,
            "dev2prod.io/target-kind": target["kind"],
            "dev2prod.io/target-name": target["name"],
        },
    }

    if experiment_type == "pod-kill":
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "PodChaos",
            "metadata": metadata,
            "spec": {
                "action": "pod-kill",
                "mode": "one",
                "selector": selector,
            },
        }

    if experiment_type == "network-latency":
        return {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "NetworkChaos",
            "metadata": metadata,
            "spec": {
                "action": "delay",
                "mode": "all",
                "selector": selector,
                "delay": {
                    "latency": f"{parameters['latencyMs']}ms",
                    "correlation": "100",
                    "jitter": "0ms",
                },
                "duration": f"{duration_seconds}s",
            },
        }

    return {
        "apiVersion": "chaos-mesh.org/v1alpha1",
        "kind": "StressChaos",
        "metadata": metadata,
        "spec": {
            "mode": "one",
            "selector": selector,
            "stressors": {
                "cpu": {
                    "workers": 1,
                    "load": parameters["cpuLoad"],
                }
            },
            "duration": f"{duration_seconds}s",
        },
    }


def list_experiments(config: dict) -> list[dict]:
    if not chaos_mesh_ready(config):
        return []

    namespace = config["CLUSTER_NAMESPACE"]
    return sorted(
        list_cluster_experiments(namespace, set()),
        key=lambda item: item.get("updatedAt") or "",
        reverse=True,
    )


def read_experiment(namespace: str, experiment_type: str, name: str) -> dict | None:
    resource = EXPERIMENT_RESOURCE_TYPES[experiment_type]["resource"]
    try:
        return load_kubernetes_json(
            f"/apis/chaos-mesh.org/v1alpha1/namespaces/{namespace}/{resource}/{quote(name)}"
        )
    except (HTTPError, URLError):
        return None


def create_experiment(config: dict, payload: object) -> dict:
    ensure_chaos_mesh_ready(config)
    if not isinstance(payload, dict):
        raise ExperimentRequestError("Provide a valid fault request.")

    experiment_type = validate_experiment_type(payload.get("type"))
    target = validate_target(config, payload.get("target"))
    duration_seconds = validate_duration_seconds(payload.get("durationSeconds"))
    parameters = validate_parameters(experiment_type, payload.get("parameters"))
    manifest = build_experiment_manifest(
        config,
        experiment_type,
        target,
        duration_seconds,
        parameters,
    )
    resource = EXPERIMENT_RESOURCE_TYPES[experiment_type]["resource"]

    try:
        created = load_json_with_method(
            f"/apis/chaos-mesh.org/v1alpha1/namespaces/{config['CLUSTER_NAMESPACE']}/{resource}",
            "POST",
            manifest,
        )
    except HTTPError as error:
        if error.code == 409:
            raise ExperimentRequestError("That fault run already exists.", code="conflict", status_code=409) from error
        raise ExperimentRequestError(
            "The cluster could not start that fault run.",
            code="experiment_failed",
            status_code=502,
        ) from error
    except URLError as error:
        raise ExperimentRequestError(
            "The cluster could not start that fault run.",
            code="experiment_failed",
            status_code=502,
        ) from error

    normalized = normalize_experiment(resource, created)
    normalized["type"] = experiment_type
    normalized["target"] = target["name"]

    if normalized.get("status") in {"unknown", "pending"}:
        for _ in range(3):
            time.sleep(0.25)
            refreshed = read_experiment(
                config["CLUSTER_NAMESPACE"],
                experiment_type,
                normalized["name"],
            )
            if not refreshed:
                continue
            normalized = normalize_experiment(resource, refreshed)
            normalized["type"] = experiment_type
            normalized["target"] = target["name"]
            if normalized.get("status") not in {"unknown", "pending"}:
                break

    return normalized


def cancel_experiment(config: dict, name: str) -> dict:
    ensure_chaos_mesh_ready(config)
    experiment_name = str(name or "").strip()
    if not experiment_name:
        raise ExperimentRequestError("Choose a valid fault run.")

    namespace = config["CLUSTER_NAMESPACE"]
    last_error: Exception | None = None

    for experiment_type, resource in EXPERIMENT_RESOURCE_TYPES.items():
        path = (
            f"/apis/chaos-mesh.org/v1alpha1/namespaces/{namespace}/"
            f"{resource['resource']}/{quote(experiment_name)}"
        )
        try:
            load_json_with_method(path, "DELETE")
            return {
                "name": experiment_name,
                "status": "cancelled",
                "type": experiment_type,
            }
        except HTTPError as error:
            if error.code == 404:
                last_error = error
                continue
            raise ExperimentRequestError(
                "The cluster could not stop that fault run.",
                code="experiment_failed",
                status_code=502,
            ) from error
        except URLError as error:
            raise ExperimentRequestError(
                "The cluster could not stop that fault run.",
                code="experiment_failed",
                status_code=502,
            ) from error

    if last_error is not None:
        raise ExperimentRequestError(
            "We could not find that fault run.",
            code="not_found",
            status_code=404,
        ) from last_error

    raise ExperimentRequestError("We could not find that fault run.", code="not_found", status_code=404)
