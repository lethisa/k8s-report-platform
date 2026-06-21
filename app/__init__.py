import os
from datetime import datetime

from flask import Flask

from app.auth.routes import auth_bp
from app.cluster import cluster_bp, routes  # noqa: F401
from app.config import CONFIG_MAP
from app.dashboard.routes import dashboard_bp
from app.extensions import db, login_manager, migrate
from app.inventory import inventory_bp


def create_app():

    # Create Flask application instance
    app = Flask(__name__)

    # Context processor to inject global variables into templates
    @app.context_processor
    def inject_globals():

        return {
            'app_version': app.config['APP_VERSION'],
            'current_year': datetime.now().year,
        }

    # Load configuration based on APP_ENV environment variable
    env = os.getenv('APP_ENV', 'development')

    if env not in CONFIG_MAP:
        raise ValueError(f'Invalid APP_ENV: {env}. Must be one of: {", ".join(CONFIG_MAP.keys())}')

    app.config.from_object(CONFIG_MAP[env])

    # Initialize database
    db.init_app(app)

    # Initialize login manager
    login_manager.init_app(app)

    # Initialize migration
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(cluster_bp)
    app.register_blueprint(inventory_bp)

    return app
