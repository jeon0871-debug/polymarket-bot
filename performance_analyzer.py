import os
import json
from collections import defaultdict
from paper_trade_logger import read_trades

SUMMARY_FILE = os.path.join("data", "performance_summary.json")

def analyze_performance():
    rows = read_trades()
    closed = [r for r in rows if r.get("status") == "closed"]

    result = {
        "total_closed": len(closed),
        "total_pnl": 0.0,
        "win_rate": 0.0,
        "avg_pnl": 0.0,
        "by_category": {}
    }

    if not closed:
        return result

    wins = sum(1 for r in closed if float(r.get("pnl", 0)) > 0)
    total_pnl = sum(float(r.get("pnl", 0)) for r in closed)

    result["total_pnl"] = round(total_pnl, 2)
    result["win_rate"] = round(wins / len(closed), 4)
    result["avg_pnl"] = round(total_pnl / len(closed), 2)

    grouped = defaultdict(list)
    for row in closed:
        grouped[row.get("category", "other")].append(row)

    by_category = {}
    for category, items in grouped.items():
        c_pnl = sum(float(r.get("pnl", 0)) for r in items)
        c_win = sum(1 for r in items if float(r.get("pnl", 0)) > 0)
        by_category[category] = {
            "count": len(items),
            "total_pnl": round(c_pnl, 2),
            "win_rate": round(c_win / len(items), 4)
        }

    result["by_category"] = by_category
    return result

def analyze_and_save():
    summary = analyze_performance()
    os.makedirs("data", exist_ok=True)
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary
