import pytest

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture()
def app():
    app = create_app('testing')

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
    user = User(
        username='tester',
        email='tester@example.com',
        role='admin',
    )
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
