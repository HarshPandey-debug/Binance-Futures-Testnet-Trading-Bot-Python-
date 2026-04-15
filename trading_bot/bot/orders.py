from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .validators import (
    validate_against_exchange_filters,
    validate_decimal,
    validate_order_type,
    validate_price_for_type,
    validate_side,
    validate_stop_price_for_type,
    validate_symbol,
)


@dataclass(slots=True)
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: str
    price: str | None = None
    stop_price: str | None = None

    @classmethod
    def from_inputs(
        cls,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | float,
        price: str | float | None,
        stop_price: str | float | None,
    ) -> "OrderRequest":
        normalized_type = validate_order_type(order_type)
        return cls(
            symbol=validate_symbol(symbol),
            side=validate_side(side),
            order_type=normalized_type,
            quantity=validate_decimal("quantity", quantity),
            price=validate_price_for_type(normalized_type, price),
            stop_price=validate_stop_price_for_type(normalized_type, stop_price),
        )

    def to_api_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "quantity": self.quantity,
            "newOrderRespType": "RESULT",
        }
        if self.order_type == "LIMIT":
            params["timeInForce"] = "GTC"
            params["price"] = self.price
        if self.order_type == "STOP_MARKET":
            params["stopPrice"] = self.stop_price
            params["workingType"] = "MARK_PRICE"
        return params


@dataclass(slots=True)
class OrderService:
    client: Any
    logger: Any = None
    dry_run: bool = False
    validate_exchange_rules: bool = True

    def place_order(self, order: OrderRequest) -> dict[str, Any]:
        if self.validate_exchange_rules and not self.dry_run:
            filters = self.client.get_symbol_filters(order.symbol)
            validate_against_exchange_filters(
                quantity=order.quantity,
                price=order.price,
                stop_price=order.stop_price,
                symbol_filters=filters,
            )

        params = order.to_api_params()

        if self.logger:
            self.logger.info(
                "Validated order payload",
                extra={"event": "order_validated", "params": params},
            )

        if self.dry_run:
            mock = {
                "orderId": 999999,
                "status": "NEW",
                "executedQty": "0",
                "avgPrice": "0.0",
                "symbol": order.symbol,
                "type": order.order_type,
                "side": order.side,
            }
            if self.logger:
                self.logger.info(
                    "Dry-run mode enabled; skipping API call",
                    extra={"event": "dry_run_response", "response": mock},
                )
            return mock

        return self.client.post_signed("/fapi/v1/order", params)
