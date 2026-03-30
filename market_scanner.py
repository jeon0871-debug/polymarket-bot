import json
import requests

GAMMA_URL = "https://gamma-api.polymarket.com/markets"

def fetch_active_markets(limit: int = 200):
    params = {"active": "true", "closed": "false", "limit": limit}
    resp = requests.get(GAMMA_URL, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()

def _market_text(market: dict) -> str:
    q = market.get("question", "") or ""
    desc = market.get("description", "") or ""
    return f"{q} {desc}".lower()

def _orderbook_enabled(market: dict) -> bool:
    # 데이터 구조가 바뀌어도 최대한 유연하게 처리
    if "enableOrderBook" in market:
        return bool(market["enableOrderBook"])
    if "enable_order_book" in market:
        return bool(market["enable_order_book"])
    return True

def filter_weather_markets(markets: list):
    keywords = ["weather", "rain", "snow", "storm", "temperature", "hurricane", "heat", "cold", "wind"]
    return [m for m in markets if any(k in _market_text(m) for k in keywords) and _orderbook_enabled(m)]

def filter_news_markets(markets: list):
    keywords = ["election", "president", "fed", "inflation", "tariff", "war", "ceasefire", "policy", "breaking", "court", "rate cut"]
    return [m for m in markets if any(k in _market_text(m) for k in keywords) and _orderbook_enabled(m)]

def get_yes_no_token_ids(market: dict):
    token_ids = market.get("clobTokenIds")
    if isinstance(token_ids, str):
        token_ids = json.loads(token_ids)
    if not token_ids or len(token_ids) < 2:
        raise ValueError("clobTokenIds를 찾지 못했습니다.")
    return token_ids[0], token_ids[1]
