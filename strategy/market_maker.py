def market_maker_strategy(market, config):
    """
    메이커 전략:
    - 스프레드가 충분히 넓고
    - 방향성이 강하지 않으며
    - 오더북 깊이가 어느 정도 있을 때
    """
    spread = market.get("spread", 0)
    momentum = abs(market.get("momentum", 0))
    depth = market.get("depth", 0)

    if (
        spread >= config["maker_min_spread"]
        and momentum < 0.02
        and depth >= config["min_depth"]
    ):
        return {
            "strategy": "market_maker",
            "action": "QUOTE_BOTH",
            "reason": "스프레드 수취 가능 구간",
            "confidence": 68,
            "size_fraction": 0.04
        }

    return None
