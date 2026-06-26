# KubeReport Testing Guide

## Purpose

This document is the dedicated testing guide for KubeReport.

It will be updated continuously as the test suite grows across modules such as Authentication, Cluster Management, Inventory, Prometheus, Analytics, Reports, and future operational features.

The goal of this document is to keep the testing strategy clear, consistent, and safe throughout the project lifecycle.

---

## Testing Principles

KubeReport tests must follow these principles:

1. Tests must be isolated from the development and production databases.
2. Tests must use the `testing` configuration explicitly.
3. Tests must be repeatable and safe to run multiple times.
4. Tests must not depend on live Kubernetes clusters unless explicitly marked as integration tests.
5. Unit tests should focus on service logic.
6. Route tests should validate HTTP behavior, authentication, redirects, rendered content, and HTMX partial responses.
7. External systems such as Kubernetes API and Prometheus should be mocked in unit and route tests.
8. Integration tests will be added separately when the core modules are stable.
9. Route files should stay thin. Database queries and business logic belong in service files.
10. Inventory behavior must be tested separately from Cluster Management behavior.
11. Tests should avoid brittle HTML whitespace assertions.
12. Test mocks must follow the same public interface used by production code.
13. Test-only fake objects may use `typing.cast()` to satisfy strict type checking while keeping production code strongly typed.

---

## Configuration Strategy

KubeReport uses `APP_ENV` to select the active application configuration.

Configuration mapping:

```python
CONFIG_MAP = {
    "default": Config,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
```

Expected behavior:

| Runtime Mode | Config Class | Database Variable |
| --- | --- | --- |
| Development | `DevelopmentConfig` | `DATABASE_URL` |
| Production | `ProductionConfig` | `DATABASE_URL` |
| Testing | `TestingConfig` | `TEST_DATABASE_URL` |

Testing must always use:

```python
create_app("testing")
```

This ensures the test suite does not depend on the value of `APP_ENV` from the local `.env` file.

---

## Environment Variable Loading

The root `.env` file must be loaded from the base configuration, not only from the testing configuration.

Current convention:

```text
app/config/default.py
```

loads:

```text
<project-root>/.env
```

This allows both normal app execution and pytest execution to read the required environment variables.

Recommended `default.py` pattern:

```python
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True

    APP_NAME = "KubeReport"

    APP_VERSION = "1.0.0"
```

Reason:

- `python run.py` uses `create_app()` and the development configuration.
- Development configuration reads `DATABASE_URL`.
- If `.env` is not loaded before configuration values are evaluated, `SQLALCHEMY_DATABASE_URI` becomes `None`.
- Flask-SQLAlchemy then raises: `Either 'SQLALCHEMY_DATABASE_URI' or 'SQLALCHEMY_BINDS' must be set.`

---

## Environment Variables

The local `.env` file may remain configured for development.

Example:

```env
APP_ENV=development

SECRET_KEY=dev-secret-key
TEST_SECRET_KEY=test-secret-key

DATABASE_URL=postgresql://kubereport:kubereport@localhost:5432/kubereport_dev
TEST_DATABASE_URL=postgresql://kubereport:kubereport@localhost:5432/kubereport_test
```

Expected behavior:

```text
python run.py
→ create_app()
→ APP_ENV=development
→ DATABASE_URL
→ kubereport_dev
```

```text
pytest
→ create_app("testing")
→ TEST_DATABASE_URL
→ kubereport_test
```

The test suite must never run against the development or production database.

---

## Testing Configuration

File:

```text
app/config/testing.py
```

Recommended implementation:

```python
import os

from app.config.default import Config


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/kubereport_test",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.getenv(
        "TEST_SECRET_KEY",
        "test-secret-key",
    )
```

Notes:

- `TestingConfig` inherits from `Config` to keep global application settings available.
- `.env` is loaded by `Config` in `default.py`.
- `TestingConfig` should not duplicate `.env` loading logic.
- `WTF_CSRF_ENABLED = False` simplifies form submission in tests.
- `override=False` keeps terminal environment variables higher priority than `.env`.

---

## Pytest Configuration

File:

```text
pytest.ini
```

Recommended implementation:

```ini
[pytest]
testpaths = tests
pythonpath = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra
```

Purpose:

- `testpaths = tests` limits test discovery to the `tests` directory.
- `pythonpath = .` allows imports from the root application package.
- `addopts = -ra` provides a useful test summary.

---

## Test Directory Structure

Current structure:

```text
tests/
├── conftest.py
├── auth/
│   └── test_login.py
├── cluster/
│   ├── test_cluster_service.py
│   └── test_cluster_routes.py
└── inventory/
    ├── test_inventory_routes.py
    ├── test_inventory_pagination.py
    ├── test_inventory_services.py
    ├── test_inventory_save_functions.py
    ├── test_inventory_sync.py
    └── test_inventory_sync_route.py
```

Planned structure:

```text
tests/
├── conftest.py
├── auth/
│   └── test_login.py
├── cluster/
│   ├── test_cluster_service.py
│   ├── test_cluster_routes.py
│   └── test_cluster_delete.py
├── inventory/
│   ├── test_inventory_routes.py
│   ├── test_inventory_pagination.py
│   ├── test_inventory_services.py
│   ├── test_inventory_save_functions.py
│   ├── test_inventory_sync.py
│   └── test_inventory_sync_route.py
├── prometheus/
│   ├── test_prometheus_client.py
│   ├── test_prometheus_service.py
│   └── test_prometheus_routes.py
├── analytics/
│   ├── test_utilization_service.py
│   ├── test_capacity_service.py
│   └── test_forecast_service.py
└── reports/
    ├── test_report_service.py
    └── test_report_routes.py
```

---

## Shared Fixtures

File:

```text
tests/conftest.py
```

Responsibilities:

- Create the Flask app using `create_app("testing")`.
- Create a test client.
- Create a test CLI runner.
- Create and clean the test database.
- Provide reusable test users.
- Provide an authenticated client fixture.
- Provide reusable kubeconfig test data.
- Provide a cluster factory for Cluster Management and Inventory tests.

The test application fixture must include a database safety guard.

Example:

```python
def _assert_test_database(database_uri: str) -> None:
    if "test" not in database_uri.lower():
        raise RuntimeError(
            "Refusing to run tests because database URI does not look like a test database."
        )
```

This guard prevents destructive operations such as `db.drop_all()` from running against a non-test database.

### Application Context in Service Tests

Service tests that access `db.session`, `Model.query`, or service functions that query models must activate the Flask application context.

Recommended file-level fixture:

```python
import pytest


@pytest.fixture(autouse=True)
def _use_app_context(app):
    pass
```

This keeps service tests clean without adding `app` to every test function signature.

---

## Database Lifecycle

For the current baseline test suite, the database lifecycle is:

```text
Before test execution:
→ db.drop_all()
→ db.create_all()

After test execution:
→ db.session.remove()
→ db.drop_all()
```

This approach is acceptable for the current stage because the application is still evolving quickly.

Future improvement:

- Use transaction rollback per test.
- Use Alembic migration-based setup for integration testing.
- Separate unit tests from database integration tests.
- Add CI database provisioning.

---

## Authentication Test Baseline

File:

```text
tests/auth/test_login.py
```

Authentication tests validate login, logout, and route protection behavior.

Current coverage:

| Test Case | Purpose | Status |
| --- | --- | --- |
| Login page can be opened | Validate `/auth/login` renders username and password fields | Done |
| Login with valid credentials | Validate successful authentication and access to protected cluster page | Done |
| Login with wrong password | Validate failed authentication for an existing user | Done |
| Login with unknown username | Validate failed authentication for a non-existing user | Done |
| Protected page requires login | Validate unauthenticated users cannot access `/clusters/` | Done |
| Logout authenticated user | Validate authenticated user can log out and loses protected access | Done |
| Logout without login | Validate logout route behavior for unauthenticated request | Done |

The login tests keep the `remember` field enabled:

```python
"remember": "y"
```

This keeps the `Remember Me` behavior covered in the baseline authentication test.

---

## Cluster Management Test Baseline

Files:

```text
tests/cluster/test_cluster_service.py
tests/cluster/test_cluster_routes.py
```

Cluster Management tests intentionally focus only on the cluster domain.

Current scope:

- Cluster creation from uploaded kubeconfig content.
- Basic cluster metadata.
- Cluster server parsing from kubeconfig.
- Cluster duplicate name validation.
- Cluster metadata update.
- Cluster list/add/edit/delete routes.
- Cluster test connection route with mocked Kubernetes connection.
- HTMX partial response integrity.

Out of scope for Cluster Management tests:

- Inventory sync.
- Namespace count.
- Node inventory.
- Workload inventory.
- Pod inventory.
- Service inventory.
- Ingress inventory.
- Storage inventory.
- Kubernetes version collected from inventory.

Those items are covered in the Inventory test suite.

Current coverage:

| Area | Test Case | Status |
| --- | --- | --- |
| Service | Parse valid kubeconfig and return cluster server | Done |
| Service | Reject invalid kubeconfig YAML | Done |
| Service | Reject kubeconfig without clusters | Done |
| Service | Reject kubeconfig without server | Done |
| Service | Create cluster from kubeconfig | Done |
| Service | Reject duplicate cluster name | Done |
| Service | Update cluster basic metadata | Done |
| Service | Reject duplicate name on update | Done |
| Service | Build cluster context without inventory data | Done |
| Route | Cluster list requires login | Done |
| Route | Authenticated user can open cluster list | Done |
| Route | Authenticated user can open add cluster page | Done |
| Route | Authenticated user can add cluster | Done |
| Route | Authenticated user can open edit cluster page | Done |
| Route | Authenticated user can update cluster | Done |
| Route | Authenticated user can delete cluster | Done |
| Route | Test connection route with mocked Kubernetes connection | Done |
| Route | HTMX partial keeps search and environment filter toolbar | Done |

### Cluster Service Boundary

Cluster service functions are responsible for database access and business rules.

Examples:

```python
get_cluster_by_id(cluster_id)
create_cluster(...)
update_cluster(...)
delete_cluster(...)
run_test_cluster(...)
build_cluster_context()
```

Route handlers should not directly query models using:

```python
Cluster.query.get(...)
Cluster.query.get_or_404(...)
db.get_or_404(...)
```

Preferred route pattern:

```python
def _get_cluster_or_404(cluster_id: str) -> Cluster:
    cluster = get_cluster_by_id(cluster_id)

    if cluster is None:
        abort(404)

    return cluster
```

This keeps the route responsible for HTTP behavior and the service responsible for data access.

---

## Inventory Test Baseline

Inventory tests validate the Inventory module separately from Cluster Management.

Inventory tests are grouped by responsibility:

```text
tests/inventory/test_inventory_routes.py
tests/inventory/test_inventory_pagination.py
tests/inventory/test_inventory_services.py
tests/inventory/test_inventory_save_functions.py
tests/inventory/test_inventory_sync.py
tests/inventory/test_inventory_sync_route.py
```

Current coverage:

| Area | Test Case | Status |
| --- | --- | --- |
| Route | Inventory pages require login | Done |
| Route | Authenticated user can open Inventory Overview | Done |
| Route | Authenticated user can open Nodes page | Done |
| Route | Authenticated user can open Namespaces page | Done |
| Route | Authenticated user can open Workloads page | Done |
| Route | Authenticated user can open Pods page | Done |
| Route | Authenticated user can open Services page | Done |
| Route | Authenticated user can open Ingresses page | Done |
| Route | Authenticated user can open Storage page | Done |
| Route | Paginated pages show Per Page filter | Done |
| Route | Paginated pages show default pagination state | Done |
| Pagination | Default `per_page=25` shows first page | Done |
| Pagination | `page=2` opens second page | Done |
| Pagination | Invalid `per_page` falls back to `25` | Done |
| Pagination | Page number greater than total pages falls back to last page | Done |
| Pagination | Page number less than one falls back to first page | Done |
| Service | `convert_ki_to_gib()` conversion behavior | Done |
| Service | `format_age()` empty, hour, and day behavior | Done |
| Service | `get_node_inventory()` summary and filters | Done |
| Service | `get_namespace_inventory()` summary and filters | Done |
| Service | `get_workload_inventory()` summary and filters | Done |
| Service | `get_pod_inventory()` summary and filters | Done |
| Service | `get_service_inventory()` summary and filters | Done |
| Service | `get_ingress_inventory()` summary and filters | Done |
| Service | `get_storage_inventory_view()` summary and filters | Done |
| Service | `get_inventory_overview()` total counts and health state | Done |
| Save Function | `save_cluster_info()` creates and replaces `ClusterInventory` | Done |
| Save Function | `save_nodes()` creates and replaces `NodeInventory` | Done |
| Save Function | `save_namespaces()` creates and replaces `NamespaceInventory` | Done |
| Save Function | `save_workloads()` creates `WorkloadInventory` | Done |
| Save Function | `save_pods()` creates `PodInventory` | Done |
| Save Function | `save_services()` creates `ServiceInventory` | Done |
| Save Function | `save_ingresses()` creates `IngressInventory` | Done |
| Save Function | `save_storage_inventory()` creates and replaces `StorageInventory` | Done |
| Sync | `sync_inventory()` creates Kubernetes client and API clients | Done |
| Sync | `sync_inventory()` calls all save functions | Done |
| Sync | `sync_inventory()` commits when successful | Done |
| Sync | `sync_inventory()` rolls back when a save function fails | Done |
| Sync | `sync_inventory()` passes cluster kubeconfig to Kubernetes client | Done |
| Sync Route | `POST /inventory/<cluster_id>/sync` requires login | Done |
| Sync Route | Authenticated sync route calls `sync_inventory()` | Done |
| Sync Route | Sync route returns 404 when cluster does not exist | Done |
| Sync Route | Sync route propagates sync errors during testing | Done |

### Inventory Route Test Notes

Inventory route smoke tests focus on HTTP behavior and page rendering.

Expected protected routes:

```text
/inventory/
/inventory/nodes
/inventory/namespaces
/inventory/workloads
/inventory/pods
/inventory/services
/inventory/ingresses
/inventory/storage
```

Authenticated page tests should assert stable page identifiers such as:

```text
Inventory Overview
Node Inventory
Namespace Inventory
Workload Inventory
Pod Inventory
Service Inventory
Ingress Inventory
Storage Inventory
```

### Inventory Pagination Test Notes

Pagination tests should avoid strict multiline HTML assertions.

Avoid:

```python
assert b'of\n                <span class="...">\n                    30\n                </span>' in response.data
```

Prefer stable assertions:

```python
assert b"Page 1 / 2" in response.data
assert b"Showing" in response.data
assert b"30" in response.data
```

Reason:

- Tailwind templates often contain long class attributes.
- Jinja output may include formatting whitespace.
- Exact multiline whitespace assertions are fragile and fail even when the UI is correct.

### Inventory Service Test Notes

Inventory service tests seed database rows directly and call service functions.

This validates the transformation from database models into dictionaries used by templates.

Examples:

```python
data = get_node_inventory()

assert data["total_nodes"] == 1
assert data["total_cpu"] == 4
assert data["nodes"][0]["runtime_display"] == "containerd"
```

### Inventory Save Function Test Notes

Save function tests mock collector functions and validate database persistence.

Examples of mocked collector functions:

```python
monkeypatch.setattr(
    "app.inventory.service.get_nodes",
    lambda api: [
        fake_node,
    ],
)
```

The `save_*` functions do not commit individually. Tests should call:

```python
db.session.commit()
```

after invoking a save function.

This matches the production flow where `sync_inventory()` performs one commit after all save functions complete.

### Inventory Sync Test Notes

`sync_inventory()` is tested as an orchestration function.

The Kubernetes client must be mocked.

The fake Kubernetes client must match the production interface:

```python
class FakeKubernetesClient:
    def core_api(self):
        ...

    def apps_api(self):
        ...

    def networking_api(self):
        ...

    def storage_api(self):
        ...
```

Do not use `get_core_api()`, `get_apps_api()`, `get_networking_api()`, or `get_storage_api()` unless the production client actually exposes those names.

### Inventory Sync Route Security

The sync route must be protected by login.

Expected route implementation:

```python
@inventory_bp.post("/<string:cluster_id>/sync")
@login_required
def sync(cluster_id: str):
    ...
```

This protects the HTMX sync endpoint the same way as normal inventory pages.

---

## Type Checking Rules for Tests

Strict type checking should remain useful in tests.

When a fake object is passed to a production function that expects Kubernetes client types, use `typing.cast()` in the test.

Example:

```python
from types import SimpleNamespace
from typing import cast

from kubernetes.client import CoreV1Api


def _core_api() -> CoreV1Api:
    return cast(
        CoreV1Api,
        SimpleNamespace(),
    )
```

Recommended mapping:

| Function | Expected API Type |
| --- | --- |
| `save_nodes()` | `CoreV1Api` |
| `save_namespaces()` | `CoreV1Api` |
| `save_workloads()` | `AppsV1Api` |
| `save_pods()` | `CoreV1Api` |
| `save_services()` | `CoreV1Api` |
| `save_ingresses()` | `NetworkingV1Api` |
| `save_storage_inventory()` | `CoreV1Api` and `StorageV1Api` |

Production service function type hints should not be weakened to `Any` just to satisfy tests.

---

## SQLAlchemy 2 Style

Tests and application code should avoid legacy query APIs where possible.

Avoid:

```python
Cluster.query.get(cluster.id)
```

Use:

```python
db.session.get(Cluster, cluster.id)
```

This avoids SQLAlchemy `LegacyAPIWarning` and keeps the project aligned with SQLAlchemy 2 style.

Known corrected pattern:

```python
cluster = db.session.get(
    Cluster,
    inventory.cluster_id,
)
```

---

## Flask-Login Deprecation Warning

When `Remember Me` is enabled, Flask-Login may emit this warning:

```text
DeprecationWarning: datetime.datetime.utcnow() is deprecated
```

The warning originates from:

```text
flask_login.login_manager
```

This is a dependency-level warning, not a KubeReport code issue.

Current decision:

- Keep the warning visible for now.
- Keep `Remember Me` enabled in tests.
- Do not suppress the warning yet.
- If the warning becomes noisy in CI, suppress only the specific Flask-Login warning, not all deprecation warnings.

---

## Running Tests

Run the authentication tests:

```powershell
python -m pytest tests/auth/test_login.py -v
```

Run the cluster tests:

```powershell
python -m pytest tests/cluster -v
```

Run the inventory tests:

```powershell
python -m pytest tests/inventory -v
```

Run a specific inventory test file:

```powershell
python -m pytest tests/inventory/test_inventory_sync_route.py -v
```

Run authentication, cluster, and inventory tests:

```powershell
python -m pytest tests/auth tests/cluster tests/inventory -v
```

Run all tests:

```powershell
python -m pytest -v
```

Run tests with print/debug output:

```powershell
python -m pytest tests/auth/test_login.py -v -s
```

Run a specific test:

```powershell
python -m pytest tests/cluster/test_cluster_routes.py::test_test_connection_route_updates_cluster_status_and_returns_table_partial -v
```

Run tests and fail on SQLAlchemy legacy warnings:

```powershell
python -m pytest tests/inventory/test_inventory_services.py -v -W error::sqlalchemy.exc.LegacyAPIWarning
```

---

## Test Categories

### Unit Tests

Purpose:

- Validate service logic.
- Mock external systems.
- Avoid dependency on live Kubernetes or Prometheus.

Examples:

- `parse_kubeconfig()`
- `create_cluster()`
- `update_cluster()`
- `convert_ki_to_gib()`
- `format_age()`
- Prometheus query builder logic.
- Analytics calculation logic.

### Route Tests

Purpose:

- Validate HTTP status codes.
- Validate redirects.
- Validate login protection.
- Validate rendered page content.
- Validate HTMX partial responses.

Examples:

- `/auth/login`
- `/auth/logout`
- `/clusters/`
- `/clusters/add`
- `/clusters/<id>/edit`
- `/clusters/<id>/delete`
- `/clusters/<id>/test`
- `/inventory/`
- `/inventory/nodes`
- `/inventory/<id>/sync`

### Database-Backed Service Tests

Purpose:

- Validate service logic that reads from or writes to the test database.
- Keep database isolated through the testing fixture.
- Avoid live external systems.

Examples:

- Inventory summary service.
- Inventory save functions.
- Cluster creation/update service.

### Integration Tests

Purpose:

- Validate multiple components working together.
- May use database, migrations, or controlled external dependencies.

Examples:

- Cluster deletion with related Prometheus config.
- Inventory sync persistence.
- Report generation persistence.

### External Integration Tests

Purpose:

- Validate real Kubernetes or Prometheus connectivity.

These tests should not run by default.

Future markers:

```ini
markers =
    integration: tests requiring database or multiple components
    external: tests requiring live external systems
```

---

## Current Testing Status

| Area | Status |
| --- | --- |
| Environment variable loading | Ready |
| Testing config | Ready |
| Test database isolation | Ready |
| Pytest baseline | Ready |
| Auth login test | Ready |
| Auth logout test | Ready |
| Cluster service test | Ready |
| Cluster route test | Ready |
| Inventory route test | Ready |
| Inventory pagination test | Ready |
| Inventory service test | Ready |
| Inventory save function test | Ready |
| Inventory sync test | Ready |
| Inventory sync route test | Ready |
| Prometheus test | Planned |
| Analytics test | Planned |
| Reports test | Planned |
| CI test workflow | Planned |

---

## Next Testing Milestones

### Milestone 1: Authentication Baseline

Status: Complete.

Scope:

- Login page test.
- Successful login test.
- Failed login test with wrong password.
- Failed login test with unknown username.
- Protected route test.
- Authenticated logout test.
- Logout route behavior test.

### Milestone 2: Cluster Management Tests

Status: Complete.

Scope:

- Kubeconfig parsing.
- Cluster creation from kubeconfig.
- Duplicate cluster validation.
- Cluster metadata update.
- Cluster route behavior.
- Cluster test connection route with mocked Kubernetes client.
- HTMX partial table response.

### Milestone 3: Inventory Tests

Status: Complete for current Sprint 1/Sprint 2 baseline.

Scope completed:

- Inventory route smoke tests.
- Inventory pagination tests.
- Inventory service aggregation tests.
- Inventory save function tests.
- Inventory sync orchestration tests.
- Inventory sync route tests.
- Login protection for sync endpoint.

Future Inventory test improvements:

- Dedicated filter combination tests for every inventory page.
- Empty-state rendering tests.
- HTMX response tests for sync table partial details.
- Integration test using a controlled fake Kubernetes data source.
- Regression tests for template query parameters such as namespace, status, type, class, and per-page selections.

### Milestone 4: Prometheus Tests

Status: Planned.

Scope:

- Prometheus config route.
- Prometheus client instant query.
- Prometheus client range query.
- Connection test behavior.
- Mocked failure handling.
- Authentication mode behavior for none/basic/bearer.
- SSL verification option behavior.

### Milestone 5: Analytics Tests

Status: Planned.

Scope:

- Utilization service with mocked Prometheus responses.
- Capacity analysis calculations.
- Top consumer ranking.
- Trends and forecasting helper logic.
- Prometheus unreachable fallback behavior.

### Milestone 6: Reports Tests

Status: Planned.

Scope:

- Report service data preparation.
- Generated report persistence.
- PDF/report rendering path.
- Report route protection.
- Error handling for missing data.

---

## Maintenance Rules

This document must be updated whenever:

- A new test module is added.
- A new fixture is added.
- A testing convention changes.
- A new external dependency needs mocking.
- A new test category is introduced.
- CI test execution changes.
- Database setup or migration strategy changes.
- A test warning is intentionally ignored or deferred.
- A route security behavior is changed because of test findings.

The document should remain the single source of truth for KubeReport testing practices.
