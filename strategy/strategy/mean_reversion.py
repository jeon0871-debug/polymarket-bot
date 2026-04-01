def mean_reversion_strategy(market, config):
    momentum = market.get("momentum", 0)

    if momentum < config["meanrev_min_negative_momentum"]:
        return {
            "strategy": "mean_reversion",
            "action": "BUY"
        }

    return None
