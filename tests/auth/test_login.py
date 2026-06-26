def test_login_page_can_be_opened(client):
    response = client.get('/auth/login')

    assert response.status_code == 200
    assert b'Username' in response.data
    assert b'Password' in response.data


def test_login_success_redirects_authenticated_user(client, test_user):
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

    protected_response = client.get('/clusters/')

    assert protected_response.status_code == 200
    assert b'Cluster Management' in protected_response.data


def test_login_with_wrong_password_does_not_authenticate(client, test_user):
    response = client.post(
        '/auth/login',
        data={
            'username': 'tester',
            'password': 'wrong-password',
            'remember': 'y',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    protected_response = client.get('/clusters/')

    assert protected_response.status_code in [302, 401]


def test_protected_page_requires_login(client):
    response = client.get('/clusters/')

    assert response.status_code in [302, 401]


def test_logout_authenticated_user(authenticated_client):
    response = authenticated_client.get(
        '/auth/logout',
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Username' in response.data
    assert b'Password' in response.data

    protected_response = authenticated_client.get('/clusters/')

    assert protected_response.status_code in [302, 401]


def test_logout_requires_login(client):
    response = client.get(
        '/auth/logout',
        follow_redirects=False,
    )

    assert response.status_code in [302, 401]


def test_login_with_unknown_username_does_not_authenticate(client):
    response = client.post(
        '/auth/login',
        data={
            'username': 'unknown-user',
            'password': 'password',
            'remember': 'y',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    protected_response = client.get('/clusters/')

    assert protected_response.status_code in [302, 401]
