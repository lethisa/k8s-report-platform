from __future__ import annotations

import time
from typing import Any

from app.extensions.db import db
from app.models import Cluster, PrometheusConfig
from app.prometheus.client import PrometheusClient
from app.prometheus.exceptions import (
    PrometheusError,
)


class PrometheusService:
    def __init__(
        self,
        cluster: Cluster,
    ) -> None:
        self.cluster = cluster

        if not cluster.prometheus_config:
            raise PrometheusError('Prometheus configuration not found')

        self.client = PrometheusClient(cluster.prometheus_config)

    def instant_query(
        self,
        query: str,
    ) -> dict[str, Any]:
        return self.client.query(query)

    def range_query(
        self,
        query: str,
        start: str,
        end: str,
        step: str,
    ) -> dict[str, Any]:
        return self.client.query_range(
            query=query,
            start=start,
            end=end,
            step=step,
        )

    def test_connection(
        self,
    ) -> dict[str, Any]:

        started = time.perf_counter()

        self.client.query('vector(1)')

        build_info = self.client.get_build_info()

        elapsed = time.perf_counter() - started

        version = build_info.get('data', {}).get('version', 'unknown')

        return {
            'success': True,
            'version': version,
            'response_time': round(
                elapsed,
                3,
            ),
        }

    @staticmethod
    def save_config(
        cluster,
        form,
    ) -> PrometheusConfig:

        config = cluster.prometheus_config

        if not config:
            config = PrometheusConfig()
            config.cluster = cluster

            db.session.add(config)

        config.endpoint = form.endpoint.data

        config.auth_type = form.auth_type.data

        config.username = form.username.data

        config.password = form.password.data

        config.bearer_token = form.bearer_token.data

        config.timeout = form.timeout.data

        config.verify_ssl = form.verify_ssl.data

        db.session.commit()

        return config
