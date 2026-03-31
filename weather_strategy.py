from config import load_adaptive_config
from market_scanner import fetch_active_markets, filter_weather_markets, get_yes_no_token_ids
from paper_trade_logger import log_paper_trade

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
        cfg = load_adaptive_config()
        edge_threshold = float(cfg.get("weather_edge_threshold", 0.05))
        stake = float(cfg.get("max_order_usdc", 3.0))

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

            if edge >= edge_threshold:
                result = self.order_engine.place_limit_buy(
                    token_id=yes_token,
                    price=best_ask,
                    size_usdc=stake
                )

                self.risk_manager.mark_enter(market_id)

                trade = log_paper_trade({
                    "strategy": "weather",
                    "category": "weather",
                    "market_id": market_id,
                    "market_question": market.get("question"),
                    "side": "YES",
                    "token_id": yes_token,
                    "entry_price": best_ask,
                    "stake_usdc": stake,
                    "confidence": round(model_prob, 2),
                    "edge": round(edge, 4),
                    "reason": "날씨 키워드 기반 규칙 + 엣지 조건 충족"
                })

                self.notifier.send(
                    f"✅ 날씨 베팅\n"
                    f"🟢 예, ${stake:.2f}\n"
                    f"📰 {market.get('question')}\n"
                    f"🎯 신뢰도: {round(model_prob * 100)}%\n"
                    f"📈 edge: {edge:.3f}\n"
                    f"🧾 trade_id: {trade['id']}\n"
                    f"응답: {result}"
                )
