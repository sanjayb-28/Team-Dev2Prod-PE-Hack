from dotenv import load_dotenv
from flask import Flask, jsonify

from app.cache import init_cache
from app.database import create_tables, init_db
from app.errors import register_error_handlers
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)

    init_db(app)
    init_cache(app)

    from app import models  # noqa: F401 - registers models with Peewee
    create_tables()

    register_routes(app)
    register_error_handlers(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    return app
