# KubeReport

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-black)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-green)

KubeReport is an open-source Kubernetes Capacity Planning and Reporting Platform built with Flask.

It helps platform engineers, DevOps teams, SREs, and infrastructure operators collect inventory data from Kubernetes clusters, analyze resource utilization, generate operational insights, and create capacity planning reports.

---

## Current Status

Current Development Phase:

- ✅ Sprint 1 - Foundation & Inventory
- 🚧 Sprint 2 - Analytics
- 📋 Sprint 3 - Reporting

---

## Features

### Dashboard

- Cluster overview
- Resource summary
- Operational insights
- Quick navigation

### Cluster Management

- Register Kubernetes clusters
- Test cluster connectivity
- Manage cluster inventory collection

### Inventory

Discover and explore Kubernetes resources across connected clusters.

Supported resources:

- Nodes
- Namespaces
- Workloads
- Pods
- Services
- Ingresses
- Storage

### Analytics (In Progress)

Analyze cluster resource consumption and capacity trends.

Planned modules:

- Analytics Overview
- Resource Utilization
- Capacity Analysis
- Trends & Forecasting
- Top Consumers
- Alerts & Anomalies

### Reporting (Planned)

Generate operational and capacity reports.

Planned modules:

- Reports
- Generate Report
- Templates
- History

---

## Screenshots

### Inventory Overview

![Inventory Overview](docs/images/inventory-overview.png)

### Analytics Overview

> Coming Soon

### Reporting

> Coming Soon

---

## Architecture

```text
Kubernetes Clusters
        │
        ▼
Inventory Collector
        │
        ▼
PostgreSQL Database
        │
        ▼
Analytics Engine
        │
        ▼
Reporting Engine
        │
        ▼
Dashboard & Reports
```

---

## Technology Stack

### Backend

- Python 3.13+
- Flask
- SQLAlchemy
- Flask-Migrate
- Alembic

### Frontend

- Jinja2
- Tailwind CSS
- Alpine.js
- Lucide Icons

### Database

- PostgreSQL

### Kubernetes

- Kubernetes Python Client
- Prometheus (Planned)

---

## Project Structure

```text
app/
├── analytics/
├── api/
├── auth/
├── cluster/
├── dashboard/
├── inventory/
├── kubernetes/
├── models/
├── reports/
├── static/
├── templates/
└── utils/
```

---

## Getting Started

### Clone Repository

```bash
git clone https://github.com/<your-org>/kubereport.git

cd kubereport
```

### Create Virtual Environment

```bash
python -m venv .venv
```

Linux / macOS

```bash
source .venv/bin/activate
```

Windows

```powershell
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

Create:

```text
.env
```

Example:

```env
APP_ENV=development

SECRET_KEY=change-me

DATABASE_URL=postgresql://postgres:postgres@localhost/kubereport
```

### Run Database Migration

```bash
flask db upgrade
```

### Start Application

```bash
python run.py
```

Application will be available at:

```text
http://localhost:5000
```

---

## Development

### Format Code

```bash
ruff format .
```

### Lint Code

```bash
ruff check .
```

### Run Tests

```bash
pytest
```

---

## Documentation

Additional documentation is available under the `docs/` directory.

- Architecture
- Development Guides
- Sprint History
- Roadmap
- Design Decisions

---

## Contributing

Contributions are welcome.

Please open an issue before submitting large changes.

Workflow:

1. Fork repository
2. Create feature branch
3. Commit changes
4. Open Pull Request

---

## License

This project is released under the MIT License.

---

## Maintainer

Lethisa Putri
