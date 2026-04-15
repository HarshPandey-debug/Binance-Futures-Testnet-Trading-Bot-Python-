from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

VALID_SIDES = {"BUY", "SELL"}
VALID_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


class ValidationError(ValueError):
    """Raised when CLI arguments fail business validation."""


def validate_symbol(symbol: str) -> str:
    clean = symbol.strip().upper()
    if not clean or len(clean) < 6:
        raise ValidationError("symbol must look like BTCUSDT")
    if not clean.isalnum():
        raise ValidationError("symbol must contain only letters and numbers")
    return clean


def validate_side(side: str) -> str:
    clean = side.strip().upper()
    if clean not in VALID_SIDES:
        raise ValidationError(f"side must be one of: {', '.join(sorted(VALID_SIDES))}")
    return clean


def validate_order_type(order_type: str) -> str:
    clean = order_type.strip().upper()
    if clean not in VALID_TYPES:
        raise ValidationError(
            f"order type must be one of: {', '.join(sorted(VALID_TYPES))}"
        )
    return clean


def parse_positive_decimal(field_name: str, value: str | float | int | None) -> Decimal:
    if value is None:
        raise ValidationError(f"{field_name} is required")

    try:
        dec = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a valid number") from exc

    if dec <= 0:
        raise ValidationError(f"{field_name} must be greater than 0")

    return dec


def validate_decimal(field_name: str, value: str | float | int | None) -> str:
    return format(parse_positive_decimal(field_name, value).normalize(), "f")


def validate_price_for_type(order_type: str, price: str | float | int | None) -> str | None:
    if order_type == "LIMIT":
        return validate_decimal("price", price)

    if price is not None:
        raise ValidationError("price is only allowed for LIMIT orders")

    return None


def validate_stop_price_for_type(
    order_type: str, stop_price: str | float | int | None
) -> str | None:
    if order_type == "STOP_MARKET":
        return validate_decimal("stop_price", stop_price)

    if stop_price is not None:
        raise ValidationError("stop_price is only allowed for STOP_MARKET orders")

    return None


def _extract_filter(filters: list[dict[str, Any]], filter_type: str) -> dict[str, Any] | None:
    return next((item for item in filters if item.get("filterType") == filter_type), None)


def _is_multiple_of(value: Decimal, step: Decimal) -> bool:
    if step == 0:
        return True
    return value % step == 0


def validate_against_exchange_filters(
    quantity: str,
    price: str | None,
    stop_price: str | None,
    symbol_filters: list[dict[str, Any]] | None,
) -> None:
    if not symbol_filters:
        return

    lot = _extract_filter(symbol_filters, "LOT_SIZE")
    if lot:
        qty = parse_positive_decimal("quantity", quantity)
        min_qty = Decimal(lot["minQty"])
        max_qty = Decimal(lot["maxQty"])
        step = Decimal(lot["stepSize"])
        if qty < min_qty or qty > max_qty:
            raise ValidationError(
                f"quantity out of bounds for symbol ({min_qty} - {max_qty})"
            )
        if not _is_multiple_of(qty, step):
            raise ValidationError(f"quantity must align to stepSize {step}")

    price_filter = _extract_filter(symbol_filters, "PRICE_FILTER")
    if price_filter:
        tick = Decimal(price_filter["tickSize"])
        if price is not None:
            price_dec = parse_positive_decimal("price", price)
            if not _is_multiple_of(price_dec, tick):
                raise ValidationError(f"price must align to tickSize {tick}")
        if stop_price is not None:
            stop_dec = parse_positive_decimal("stop_price", stop_price)
            if not _is_multiple_of(stop_dec, tick):
                raise ValidationError(f"stop_price must align to tickSize {tick}")
