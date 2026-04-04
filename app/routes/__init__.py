def register_routes(app):
    from app.routes.events import events_bp
    from app.routes.links import links_bp
    from app.routes.users import users_bp
    from app.routes.urls import urls_bp

    app.register_blueprint(events_bp)
    app.register_blueprint(links_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(urls_bp)
