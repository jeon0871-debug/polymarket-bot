def mean_reversion_strategy(market, config):
    """
    평균회귀 전략:
    - 과도하게 눌린 가격이
    - 중간값 방향으로 되돌아올 가능성을 노림
    """
    momentum = market.get("momentum", 0)
    price = market.get("price", 0)
    mid_price = market.get("mid_price", 0)

    if mid_price <= 0:
        return None

    deviation = mid_price - price

    if (
        momentum <= config["meanrev_min_negative_momentum"]
        and deviation >= config["meanrev_deviation_from_mid"]
    ):
        return {
            "strategy": "mean_reversion",
            "action": "BUY",
            "reason": "과매도 후 평균회귀 가능성",
            "confidence": 74,
            "size_fraction": 0.06
        }

    return None
