def evaluate_market(market, config):
    """
    시장 품질을 점수화해서 진입 가능 여부 판단
    """
    score = 100
    reasons = []

    spread = market.get("spread", 999)
    depth = market.get("depth", 0)
    trades_15m = market.get("trades_15m", 0)
    expiry_hours = market.get("time_to_expiry_hours", 0)
    expected_slippage = market.get("expected_slippage", 999)

    if spread > config["max_spread"]:
        score -= 30
        reasons.append("스프레드 과다")

    if depth < config["min_depth"]:
        score -= 20
        reasons.append("호가 깊이 부족")

    if trades_15m < config["min_trades_15m"]:
        score -= 20
        reasons.append("최근 체결 부족")

    if expiry_hours < config["min_time_to_expiry_hours"]:
        score -= 15
        reasons.append("종료 임박 시장")

    if expected_slippage > config["max_slippage"]:
        score -= 25
        reasons.append("예상 슬리피지 과다")

    passed = score >= config["min_market_score"]
    return passed, score, reasons
