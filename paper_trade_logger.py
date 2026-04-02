import json
import os
from datetime import datetime, timezone

PAPER_TRADE_FILE = "paper_trades.json"


def _load_trades():
    if not os.path.exists(PAPER_TRADE_FILE):
        return []

    try:
        with open(PAPER_TRADE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_trades(trades):
    with open(PAPER_TRADE_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


def read_trades():
    """
    performance_analyzer.py 에서 불러다 쓰는 함수
    """
    return _load_trades()


def log_paper_trade(trade: dict):
    trades = _load_trades()

    new_trade = {
        "id": len(trades) + 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "OPEN",
        **trade
    }

    trades.append(new_trade)
    _save_trades(trades)
    return new_trade


def update_trade(trade_id: int, updates: dict):
    trades = _load_trades()

    for trade in trades:
        if trade.get("id") == trade_id:
            trade.update(updates)
            trade["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_trades(trades)
            return trade

    return None


def close_trade(trade_id: int, exit_price: float, pnl_usdc: float, result: str = None):
    trades = _load_trades()

    for trade in trades:
        if trade.get("id") == trade_id:
            trade["status"] = "CLOSED"
            trade["exit_price"] = exit_price
            trade["pnl_usdc"] = pnl_usdc
            trade["closed_at"] = datetime.now(timezone.utc).isoformat()
            if result:
                trade["result"] = result
            _save_trades(trades)
            return trade

    return None
