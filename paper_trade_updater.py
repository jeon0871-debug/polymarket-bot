import os
import json
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


def _calculate_pnl(entry_price: float, current_price: float, stake_usdc: float):
    if entry_price <= 0:
        return 0.0
    shares = stake_usdc / entry_price
    current_value = shares * current_price
    return round(current_value - stake_usdc, 4)


def update_paper_trades(order_engine, notifier=None):
    trades = _load_trades()
    updated = False

    for trade in trades:
        if trade.get("status") != "open":
            continue

        token_id = trade.get("token_id")
        entry_price = float(trade.get("entry_price", 0))
        stake_usdc = float(trade.get("stake_usdc", 0))

        try:
            best_bid, best_ask, _ = order_engine.get_best_prices(token_id)

            current_price = best_bid if best_bid is not None else best_ask
            if current_price is None:
                continue

            pnl_usdc = _calculate_pnl(entry_price, current_price, stake_usdc)
            trade["current_price"] = current_price
            trade["pnl_usdc"] = pnl_usdc
            trade["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 간단한 종료 규칙
            # +15% 익절 / -10% 손절
            take_profit_price = round(entry_price * 1.15, 4)
            stop_loss_price = round(entry_price * 0.90, 4)

            should_close = False
            close_reason = None

            if current_price >= take_profit_price:
                should_close = True
                close_reason = "take_profit"
            elif current_price <= stop_loss_price:
                should_close = True
                close_reason = "stop_loss"

            if should_close:
                trade["status"] = "closed"
                trade["exit_price"] = current_price
                trade["closed_at"] = datetime.now(timezone.utc).isoformat()
                trade["close_reason"] = close_reason
                updated = True

                if notifier:
                    notifier.send(
                        f"📘 페이퍼 종료\n"
                        f"전략: {trade.get('strategy')}\n"
                        f"시장: {trade.get('market_question')}\n"
                        f"진입: {entry_price:.3f}\n"
                        f"청산: {current_price:.3f}\n"
                        f"손익: ${pnl_usdc:.4f}\n"
                        f"사유: {close_reason}"
                    )
            else:
                updated = True

        except Exception as e:
            if notifier:
                notifier.send(
                    f"⚠️ paper trade 업데이트 오류\n"
                    f"trade_id: {trade.get('id')}\n"
                    f"error: {e}"
                )

    if updated:
        _save_trades(trades)

    return trades
