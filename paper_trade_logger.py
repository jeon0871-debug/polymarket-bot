import csv
import os
from datetime import datetime

CSV_FILE = os.getenv("PAPER_TRADE_LOG_FILE", "paper_trades.csv")

FIELDNAMES = [
    "timestamp",
    "strategy",
    "market_id",
    "market_question",
    "category",
    "side",
    "size_usdc",
    "entry_price",
    "model_prob",
    "edge",
    "confidence",
    "status",
    "reason",
    "pnl",
]

def _ensure_file():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

def log_paper_trade(
    strategy: str,
    market_id: str,
    market_question: str,
    category: str,
    side: str,
    size_usdc: float,
    entry_price: float,
    model_prob: float,
    edge: float,
    confidence: float,
    status: str,
    reason: str,
    pnl: float = 0.0,
):
    _ensure_file()
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "strategy": strategy,
        "market_id": market_id,
        "market_question": market_question,
        "category": category,
        "side": side,
        "size_usdc": round(size_usdc, 4),
        "entry_price": round(entry_price, 4),
        "model_prob": round(model_prob, 4),
        "edge": round(edge, 4),
        "confidence": round(confidence, 4),
        "status": status,
        "reason": reason,
        "pnl": round(pnl, 4),
    }
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)
