from market_scanner import fetch_active_markets, filter_news_markets, get_yes_no_token_ids

class NewsStrategy:
    def __init__(self, order_engine, risk_manager, notifier):
        self.order_engine = order_engine
        self.risk_manager = risk_manager
        self.notifier = notifier

    def estimate_signal(self, market: dict):
        text = (market.get("question", "") + " " + market.get("description", "")).lower()
        confidence = 0.50
        direction = "unclear"
        if "election" in text or "president" in text:
            confidence = 0.72
            direction = "yes_up"
        elif "inflation" in text or "fed" in text:
            confidence = 0.70
            direction = "yes_up"
        elif "war" in text or "ceasefire" in text:
            confidence = 0.68
            direction = "yes_up"
        return {"direction": direction, "confidence": confidence}

    def run_cycle(self):
        markets = fetch_active_markets(limit=200)
        candidates = filter_news_markets(markets)

        for market in candidates[:10]:
            market_id = str(market.get("id") or market.get("conditionId") or market.get("question"))
            if not self.risk_manager.can_enter(market_id):
                continue

            signal = self.estimate_signal(market)
            if signal["direction"] != "yes_up" or signal["confidence"] < 0.70:
                continue

            yes_token, _ = get_yes_no_token_ids(market)
            _, best_ask, _ = self.order_engine.get_best_prices(yes_token)
            if best_ask is None:
                continue

            model_prob = min(0.85, 0.60 + (signal["confidence"] - 0.70))
            edge = model_prob - best_ask - 0.04

            if edge >= 0.05:
                result = self.order_engine.place_limit_buy(
                    token_id=yes_token,
                    price=best_ask,
                    size=3.0
                )
                self.risk_manager.mark_enter(market_id)
                self.notifier.send(
                    "[NEWS]\n"
                    f"시장: {market.get('question')}\n"
                    f"신뢰도: {signal['confidence']:.2f}\n"
                    f"시장 ask: {best_ask:.2f}\n"
                    f"엣지: {edge:.2f}\n"
                    f"응답: {result}"
                )
                from paper_trade_logger import log_paper_trade
