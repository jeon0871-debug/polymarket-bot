from self_tuner import tune_config
from telegram_reporter import build_daily_report

import time
import logging

from config import require_env, get_env, as_bool, as_float, as_int
from geo_check import check_geoblock
from notifier import TelegramNotifier
from order_engine import OrderEngine
from risk_manager import RiskManager
from weather_strategy import WeatherStrategy
from news_strategy import NewsStrategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def main(last_tune_ts = 0
last_report_ts = 0):
    require_env()

    notifier = TelegramNotifier(
        token=get_env("TELEGRAM_BOT_TOKEN"),
        chat_id=get_env("TELEGRAM_CHAT_ID")
    )

    geo = check_geoblock()
    logging.info(f"Geoblock result: {geo}")
    notifier.send(f"봇 시작 | mode={get_env('TRADING_MODE')} | geo={geo}")

    order_engine = OrderEngine()

    risk_manager = RiskManager(
        max_daily_loss=as_float("MAX_DAILY_LOSS", 20),
        max_open_positions=as_int("MAX_OPEN_POSITIONS", 3),
        cooldown_sec=as_int("ENTRY_COOLDOWN_SEC", 900),
    )

    weather_strategy = WeatherStrategy(order_engine, risk_manager, notifier)
    news_strategy = NewsStrategy(order_engine, risk_manager, notifier)

    weather_enabled = as_bool("WEATHER_ENABLED", True)
    news_enabled = as_bool("NEWS_ENABLED", True)

    while True:
        try:
            geo = check_geoblock()
            logging.info(f"Loop geoblock result: {geo}")

            if weather_enabled:
                logging.info("Running weather cycle")
                weather_strategy.run_cycle()

            time.sleep(60)

            if news_enabled:
                logging.info("Running news cycle")
                news_strategy.run_cycle()
                tune_config()
            time.sleep(180)

        except Exception as e:
            logging.exception("Bot loop error")
            notifier.send(f"오류 발생: {e}")
            time.sleep(60)
             build_daily_report

if __name__ == "__main__":
    main()
