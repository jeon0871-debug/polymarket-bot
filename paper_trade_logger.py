import os
import json
import uuid
from datetime import datetime, timezone

DATA_DIR = "data"
TRADES_FILE = os.path.join(DATA_DIR, "paper_trades.jsonl")

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def log_paper_trade(record: dict):
    _ensure_dir()
    item = {
        "id": str(uuid.uuid4()),
        "created_at": now_iso(),
        "status": "open",
        **record,
    }
    with open(TRADES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item

def read_trades():
    _ensure_dir()
    if not os.path.exists(TRADES_FILE):
        return []
    rows = []
    with open(TRADES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def write_trades(rows):
    _ensure_dir()
    with open(TRADES_FILE, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
