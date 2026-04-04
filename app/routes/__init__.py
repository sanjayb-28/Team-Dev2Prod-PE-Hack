def register_routes(app):
    from app.routes.links import links_bp
    from app.routes.users import users_bp

    app.register_blueprint(links_bp)
    app.register_blueprint(users_bp)
