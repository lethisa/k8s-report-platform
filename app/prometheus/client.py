from __future__ import annotations

from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from app.models import PrometheusConfig
from app.prometheus.exceptions import (
    PrometheusAuthenticationError,
    PrometheusConnectionError,
    PrometheusQueryError,
)


class PrometheusClient:
    def __init__(
        self,
        config: PrometheusConfig,
    ) -> None:
        self.config = config
        self.base_url = config.endpoint.rstrip('/')

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}

        if self.config.auth_type == 'bearer' and self.config.bearer_token:
            headers['Authorization'] = f'Bearer {self.config.bearer_token}'

        return headers

    def _build_auth(
        self,
    ) -> HTTPBasicAuth | None:
        if self.config.auth_type == 'basic' and self.config.username and self.config.password:
            return HTTPBasicAuth(
                self.config.username,
                self.config.password,
            )

        return None

    def query(
        self,
        query: str,
    ) -> dict[str, Any]:

        url = f'{self.base_url}/api/v1/query'

        try:
            response = requests.get(
                url,
                params={'query': query},
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )

            self._validate_response(response)

            return response.json()

        except requests.exceptions.ConnectionError as exc:
            raise PrometheusConnectionError(str(exc)) from exc

        except requests.exceptions.Timeout as exc:
            raise PrometheusConnectionError('Connection timeout') from exc

        except requests.exceptions.RequestException as exc:
            raise PrometheusConnectionError(str(exc)) from exc

    def query_range(
        self,
        query: str,
        start: str,
        end: str,
        step: str,
    ) -> dict[str, Any]:

        url = f'{self.base_url}/api/v1/query_range'

        try:
            response = requests.get(
                url,
                params={
                    'query': query,
                    'start': start,
                    'end': end,
                    'step': step,
                },
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )

            self._validate_response(response)

            return response.json()

        except requests.exceptions.ConnectionError as exc:
            raise PrometheusConnectionError(str(exc)) from exc

        except requests.exceptions.Timeout as exc:
            raise PrometheusConnectionError('Connection timeout') from exc

        except requests.exceptions.RequestException as exc:
            raise PrometheusConnectionError(str(exc)) from exc

    def get_build_info(
        self,
    ) -> dict[str, Any]:

        url = f'{self.base_url}/api/v1/status/buildinfo'

        try:
            response = requests.get(
                url,
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )

            self._validate_response(response)

            return response.json()

        except requests.exceptions.ConnectionError as exc:
            raise PrometheusConnectionError(str(exc)) from exc

        except requests.exceptions.Timeout as exc:
            raise PrometheusConnectionError('Connection timeout') from exc

        except requests.exceptions.RequestException as exc:
            raise PrometheusConnectionError(str(exc)) from exc

    @staticmethod
    def _validate_response(
        response: requests.Response,
    ) -> None:

        if response.status_code in (401, 403):
            raise PrometheusAuthenticationError('Authentication failed')

        if response.status_code >= 400:
            raise PrometheusQueryError(f'HTTP {response.status_code}')
