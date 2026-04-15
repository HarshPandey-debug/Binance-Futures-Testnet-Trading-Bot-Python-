# Binance Futures Testnet Trading Bot (Python)

A senior-grade, production-leaning CLI app for placing **USDT-M Futures** orders on Binance Testnet.

## Features

- Place `MARKET` and `LIMIT` orders on Binance Futures Testnet (`https://testnet.binancefuture.com`)
- Bonus order type: `STOP_MARKET`
- Supports both sides: `BUY` and `SELL`
- Strict CLI input validation for symbol, side, type, quantity, price, and stop price rules
- Optional exchange-rule prechecks (tick size / lot size) before submitting orders
- Structured architecture:
  - API client layer (`trading_bot/bot/client.py`)
  - Order domain/service layer (`trading_bot/bot/orders.py`)
  - Validation layer (`trading_bot/bot/validators.py`)
  - Logging setup (`trading_bot/bot/logging_config.py`)
  - CLI entrypoint (`trading_bot/cli.py`)
- Structured JSON logging to file (request/response/error events)
- Robust exception handling for validation issues, API failures, and network errors
- Retry with backoff for transient network failures
- `--dry-run` mode for deterministic local demonstration and interview walkthroughs

---

## 1) Setup

### Prerequisites

- Python 3.10+
- Binance Futures Testnet account and API credentials

### Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment variables

```bash
export BINANCE_TESTNET_API_KEY="your_key"
export BINANCE_TESTNET_API_SECRET="your_secret"
```

> These env vars are required for live testnet orders and optional for `--dry-run`.

---

## 2) Usage

### MARKET order

```bash
python -m trading_bot.cli \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

### LIMIT order

```bash
python -m trading_bot.cli \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 90000
```

### STOP_MARKET order (bonus)

```bash
python -m trading_bot.cli \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_MARKET \
  --quantity 0.001 \
  --stop-price 68000
```

### Dry run (no API call)

```bash
python -m trading_bot.cli \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001 \
  --dry-run \
  --log-file logs/market_order.log
```

---

## 3) Output behavior

The CLI prints:

1. Order request summary
2. Order response details (`orderId`, `status`, `executedQty`, `avgPrice`)
3. Clear success/failure status message

---

## 4) Logging

- Default log file: `logs/trading_bot.log`
- Log format: JSON lines (good for debugging and ingestion into tools)
- Captures:
  - validated order payload
  - API request metadata
  - API response metadata
  - validation, network, and API errors

### Required sample logs included

- `logs/market_order.log`
- `logs/limit_order.log`

---

## 5) Assumptions

- This app targets **USDT-M Futures testnet** only.
- LIMIT orders are placed with `timeInForce=GTC`.
- For live orders, exchange filters are fetched from `/fapi/v1/exchangeInfo` and used to pre-validate quantity and price increments.

---

## 6) Project structure

```text
trading_bot/
  __init__.py
  cli.py
  bot/
    __init__.py
    client.py
    orders.py
    validators.py
    logging_config.py
tests/
  test_validators.py
logs/
  market_order.log
  limit_order.log
README.md
requirements.txt
```

---

## 7) Test commands

```bash
python -m unittest discover -s tests -v
python -m compileall trading_bot
```

---

## 8) Interview talking points (senior signals)

- Separation of concerns with clear module boundaries
- Typed interfaces and dataclass-driven request modeling
- Structured logs with semantic event names
- Defensive error classification (validation/api/network/unexpected)
- Deterministic demo mode (`--dry-run`) to prove behavior without environment dependencies
- Exchange-rule pre-validation to fail fast before costly API calls
