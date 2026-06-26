import os
from pathlib import Path

from dotenv import load_dotenv

from app.config.default import Config

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / '.env'

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'TEST_DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/kubereport_test',
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.getenv(
        'TEST_SECRET_KEY',
        'test-secret-key',
    )
