import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dotenv import load_dotenv
from flask import Flask, Response, jsonify

from control_plane.cluster import (
    get_resource_detail,
    get_resource_events,
    list_namespace_resources,
)


def read_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_workload_status(base_url: str, timeout: float = 1.0) -> dict:
    health_url = f"{base_url.rstrip('/')}/health"

    try:
        with urlopen(health_url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return {
            "status": "unreachable",
            "message": f"Health check returned {error.code}.",
        }
    except (URLError, TimeoutError, json.JSONDecodeError):
        return {
            "status": "unreachable",
            "message": "Health check is unavailable.",
        }

    if response.status != 200 or payload.get("status") != "ok":
        return {
            "status": "degraded",
            "message": "Health check returned an unexpected response.",
        }

    return {"status": "healthy"}


def serialize_sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config.update(
        CLUSTER_NAME=os.environ.get("CLUSTER_NAME", "dev2prod-local"),
        CLUSTER_NAMESPACE=os.environ.get("CLUSTER_NAMESPACE", "dev2prod"),
        CLUSTER_PROVIDER=os.environ.get("CLUSTER_PROVIDER", "digitalocean"),
        WORKLOAD_API_URL=os.environ.get("WORKLOAD_API_URL", "http://127.0.0.1:5000"),
        WORKLOAD_DEPLOYMENT_NAME=os.environ.get("WORKLOAD_DEPLOYMENT_NAME", "workload-api"),
        WORKLOAD_SERVICE_NAME=os.environ.get("WORKLOAD_SERVICE_NAME", "workload-api"),
        CONTROL_PLANE_DEPLOYMENT_NAME=os.environ.get(
            "CONTROL_PLANE_DEPLOYMENT_NAME",
            "control-plane",
        ),
        CONTROL_PLANE_ALLOWED_ORIGIN=os.environ.get("CONTROL_PLANE_ALLOWED_ORIGIN"),
        CHAOS_MESH_ENABLED=read_flag("CHAOS_MESH_ENABLED"),
    )

    @app.after_request
    def add_cors_headers(response):
        allowed_origin = app.config["CONTROL_PLANE_ALLOWED_ORIGIN"]
        if allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/cluster/status")
    def cluster_status():
        workload = get_workload_status(app.config["WORKLOAD_API_URL"])
        chaos_mesh_status = "ready" if app.config["CHAOS_MESH_ENABLED"] else "unavailable"
        mode = "cluster" if os.environ.get("KUBERNETES_SERVICE_HOST") else "local"

        return jsonify(
            data={
                "clusterName": app.config["CLUSTER_NAME"],
                "namespace": app.config["CLUSTER_NAMESPACE"],
                "provider": app.config["CLUSTER_PROVIDER"],
                "mode": mode,
                "scopeLocked": True,
                "controlPlane": {"status": "healthy"},
                "workload": workload,
                "chaosMesh": {"status": chaos_mesh_status},
            }
        )

    @app.get("/api/resources")
    def resources():
        return jsonify(data=list_namespace_resources(app.config))

    @app.get("/api/resources/<kind>/<name>")
    def resource_detail(kind: str, name: str):
        resource = get_resource_detail(app.config, kind, name)
        if resource is None:
            return jsonify(error={"code": "not_found", "message": "We could not find that resource."}), 404
        return jsonify(data=resource)

    @app.get("/api/resources/<kind>/<name>/events")
    def resource_events(kind: str, name: str):
        return jsonify(data=get_resource_events(app.config, kind, name))

    @app.get("/api/stream")
    def stream():
        def generate():
            yield serialize_sse(
                "cluster_snapshot",
                {
                    "status": {
                        "clusterName": app.config["CLUSTER_NAME"],
                        "namespace": app.config["CLUSTER_NAMESPACE"],
                        "provider": app.config["CLUSTER_PROVIDER"],
                        "mode": "cluster"
                        if os.environ.get("KUBERNETES_SERVICE_HOST")
                        else "local",
                        "scopeLocked": True,
                        "controlPlane": {"status": "healthy"},
                        "workload": get_workload_status(app.config["WORKLOAD_API_URL"]),
                        "chaosMesh": {
                            "status": "ready"
                            if app.config["CHAOS_MESH_ENABLED"]
                            else "unavailable"
                        },
                    },
                    "resources": list_namespace_resources(app.config),
                },
            )

        return Response(generate(), mimetype="text/event-stream")

    return app
