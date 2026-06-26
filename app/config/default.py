import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / '.env'

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True

    APP_NAME = 'KubeReport'

    APP_VERSION = '1.0.0'
