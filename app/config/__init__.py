from .development import DevelopmentConfig
from .default import Config

# Map of configuration names to classes
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "default": Config
}