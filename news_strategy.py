from config import load_adaptive_config
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
            reason = "선거/대통령 관련 키워드 감지"
        elif "inflation" in text or "fed" in text or "rate cut" in text:
            confidence = 0.70
            direction = "yes_up"
            reason = "거시경제 키워드 감지"
        elif "war" in text or "ceasefire" in text or "ukraine" in text or "russia" in text:
            confidence = 0.75
            direction = "yes_up"
            reason = "전쟁/휴전 키워드 감지"
        elif "bitcoin" in text or "btc" in text:
            confidence = 0.65
            direction = "yes_up"
            reason = "비트코인 키워드 감지"

        weight = cfg.get("category_weights", {}).get(category, 1.0)
        confidence = min(0.95, confidence * weight)

        blocked_keywords = cfg.get("blocked_keywords", [])
        if any(k.lower() in text for k in blocked_keywords):
            reason = "차단 키워드 포함"
            return {
                "direction": "unclear",
                "confidence": 0.0,
                "reason": reason,
                "category": category
            }

        return {
            "direction": direction,
            "confidence": confidence,
            "reason": reason,
            "category": category
        }

    def run_cycle(self):
        cfg = load_adaptive_config()
        edge_threshold = float(cfg.get("news_edge_threshold", 0.05))
        min_conf = float(cfg.get("min_confidence", 0.70))
        stake = float(cfg.get("max_order_usdc", 3.0))

        markets = fetch_active_markets(limit=200)
        candidates = filter_news_markets(markets)

        for market in candidates[:10]:
            market_id = str(market.get("id") or market.get("conditionId") or market.get("question"))
            if not self.risk_manager.can_enter(market_id):
                continue

            signal = self.estimate_signal(market, cfg)
            if signal["direction"] != "yes_up" or signal["confidence"] < min_conf:
                continue

            yes_token, _ = get_yes_no_token_ids(market)
            _, best_ask, _ = self.order_engine.get_best_prices(yes_token)

            if best_ask is None:
                continue

            model_prob = min(0.95, signal["confidence"])
            edge = model_prob - best_ask - 0.04

            if edge >= edge_threshold:
                result = self.order_engine.place_limit_buy(
                    token_id=yes_token,
                    price=best_ask,
                    size_usdc=stake
                )

                self.risk_manager.mark_enter(market_id)

                trade = log_paper_trade({
                    "strategy": "news",
                    "category": signal["category"],
                    "market_id": market_id,
                    "market_question": market.get("question"),
                    "side": "YES",
                    "token_id": yes_token,
                    "entry_price": best_ask,
                    "stake_usdc": stake,
                    "confidence": round(signal["confidence"], 2),
                    "edge": round(edge, 4),
                    "reason": signal["reason"]
                })

                self.notifier.send(
                    f"✅ 뉴스 베팅\n"
                    f"🟢 예, ${stake:.2f}\n"
                    f"📰 {market.get('question')}\n"
                    f"📂 카테고리: {signal['category']}\n"
                    f"🎯 신뢰도: {round(signal['confidence'] * 100)}%\n"
                    f"📈 edge: {edge:.3f}\n"
                    f"🧠 이유: {signal['reason']}\n"
                    f"🧾 trade_id: {trade['id']}\n"
                    f"응답: {result}"
                )
