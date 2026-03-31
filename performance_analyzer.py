import csv
import os
from collections import defaultdict

CSV_FILE = os.getenv("PAPER_TRADE_LOG_FILE", "paper_trades.csv")

def analyze_performance():
    if not os.path.exists(CSV_FILE):
        return {
            "count": 0,
            "avg_pnl": 0.0,
            "win_rate": 0.0,
            "by_category": {},
            "by_strategy": {},
        }

    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["pnl"] = float(row.get("pnl", 0) or 0)
                row["confidence"] = float(row.get("confidence", 0) or 0)
                rows.append(row)
            except Exception:
                continue

    if not rows:
        return {
            "count": 0,
            "avg_pnl": 0.0,
            "win_rate": 0.0,
            "by_category": {},
            "by_strategy": {},
        }

    total = len(rows)
    wins = sum(1 for r in rows if r["pnl"] > 0)
    avg_pnl = sum(r["pnl"] for r in rows) / total

    by_category = defaultdict(lambda: {"count": 0, "wins": 0, "pnl_sum": 0.0})
    by_strategy = defaultdict(lambda: {"count": 0, "wins": 0, "pnl_sum": 0.0})

    for r in rows:
        c = r.get("category", "other")
        s = r.get("strategy", "unknown")

        by_category[c]["count"] += 1
        by_category[c]["wins"] += 1 if r["pnl"] > 0 else 0
        by_category[c]["pnl_sum"] += r["pnl"]

        by_strategy[s]["count"] += 1
        by_strategy[s]["wins"] += 1 if r["pnl"] > 0 else 0
        by_strategy[s]["pnl_sum"] += r["pnl"]

    def finalize(d):
        out = {}
        for k, v in d.items():
            out[k] = {
                "count": v["count"],
                "win_rate": (v["wins"] / v["count"]) if v["count"] else 0.0,
                "avg_pnl": (v["pnl_sum"] / v["count"]) if v["count"] else 0.0,
            }
        return out

    return {
        "count": total,
        "avg_pnl": avg_pnl,
        "win_rate": wins / total if total else 0.0,
        "by_category": finalize(by_category),
        "by_strategy": finalize(by_strategy),
    }
