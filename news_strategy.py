from config import load_adaptive_config, as_float
from market_scanner import fetch_active_markets, filter_news_markets, get_yes_no_token_ids
from paper_trade_logger import log_paper_trade


class NewsStrategy:
    def __init__(self, order_engine, risk_manager, notifier):
        self.order_engine = order_engine
        self.risk_manager = risk_manager
        self.notifier = notifier

    def detect_category(self, text: str) -> str:
        text = text.lower()

        if any(k in text for k in ["war", "ukraine", "russia", "ceasefire", "taiwan"]):
            return "war"
        if any(k in text for k in ["election", "president", "trump", "biden"]):
            return "election"
        if any(k in text for k in ["bitcoin", "btc"]):
            return "bitcoin"
        if any(k in text for k in ["fed", "inflation", "rate cut", "macro"]):
            return "macro"

        return "other"

    def estimate_signal(self, market: dict, cfg: dict):
        text = (market.get("question", "") + " " + market.get("description", "")).lower()
        category = self.detect_category(text)

        confidence = 0.50
        direction = "unclear"
        reason = "규칙 미충족"

        if "election" in text or "president" in text:
            confidence = 0.72
            direction = "yes_up"
            reason = "선거/대통령 키워드"
        elif "inflation" in text or "fed" in text:
            confidence = 0.70
            direction = "yes_up"
            reason = "거시경제 키워드"
        elif "war" in text or "ceasefire" in text:
            confidence = 0.75
            direction = "yes_up"
            reason = "전쟁 키워드"
        elif "bitcoin" in text:
            confidence = 0.65
            direction = "yes_up"
            reason = "비트코인 키워드"

        weight = cfg.get("category_weights", {}).get(category, 1.0)
        confidence = min(0.95, confidence * weight)

        return {
            "direction": direction,
            "confidence": confidence,
            "reason": reason,
            "category": category
        }

    def build_signal(self, market: dict, stake_usdc: float) -> dict:
        capital = as_float("BOT_CAPITAL_USDC", 300.0)
        size_fraction = stake_usdc / capital if capital > 0 else 0.0

        market_id = str(market.get("id") or market.get("conditionId") or market.get("question"))
        event_id = str(
            market.get("eventId")
            or market.get("event_id")
            or market.get("seriesId")
            or market_id
        )

        return {
            "strategy": "news",
            "market_id": market_id,
            "event_id": event_id,
            "size_fraction": size_fraction
        }

    def run_cycle(self):
        cfg = load_adaptive_config()

        edge_threshold = float(cfg.get("news_edge_threshold", 0.05))
        min_conf = float(cfg.get("min_confidence", 0.70))
        stake = float(cfg.get("max_order_usdc", as_float("MAX_ORDER_USDC", 3.0)))

        markets = fetch_active_markets(limit=200)
        candidates = filter_news_markets(markets)

        for market in candidates[:10]:
            try:
                yes_token, _ = get_yes_no_token_ids(market)

                if not yes_token:
                    continue

                _, best_ask, _ = self.order_engine.get_best_prices(yes_token)

                if best_ask is None:
                    continue

                # 고가 필터
                if best_ask >= 0.85:
                    continue

                signal_data = self.estimate_signal(market, cfg)

                if signal_data["direction"] != "yes_up":
                    continue

                if signal_data["confidence"] < min_conf:
                    continue

                model_prob = signal_data["confidence"]
                edge = model_prob - best_ask - 0.04

                if edge < edge_threshold:
                    continue

                signal = self.build_signal(market, stake)

                if not self.risk_manager.can_trade(signal):
                    continue

                result = self.order_engine.place_limit_buy(
                    token_id=yes_token,
                    price=best_ask,
                    size_usdc=stake
                )

                self.risk_manager.register_open_exposure(signal)

                trade = log_paper_trade({
                    "strategy": "news",
                    "category": signal_data["category"],
                    "market_id": signal["market_id"],
                    "event_id": signal["event_id"],
                    "market_question": market.get("question"),
                    "side": "YES",
                    "token_id": yes_token,
                    "entry_price": best_ask,
                    "stake_usdc": stake,
                    "confidence": round(signal_data["confidence"], 2),
                    "edge": round(edge, 4),
                    "reason": signal_data["reason"]
                })

                self.notifier.send(
                    f"📰 뉴스 베팅\n"
                    f"🟢 YES ${stake:.2f}\n"
                    f"{market.get('question')}\n"
                    f"📂 {signal_data['category']}\n"
                    f"🎯 {round(signal_data['confidence']*100)}%\n"
                    f"📈 edge: {edge:.3f}"
                )

            except Exception as e:
                try:
                    self.notifier.send(
                        f"⚠️ NewsStrategy 오류\n"
                        f"{market.get('question', 'unknown')}\n"
                        f"{e}"
                    )
                except Exception:
                    pass
