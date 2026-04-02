import os
import json
import uuid
from datetime import datetime, timezone

PAPER_TRADES_FILE = "paper_trades.json"


def _load_trades():
    if not os.path.exists(PAPER_TRADES_FILE):
        return []
    with open(PAPER_TRADES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_trades(trades):
    with open(PAPER_TRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


def log_paper_trade(trade: dict):
    trades = _load_trades()

    trade_record = {
        "id": str(uuid.uuid4())[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
        "exit_price": None,
        "pnl_usdc": None,
        **trade
    }

    trades.append(trade_record)
    _save_trades(trades)

    return trade_record
