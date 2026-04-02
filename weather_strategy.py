from config import load_adaptive_config, get_env, as_float
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
            "strategy": "weather",
            "market_id": market_id,
            "event_id": event_id,
            "size_fraction": size_fraction
        }

    def run_cycle(self):
        cfg = load_adaptive_config()
        edge_threshold = float(cfg.get("weather_edge_threshold", 0.05))

        # adaptive config 우선, 없으면 환경변수/기본값
        stake = float(cfg.get("max_order_usdc", as_float("MAX_ORDER_USDC", 3.0)))

        markets = fetch_active_markets(limit=200)
        candidates = filter_weather_markets(markets)

        for market in candidates[:10]:
            try:
                yes_token, no_token = get_yes_no_token_ids(market)

                if not yes_token:
                    continue

                best_bid, best_ask, book = self.order_engine.get_best_prices(yes_token)

                if best_ask is None:
                    continue

                model_prob = self.estimate_yes_probability(market)

                # 가격 + 완충 비용(수수료/슬리피지/오차 흡수용)
                edge = model_prob - best_ask - 0.03

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
                    "strategy": "weather",
                    "category": "weather",
                    "market_id": signal["market_id"],
                    "event_id": signal["event_id"],
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
                    f"🟢 YES, ${stake:.2f}\n"
                    f"📰 {market.get('question')}\n"
                    f"💵 ask: {best_ask:.3f}\n"
                    f"🎯 신뢰도: {round(model_prob * 100)}%\n"
                    f"📈 edge: {edge:.3f}\n"
                    f"🧾 trade_id: {trade.get('id', 'N/A')}\n"
                    f"응답: {result}"
                )

            except Exception as e:
                try:
                    self.notifier.send(
                        f"⚠️ WeatherStrategy 오류\n"
                        f"시장: {market.get('question', 'unknown')}\n"
                        f"에러: {e}"
                    )
                except Exception:
                    pass
