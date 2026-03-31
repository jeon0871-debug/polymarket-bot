from market_scanner import fetch_active_markets, filter_weather_markets, get_yes_no_token_ids

class WeatherStrategy:
    def __init__(self, order_engine, risk_manager, notifier):
        self.order_engine = order_engine
        self.risk_manager = risk_manager
        self.notifier = notifier

    def estimate_yes_probability(self, market: dict) -> float:
        text = (market.get("question", "") + " " + market.get("description", "")).lower()
        if "rain" in text:
            return 0.60
        if "storm" in text:
            return 0.58
        if "snow" in text:
            return 0.57
        if "temperature" in text or "heat" in text:
            return 0.55
        return 0.50

    def run_cycle(self):
        markets = fetch_active_markets(limit=200)
        candidates = filter_weather_markets(markets)

        for market in candidates[:10]:
            market_id = str(market.get("id") or market.get("conditionId") or market.get("question"))
            if not self.risk_manager.can_enter(market_id):
                continue

            yes_token, _ = get_yes_no_token_ids(market)
            _, best_ask, _ = self.order_engine.get_best_prices(yes_token)
            if best_ask is None:
                continue

            model_prob = self.estimate_yes_probability(market)
            edge = model_prob - best_ask - 0.03

            if edge >= 0.05:
                result = self.order_engine.place_limit_buy(
                    token_id=yes_token,
                    price=best_ask,
                    size=3.0
                )
                self.risk_manager.mark_enter(market_id)
                self.notifier.send(
                    "[WEATHER]\n"
                    f"시장: {market.get('question')}\n"
                    f"모델확률: {model_prob:.2f}\n"
                    f"시장 ask: {best_ask:.2f}\n"
                    f"엣지: {edge:.2f}\n"
                    f"응답: {result}"
                )
                from paper_trade_logger import log_paper_trade
