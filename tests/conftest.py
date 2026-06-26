from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from app.models import User


def _assert_test_database(database_uri: str) -> None:
    if 'test' not in database_uri.lower():
        raise RuntimeError('Refusing to run tests because database URI does not look like a test database.')


@pytest.fixture()
def app():
    app = create_app('testing')

    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    _assert_test_database(database_uri)

    with app.app_context():
        db.drop_all()
        db.create_all()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def test_user(app):
    user = User()

    user.username = 'tester'
    user.email = 'tester@example.com'
    user.role = 'admin'
    user.set_password('password')

    db.session.add(user)
    db.session.commit()

    return user


@pytest.fixture()
def authenticated_client(client, test_user):
    response = client.post(
        '/auth/login',
        data={
            'username': 'tester',
            'password': 'password',
            'remember': 'y',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    return client
