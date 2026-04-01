import timeraise Exception("STOP")
import logging
from datetime import datetime, timezone

from config import require_env, get_env, as_float, as_int, load_adaptive_config
from geo_check import check_geoblock
from notifier import TelegramNotifier
from order_engine import OrderEngine
from risk_manager import RiskManager
from weather_strategy import WeatherStrategy
from news_strategy import NewsStrategy
from paper_trade_updater import update_paper_trades
from performance_analyzer import analyze_and_save
from self_tuner import tune_config
from telegram_reporter import build_daily_report
from strategy_selector import update_strategy_selection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def should_send_daily_report(last_report_day, hour_utc):
    now = datetime.now(timezone.utc)
    current_day = now.strftime("%Y-%m-%d")
    return now.hour >= hour_utc and last_report_day != current_day, current_day

def main():
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

    last_report_day = None

    while True:
        try:
            geo = check_geoblock()
            logging.info(f"Loop geoblock result: {geo}")

            cfg = load_adaptive_config()
            enabled_strategies = cfg.get("enabled_strategies", {
                "weather": True,
                "news": True
            })
            daily_report_hour_utc = int(cfg.get("daily_report_hour_utc", 1))

            update_paper_trades(order_engine, notifier)

            if enabled_strategies.get("weather", True):
                logging.info("Running weather cycle")
                weather_strategy.run_cycle()
            else:
                logging.info("Weather strategy disabled by performance filter")

            time.sleep(60)

            if enabled_strategies.get("news", True):
                logging.info("Running news cycle")
                news_strategy.run_cycle()
            else:
                logging.info("News strategy disabled by performance filter")

            summary = analyze_and_save()
            logging.info(f"Performance summary: {summary}")

            new_cfg = tune_config()
            logging.info(f"Tuned config: {new_cfg}")

            updated_cfg = update_strategy_selection()
            logging.info(f"Strategy selection updated: {updated_cfg.get('enabled_strategies')}")

            send_now, current_day = should_send_daily_report(last_report_day, daily_report_hour_utc)
            if send_now:
                build_daily_report(notifier)
                last_report_day = current_day

            time.sleep(180)

        except Exception as e:
            logging.exception("Bot loop error")
            notifier.send(f"오류 발생: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
