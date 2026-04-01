import time
from config import TRADING_CONFIG, require_env
from strategy.momentum import momentum_strategy
from strategy.mean_reversion import mean_reversion_strategy
from strategy.market_maker import market_maker_strategy
from risk.risk_manager import RiskManager
from utils.market_filter import evaluate_market

risk = RiskManager(TRADING_CONFIG)

def get_market_data():
    """
    현재는 테스트용 더미 데이터.
    나중에 Polymarket API / WebSocket 연결 시 이 부분만 교체하면 됨.
    """
    return {
        "market_id": "test_market_1",
        "event_id": "test_event_1",
        "price": 0.52,
        "mid_price": 0.50,
        "spread": 0.02,
        "volume": 500,
        "depth": 700,
        "momentum": 0.05,
        "imbalance": 2.1,
        "trades_15m": 14,
        "time_to_expiry_hours": 12,
        "expected_slippage": 0.008
    }

def build_signal(market, config):
    if config["use_momentum"]:
        signal = momentum_strategy(market, config)
        if signal:
            return signal

    if config["use_mean_reversion"]:
        signal = mean_reversion_strategy(market, config)
        if signal:
            return signal

    if config["use_market_maker"]:
        signal = market_maker_strategy(market, config)
        if signal:
            return signal

    return None

def execute_trade(signal):
    """
    현재는 테스트용 출력만 수행.
    실제 주문 API 연결 시 이 부분만 교체하면 됨.
    """
    print(f"[거래 실행] {signal}")

def run():
    while True:
        market = get_market_data()

        passed, score, reasons = evaluate_market(market, TRADING_CONFIG)

        if not passed:
            print(f"[시장 탈락] score={score}, reasons={reasons}")
            time.sleep(2)
            continue

        signal = build_signal(market, TRADING_CONFIG)

        if not signal:
            print("[신호 없음]")
            time.sleep(2)
            continue

        signal["market_score"] = score
        signal["market_id"] = market["market_id"]
        signal["event_id"] = market["event_id"]

        if risk.can_trade(signal):
            execute_trade(signal)
            risk.register_open_exposure(signal)
        else:
            print("[거래 차단] 리스크 조건 불충족")

        time.sleep(2)

if __name__ == "__main__":
    require_env()
    run()
