import os
import json
from collections import defaultdict
from paper_trade_logger import read_trades

SUMMARY_FILE = os.path.join("data", "performance_summary.json")

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def analyze_performance():
    rows = read_trades()
    closed = [r for r in rows if r.get("status") == "closed"]

    result = {
        "total_closed": len(closed),
        "total_pnl": 0.0,
        "win_rate": 0.0,
        "avg_pnl": 0.0,
        "by_category": {},
        "by_strategy": {}
    }

    if not closed:
        return result

    wins = sum(1 for r in closed if _safe_float(r.get("pnl", 0)) > 0)
    total_pnl = sum(_safe_float(r.get("pnl", 0)) for r in closed)

    result["total_pnl"] = round(total_pnl, 2)
    result["win_rate"] = round(wins / len(closed), 4)
    result["avg_pnl"] = round(total_pnl / len(closed), 2)

    grouped_category = defaultdict(list)
    grouped_strategy = defaultdict(list)

    for row in closed:
        grouped_category[row.get("category", "other")].append(row)
        grouped_strategy[row.get("strategy", "unknown")].append(row)

    by_category = {}
    for category, items in grouped_category.items():
        c_pnl = sum(_safe_float(r.get("pnl", 0)) for r in items)
        c_win = sum(1 for r in items if _safe_float(r.get("pnl", 0)) > 0)
        by_category[category] = {
            "count": len(items),
            "total_pnl": round(c_pnl, 2),
            "win_rate": round(c_win / len(items), 4),
            "avg_pnl": round(c_pnl / len(items), 2)
        }

    by_strategy = {}
    for strategy, items in grouped_strategy.items():
        s_pnl = sum(_safe_float(r.get("pnl", 0)) for r in items)
        s_win = sum(1 for r in items if _safe_float(r.get("pnl", 0)) > 0)
        by_strategy[strategy] = {
            "count": len(items),
            "total_pnl": round(s_pnl, 2),
            "win_rate": round(s_win / len(items), 4),
            "avg_pnl": round(s_pnl / len(items), 2)
        }

    result["by_category"] = by_category
    result["by_strategy"] = by_strategy
    return result

def analyze_and_save():
    summary = analyze_performance()
    os.makedirs("data", exist_ok=True)
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary
