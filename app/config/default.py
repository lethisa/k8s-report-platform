import os


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True

    APP_NAME = 'KubeReport'

    APP_VERSION = '1.0.0'
