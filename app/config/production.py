from app.config.default import Config


class ProductionConfig(Config):
    # Disable debug mode for production
    DEBUG = False
