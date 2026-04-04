import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dotenv import load_dotenv
from flask import Flask, jsonify


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


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config.update(
        CLUSTER_NAME=os.environ.get("CLUSTER_NAME", "dev2prod-local"),
        CLUSTER_NAMESPACE=os.environ.get("CLUSTER_NAMESPACE", "dev2prod"),
        CLUSTER_PROVIDER=os.environ.get("CLUSTER_PROVIDER", "digitalocean"),
        WORKLOAD_API_URL=os.environ.get("WORKLOAD_API_URL", "http://127.0.0.1:5000"),
        CHAOS_MESH_ENABLED=read_flag("CHAOS_MESH_ENABLED"),
    )

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

    return app
