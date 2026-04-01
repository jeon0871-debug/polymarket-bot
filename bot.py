import time
from config import CONFIG
from strategy.momentum import momentum_strategy
from strategy.mean_reversion import mean_reversion_strategy
from risk.risk_manager import RiskManager
from utils.market_filter import filter_market

risk = RiskManager(CONFIG)

def get_market_data():
    # 실제 Polymarket API 연결 전 테스트용 데이터
    return {
        "price": 0.52,
        "spread": 0.02,
        "volume": 500,
        "momentum": 0.05
    }

def run():
    while True:
        market = get_market_data()

        if not filter_market(market, CONFIG):
            print("시장 필터 탈락")
            time.sleep(2)
            continue

        signal = None

        if CONFIG["use_momentum"]:
            signal = momentum_strategy(market)

        elif CONFIG["use_mean_reversion"]:
            signal = mean_reversion_strategy(market)

        if signal:
            if risk.can_trade(signal):
                print(f"TRADE 실행: {signal}")
            else:
                print("리스크 제한으로 거래 차단")

        time.sleep(2)

if __name__ == "__main__":
    run()
