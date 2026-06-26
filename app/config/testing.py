import os


class TestingConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'TEST_DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/kubereport_test',
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
