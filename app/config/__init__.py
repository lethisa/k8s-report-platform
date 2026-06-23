from app.config.default import Config
from app.config.development import DevelopmentConfig

# Map of configuration names to classes
CONFIG_MAP = {'development': DevelopmentConfig, 'default': Config}
