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
6. Route tests should validate HTTP behavior, authentication, redirects, and rendered content.
7. External systems such as Kubernetes API and Prometheus should be mocked in unit and route tests.
8. Integration tests will be added separately when the core modules are stable.

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

The expected behavior is:

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
flask run
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
from pathlib import Path

from dotenv import load_dotenv

from app.config.default import Config


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


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
- `WTF_CSRF_ENABLED = False` simplifies form submission in tests.
- `.env` is loaded in the testing config to avoid mid-file imports in `conftest.py`.
- `override=False` allows terminal environment variables to take priority over `.env`.

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
└── auth/
    └── test_login.py
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
│   ├── test_inventory_service.py
│   └── test_inventory_routes.py
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

---

## Database Lifecycle

For the current baseline test suite, the database lifecycle is:

```text
Before each test session or fixture execution:
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

Current coverage:

| Test Case | Purpose | Status |
| --- | --- | --- |
| Login page can be opened | Validate `/auth/login` renders correctly | Done |
| Login with valid credentials | Validate successful authentication | Done |
| Login with wrong password | Validate failed authentication | Done |
| Protected page requires login | Validate login protection | Done |
| Logout authenticated user | Validate session termination | Planned |
| Logout without login | Validate logout route protection | Planned |
| Login with unknown username | Validate failed authentication for unknown user | Planned |

The login test keeps the `remember` field enabled:

```python
"remember": "y"
```

This keeps the `Remember Me` behavior covered in the baseline authentication test.

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
python -m pytest tests/auth/test_login.py::test_login_success_redirects_authenticated_user -v
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
- Prometheus query builder logic
- Analytics calculation logic

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
| Testing config | Ready |
| Test database isolation | Ready |
| Pytest baseline | Ready |
| Auth login test | Ready |
| Auth logout test | Planned |
| Cluster service test | Planned |
| Cluster route test | Planned |
| Inventory test | Planned |
| Prometheus test | Planned |
| Analytics test | Planned |
| Reports test | Planned |
| CI test workflow | Planned |

---

## Next Testing Milestones

### Milestone 1: Authentication Baseline

Scope:

- Login page test.
- Successful login test.
- Failed login test.
- Protected route test.
- Logout tests.

Suggested commit:

```bash
git commit -m "test(auth): add authentication testing baseline"
```

### Milestone 2: Cluster Service Tests

Scope:

- Kubeconfig parsing.
- Cluster creation.
- Duplicate cluster validation.
- Cluster update.
- Cluster summary context.
- Cluster delete service behavior.

Suggested commit:

```bash
git commit -m "test(cluster): add cluster service tests"
```

### Milestone 3: Cluster Route Tests

Scope:

- Cluster list route.
- Add cluster route.
- Edit cluster route.
- Delete cluster route.
- Test connection route with mocked Kubernetes client.
- HTMX partial table response.

Suggested commit:

```bash
git commit -m "test(cluster): add cluster route tests"
```

### Milestone 4: Inventory Tests

Scope:

- Inventory sync service.
- Inventory summary.
- Node inventory.
- Namespace inventory.
- Workload inventory.
- Pod inventory.
- Services, ingresses, and storage inventory.

Suggested commit:

```bash
git commit -m "test(inventory): add inventory service tests"
```

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

The document should remain the single source of truth for KubeReport testing practices.
