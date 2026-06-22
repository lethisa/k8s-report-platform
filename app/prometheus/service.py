from __future__ import annotations

import time
from typing import Any

from app.extensions.db import db
from app.models import Cluster, PrometheusConfig
from app.prometheus.client import PrometheusClient
from app.prometheus.exceptions import (
    PrometheusError,
)
from app.prometheus.forms import PrometheusConfigForm


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

        result = self.client.query('vector(1)')

        if result.get('status') != 'success':
            raise PrometheusError('Prometheus query failed')

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
        cluster: Cluster,
        form: PrometheusConfigForm,
    ) -> PrometheusConfig:

        config = cluster.prometheus_config

        if not config:
            config = PrometheusConfig()
            config.cluster = cluster

            db.session.add(config)

        endpoint = form.endpoint.data
        auth_type = form.auth_type.data
        timeout = form.timeout.data
        verify_ssl = form.verify_ssl.data

        if endpoint is None:
            raise PrometheusError('Endpoint is required')

        if auth_type is None:
            raise PrometheusError('Authentication type is required')

        if timeout is None:
            raise PrometheusError('Timeout is required')

        if verify_ssl is None:
            verify_ssl = True

        config.endpoint = endpoint
        config.auth_type = auth_type

        if auth_type == 'none':
            config.username = None
            config.password = None
            config.bearer_token = None

        elif auth_type == 'basic':
            config.username = form.username.data
            config.bearer_token = None

        elif auth_type == 'bearer':
            config.username = None
            config.password = None

        if form.password.data:
            config.password = form.password.data

        if form.bearer_token.data:
            config.bearer_token = form.bearer_token.data

        config.timeout = timeout

        config.verify_ssl = verify_ssl

        db.session.commit()

        return config
