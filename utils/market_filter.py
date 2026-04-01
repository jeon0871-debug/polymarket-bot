def evaluate_market(market, config):
    score = 100

    if market["spread"] > config["max_spread"]:
        score -= 30

    if market["depth"] < config["min_depth"]:
        score -= 20

    if market["trades_15m"] < config["min_trades_15m"]:
        score -= 20

    passed = score >= config["min_market_score"]
    return passed, score
