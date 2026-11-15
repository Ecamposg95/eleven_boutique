"""Cliente HTTP del canal de Atlas ONE (lectura de catálogo y alta de leads).

La llave nunca aparece en mensajes de error, repr ni logs.
"""

from collections.abc import Callable, Iterator
from datetime import datetime, timezone
import time

import httpx

PAGE_LIMIT = 200
MAX_RETRIES = 3
BACKOFF_BASE = 1.0
MAX_RETRY_AFTER = 60.0


class AtlasError(Exception):
    """Fallo al hablar con Atlas. El mensaje nunca incluye la llave."""


class AtlasForbidden(AtlasError):
    """Atlas respondió 403 (la llave no tiene el scope necesario)."""


def fmt_since(dt: datetime) -> str:
    """ISO 8601 en UTC con sufijo Z (una fecha ingenua se toma como UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AtlasClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 20.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._sleep = sleep
        self._http = httpx.Client(
            transport=transport,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def __repr__(self) -> str:
        return f"AtlasClient(base_url={self._base_url!r})"

    def close(self) -> None:
        self._http.close()

    def _delay(self, response: httpx.Response | None, attempt: int) -> float:
        if response is not None:
            raw = response.headers.get("Retry-After")
            if raw:
                try:
                    return min(max(float(raw), 0.0), MAX_RETRY_AFTER)
                except ValueError:
                    pass
        return BACKOFF_BASE * (2**attempt)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        url = f"{self._base_url}/{path.lstrip('/')}"
        for attempt in range(MAX_RETRIES + 1):
            response: httpx.Response | None = None
            try:
                response = self._http.request(method, url, params=params, json=json, headers=headers)
            except httpx.TransportError as exc:
                failure = f"error de red ({type(exc).__name__})"
            else:
                status = response.status_code
                if status == 403:
                    raise AtlasForbidden("Atlas respondió 403: la llave no tiene permiso")
                if status == 429 or status >= 500:
                    failure = f"Atlas respondió {status}"
                elif status >= 400:
                    raise AtlasError(f"Atlas respondió {status}")
                else:
                    return response
            if attempt == MAX_RETRIES:
                raise AtlasError(f"{failure} tras {MAX_RETRIES + 1} intentos")
            self._sleep(self._delay(response, attempt))
        raise AtlasError("reintentos agotados")  # pragma: no cover

    def iter_pages(
        self, path: str, updated_since: datetime | None
    ) -> Iterator[tuple[list[dict], str]]:
        """Páginas de `path`: (items, server_time de la primera página)."""
        params: dict[str, str | int] = {"limit": PAGE_LIMIT}
        if updated_since is not None:
            params["updated_since"] = fmt_since(updated_since)
        first_server_time: str | None = None
        while True:
            response = self._request("GET", path, params=params)
            try:
                body = response.json()
                items = body["items"]
                server_time = body["server_time"]
                cursor = body.get("next_cursor")
                if not isinstance(items, list) or not isinstance(server_time, str):
                    raise ValueError("forma inesperada")
            except (ValueError, KeyError, TypeError, AttributeError):
                raise AtlasError("respuesta inválida") from None
            if first_server_time is None:
                first_server_time = server_time
            yield items, first_server_time
            if not cursor:
                return
            params["cursor"] = cursor

    def post_lead(self, payload: dict, idempotency_key: str) -> int:
        response = self._request(
            "POST", "/leads", json=payload, headers={"Idempotency-Key": idempotency_key}
        )
        return response.status_code
