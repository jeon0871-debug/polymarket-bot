def momentum_strategy(market, config):
    momentum = market.get("momentum", 0)
    volume = market.get("volume", 0)

    if momentum > config["momentum_min_move"] and volume > config["momentum_min_volume"]:
        return {
            "strategy": "momentum",
            "action": "BUY"
        }

    return None
