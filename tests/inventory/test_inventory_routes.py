from __future__ import annotations

import pytest

INVENTORY_PROTECTED_ROUTES = [
    '/inventory/',
    '/inventory/nodes',
    '/inventory/namespaces',
    '/inventory/workloads',
    '/inventory/pods',
    '/inventory/services',
    '/inventory/ingresses',
    '/inventory/storage',
]


@pytest.mark.parametrize(
    'route',
    INVENTORY_PROTECTED_ROUTES,
)
def test_inventory_pages_require_login(client, route):
    response = client.get(
        route,
        follow_redirects=False,
    )

    assert response.status_code in [
        302,
        401,
    ]


@pytest.mark.parametrize(
    ('route', 'expected_text'),
    [
        (
            '/inventory/',
            b'Inventory Overview',
        ),
        (
            '/inventory/nodes',
            b'Node Inventory',
        ),
        (
            '/inventory/namespaces',
            b'Namespace Inventory',
        ),
        (
            '/inventory/workloads',
            b'Workload Inventory',
        ),
        (
            '/inventory/pods',
            b'Pod Inventory',
        ),
        (
            '/inventory/services',
            b'Service Inventory',
        ),
        (
            '/inventory/ingresses',
            b'Ingress Inventory',
        ),
        (
            '/inventory/storage',
            b'Storage Inventory',
        ),
    ],
)
def test_inventory_pages_can_be_opened_by_authenticated_user(
    authenticated_client,
    route,
    expected_text,
):
    response = authenticated_client.get(route)

    assert response.status_code == 200
    assert expected_text in response.data


@pytest.mark.parametrize(
    ('route', 'expected_text'),
    [
        (
            '/inventory/nodes',
            b'Per Page',
        ),
        (
            '/inventory/namespaces',
            b'Per Page',
        ),
        (
            '/inventory/workloads',
            b'Per Page',
        ),
        (
            '/inventory/pods',
            b'Per Page',
        ),
        (
            '/inventory/services',
            b'Per Page',
        ),
        (
            '/inventory/ingresses',
            b'Per Page',
        ),
        (
            '/inventory/storage',
            b'Per Page',
        ),
    ],
)
def test_inventory_paginated_pages_show_per_page_filter(
    authenticated_client,
    route,
    expected_text,
):
    response = authenticated_client.get(route)

    assert response.status_code == 200
    assert expected_text in response.data


@pytest.mark.parametrize(
    ('route', 'expected_text'),
    [
        (
            '/inventory/nodes',
            b'Page 1 / 1',
        ),
        (
            '/inventory/namespaces',
            b'Page 1 / 1',
        ),
        (
            '/inventory/workloads',
            b'Page 1 / 1',
        ),
        (
            '/inventory/pods',
            b'Page 1 / 1',
        ),
        (
            '/inventory/services',
            b'Page 1 / 1',
        ),
        (
            '/inventory/ingresses',
            b'Page 1 / 1',
        ),
        (
            '/inventory/storage',
            b'Page 1 / 1',
        ),
    ],
)
def test_inventory_paginated_pages_show_default_pagination_state(
    authenticated_client,
    route,
    expected_text,
):
    response = authenticated_client.get(route)

    assert response.status_code == 200
    assert expected_text in response.data
