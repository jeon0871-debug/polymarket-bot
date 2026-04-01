def momentum_strategy(market, config):
    """
    모멘텀 전략:
    - 최근 가격 움직임이 강하고
    - 거래량이 충분하고
    - 오더북 불균형이 한쪽으로 쏠릴 때
    """
    momentum = market.get("momentum", 0)
    volume = market.get("volume", 0)
    imbalance = market.get("imbalance", 1)
    spread = market.get("spread", 1)

    if (
        momentum >= config["momentum_min_move"]
        and volume >= config["momentum_min_volume"]
        and imbalance >= config["momentum_min_imbalance"]
        and spread <= config["max_spread"]
    ):
        return {
            "strategy": "momentum",
            "action": "BUY",
            "reason": "강한 모멘텀 + 거래량 증가 + 오더북 불균형",
            "confidence": 82,
            "size_fraction": 0.08
        }

    return None
