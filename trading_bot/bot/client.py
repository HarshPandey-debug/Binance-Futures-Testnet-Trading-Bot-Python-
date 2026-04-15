from __future__ import annotations

import hashlib
import hmac
import json
import socket
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BinanceAPIError(RuntimeError):
    """Raised when Binance returns a non-2xx response."""


class NetworkError(RuntimeError):
    """Raised for transport-level failures."""


@dataclass(slots=True)
class BinanceFuturesClient:
    api_key: str
    api_secret: str
    base_url: str = "https://testnet.binancefuture.com"
    timeout_seconds: int = 10
    max_retries: int = 2
    logger: Any = None
    _exchange_info_cache: dict[str, Any] = field(default_factory=dict)

    def _sign_params(self, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "timestamp": int(time.time() * 1000), "recvWindow": 5_000}
        qs = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"), qs.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return {**params, "signature": signature}

    def _request(
        self, method: str, path: str, params: dict[str, Any] | None = None, signed: bool = False
    ) -> dict[str, Any]:
        params = params or {}
        query_params = self._sign_params(params) if signed else params

        url = f"{self.base_url}{path}"
        body = None
        if method == "GET":
            if query_params:
                url = f"{url}?{urlencode(query_params)}"
        else:
            body = urlencode(query_params).encode("utf-8")

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key

        request = Request(url=url, data=body, method=method, headers=headers)

        if self.logger:
            self.logger.info(
                "Submitting request",
                extra={
                    "event": "api_request",
                    "method": method,
                    "url": url,
                    "params": query_params,
                },
            )

        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    raw_payload = response.read().decode("utf-8")
                    status_code = response.status
                payload = json.loads(raw_payload)

                if self.logger:
                    self.logger.info(
                        "Received API response",
                        extra={
                            "event": "api_response",
                            "method": method,
                            "url": url,
                            "status_code": status_code,
                            "response": payload,
                        },
                    )
                return payload

            except HTTPError as exc:
                raw_payload = exc.read().decode("utf-8")
                try:
                    payload = json.loads(raw_payload)
                except json.JSONDecodeError:
                    payload = {"raw": raw_payload}

                if self.logger:
                    self.logger.error(
                        "Binance API rejected request",
                        extra={
                            "event": "api_response",
                            "method": method,
                            "url": url,
                            "status_code": exc.code,
                            "response": payload,
                        },
                    )
                raise BinanceAPIError(f"Binance API error ({exc.code}): {payload}") from exc

            except (URLError, TimeoutError, socket.timeout, OSError) as exc:
                is_last = attempt >= self.max_retries
                if self.logger:
                    self.logger.error(
                        "Network failure during request",
                        extra={
                            "event": "network_error",
                            "method": method,
                            "url": url,
                            "params": query_params,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        },
                        exc_info=True,
                    )
                if is_last:
                    raise NetworkError(str(exc)) from exc
                time.sleep(0.5 * (attempt + 1))

        raise NetworkError("Network request failed after retries")

    def post_signed(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, params=params, signed=True)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params, signed=False)

    def get_symbol_filters(self, symbol: str) -> list[dict[str, Any]] | None:
        if symbol in self._exchange_info_cache:
            return self._exchange_info_cache[symbol]

        payload = self.get("/fapi/v1/exchangeInfo")
        symbols = payload.get("symbols", [])
        for entry in symbols:
            if entry.get("symbol") == symbol:
                filters = entry.get("filters", [])
                self._exchange_info_cache[symbol] = filters
                return filters
        return None
