import os

from control_plane import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("APP_DEBUG", "true").strip().lower() == "true",
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=int(os.environ.get("CONTROL_PLANE_PORT", 8000)),
    )
