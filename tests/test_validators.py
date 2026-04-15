import unittest

from trading_bot.bot.orders import OrderRequest
from trading_bot.bot.validators import ValidationError, validate_against_exchange_filters


class ValidatorTests(unittest.TestCase):
    def test_limit_requires_price(self):
        with self.assertRaises(ValidationError):
            OrderRequest.from_inputs(
                symbol="BTCUSDT",
                side="BUY",
                order_type="LIMIT",
                quantity="0.001",
                price=None,
                stop_price=None,
            )

    def test_stop_market_requires_stop_price(self):
        with self.assertRaises(ValidationError):
            OrderRequest.from_inputs(
                symbol="BTCUSDT",
                side="SELL",
                order_type="STOP_MARKET",
                quantity="0.001",
                price=None,
                stop_price=None,
            )

    def test_market_disallows_price(self):
        with self.assertRaises(ValidationError):
            OrderRequest.from_inputs(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity="0.001",
                price="50000",
                stop_price=None,
            )

    def test_exchange_filters_validate_step_sizes(self):
        filters = [
            {"filterType": "LOT_SIZE", "minQty": "0.001", "maxQty": "100", "stepSize": "0.001"},
            {"filterType": "PRICE_FILTER", "tickSize": "0.1"},
        ]

        with self.assertRaises(ValidationError):
            validate_against_exchange_filters(
                quantity="0.0015",
                price="50000.2",
                stop_price=None,
                symbol_filters=filters,
            )

        with self.assertRaises(ValidationError):
            validate_against_exchange_filters(
                quantity="0.002",
                price="50000.25",
                stop_price=None,
                symbol_filters=filters,
            )

        validate_against_exchange_filters(
            quantity="0.002",
            price="50000.2",
            stop_price=None,
            symbol_filters=filters,
        )


if __name__ == "__main__":
    unittest.main()
