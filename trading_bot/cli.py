from __future__ import annotations

import argparse
import os
import sys
from textwrap import dedent

from trading_bot.bot.client import BinanceAPIError, BinanceFuturesClient, NetworkError
from trading_bot.bot.logging_config import setup_logging
from trading_bot.bot.orders import OrderRequest, OrderService
from trading_bot.bot.validators import ValidationError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Place Binance USDT-M Futures orders on Testnet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent(
            """
            Examples:
              python -m trading_bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
              python -m trading_bot.cli --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 72000
              python -m trading_bot.cli --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 68000
            """
        ),
    )

    parser.add_argument("--symbol", required=True, help="e.g., BTCUSDT")
    parser.add_argument("--side", required=True, help="BUY or SELL")
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        help="MARKET, LIMIT, STOP_MARKET",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity")
    parser.add_argument("--price", help="Required for LIMIT")
    parser.add_argument("--stop-price", help="Required for STOP_MARKET")
    parser.add_argument(
        "--base-url",
        default="https://testnet.binancefuture.com",
        help="Binance Futures API base URL",
    )
    parser.add_argument("--log-file", default="logs/trading_bot.log", help="Log output file")
    parser.add_argument("--verbose", action="store_true", help="Enable debug-level console logs")
    parser.add_argument(
        "--skip-exchange-validation",
        action="store_true",
        help="Skip exchange lot-size/tick-size validation prechecks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and log only, without placing a real order",
    )

    return parser.parse_args()


def print_summary(order: OrderRequest) -> None:
    print("\nOrder Request Summary")
    print("-" * 40)
    print(f"Symbol      : {order.symbol}")
    print(f"Side        : {order.side}")
    print(f"Type        : {order.order_type}")
    print(f"Quantity    : {order.quantity}")
    print(f"Price       : {order.price if order.price else 'N/A'}")
    print(f"Stop Price  : {order.stop_price if order.stop_price else 'N/A'}")


def print_response(response: dict[str, object]) -> None:
    print("\nOrder Response")
    print("-" * 40)
    print(f"Order ID    : {response.get('orderId', 'N/A')}")
    print(f"Status      : {response.get('status', 'N/A')}")
    print(f"Executed Qty: {response.get('executedQty', 'N/A')}")
    print(f"Avg Price   : {response.get('avgPrice', 'N/A')}")


def main() -> int:
    args = parse_args()
    logger = setup_logging(args.log_file, verbose=args.verbose)

    try:
        order = OrderRequest.from_inputs(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )

        print_summary(order)

        if not args.dry_run:
            api_key = os.getenv("BINANCE_TESTNET_API_KEY")
            api_secret = os.getenv("BINANCE_TESTNET_API_SECRET")

            if not api_key or not api_secret:
                raise ValidationError(
                    "Missing BINANCE_TESTNET_API_KEY or BINANCE_TESTNET_API_SECRET environment variables"
                )
        else:
            api_key = "dry-run"
            api_secret = "dry-run"

        client = BinanceFuturesClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=args.base_url,
            logger=logger,
        )
        service = OrderService(
            client=client,
            logger=logger,
            dry_run=args.dry_run,
            validate_exchange_rules=not args.skip_exchange_validation,
        )
        response = service.place_order(order)

        print_response(response)
        if args.dry_run:
            print("\n✅ Dry run successful (no live order sent).")
        else:
            print("\n✅ Order placed successfully.")

        return 0

    except ValidationError as exc:
        logger.error(
            "Input validation failed",
            extra={
                "event": "validation_error",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        print(f"\n❌ Validation error: {exc}")
        return 2

    except (BinanceAPIError, NetworkError) as exc:
        logger.error(
            "Order placement failed",
            extra={
                "event": "order_error",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            exc_info=True,
        )
        print(f"\n❌ Failed to place order: {exc}")
        return 1

    except Exception as exc:  # Defensive top-level handler
        logger.error(
            "Unexpected fatal error",
            extra={
                "event": "unexpected_error",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
            exc_info=True,
        )
        print(f"\n❌ Unexpected error: {exc}")
        return 99


if __name__ == "__main__":
    sys.exit(main())
