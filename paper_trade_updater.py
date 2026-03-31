from datetime import datetime, timezone
from config import load_adaptive_config
from paper_trade_logger import read_trades, write_trades

def _parse_iso(s: str):
    return datetime.fromisoformat(s)

def update_paper_trades(order_engine, notifier=None):
    cfg = load_adaptive_config()
    hold_minutes = cfg.get("paper_hold_minutes", 60)

    rows = read_trades()
    changed = False
    now = datetime.now(timezone.utc)

    for row in rows:
        if row.get("status") != "open":
            continue

        created_at = _parse_iso(row["created_at"])
        elapsed_min = (now - created_at).total_seconds() / 60

        if elapsed_min < hold_minutes:
            continue

        token_id = row["token_id"]
        entry_price = float(row["entry_price"])
        stake = float(row["stake_usdc"])

        best_bid, best_ask, _ = order_engine.get_best_prices(token_id)
        exit_price = best_bid if best_bid is not None else entry_price

        pnl = ((exit_price - entry_price) / max(entry_price, 0.01)) * stake

        row["status"] = "closed"
        row["closed_at"] = now.isoformat()
        row["exit_price"] = exit_price
        row["pnl"] = round(pnl, 2)
        changed = True

        if notifier:
            notifier.send(
                f"📘 모의거래 종료\n"
                f"시장: {row.get('market_question')}\n"
                f"방향: {row.get('side')}\n"
                f"진입가: {entry_price:.2f}\n"
                f"청산가: {exit_price:.2f}\n"
                f"PnL: {row['pnl']:+.2f}"
            )

    if changed:
        write_trades(rows)
