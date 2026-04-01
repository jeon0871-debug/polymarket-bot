import time
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

def safe_notify(notifier, message: str):
    try:
        if notifier:
            notifier.send(message)
    except Exception:
        logging.exception("텔레그램 알림 전송 실패")

def should_send_daily_report(last_report_day, hour_utc):
    now = datetime.now(timezone.utc)
    current_day = now.strftime("%Y-%m-%d")
    return now.hour >= hour_utc and last_report_day != current_day, current_day

def is_geo_blocked(geo_result):
    """
    geo_check.py 반환값이 dict / bool / 문자열일 가능성에 대비
    """
    if isinstance(geo_result, dict):
        return geo_result.get("blocked", False)
    if isinstance(geo_result, bool):
        return geo_result
    if isinstance(geo_result, str):
        lower = geo_result.lower()
        return "blocked" in lower or "denied" in lower or "restricted" in lower
    return False

def main():
    require_env()

    notifier = None
    order_engine = None

    try:
        notifier = TelegramNotifier(
            token=get_env("TELEGRAM_BOT_TOKEN"),
            chat_id=get_env("TELEGRAM_CHAT_ID")
        )
    except Exception:
        logging.exception("TelegramNotifier 초기화 실패")

    try:
        geo = check_geoblock()
        logging.info(f"Geoblock result: {geo}")
        safe_notify(notifier, f"봇 시작 | mode={get_env('TRADING_MODE')} | geo={geo}")
    except Exception:
        logging.exception("초기 geoblock 확인 실패")
        safe_notify(notifier, "초기 geoblock 확인 실패")

    try:
        order_engine = OrderEngine()
    except Exception as e:
        logging.exception("OrderEngine 초기화 실패")
        safe_notify(notifier, f"OrderEngine 초기화 실패: {e}")
        raise

    risk_manager = RiskManager(
        max_daily_loss=as_float("MAX_DAILY_LOSS", 20),
        max_open_positions=as_int("MAX_OPEN_POSITIONS", 3),
        cooldown_sec=as_int("ENTRY_COOLDOWN_SEC", 900),
    )

    weather_strategy = WeatherStrategy(order_engine, risk_manager, notifier)
    news_strategy = NewsStrategy(order_engine, risk_manager, notifier)

    last_report_day = None
    last_analysis_ts = 0
    analysis_interval_sec = as_int("ANALYSIS_INTERVAL_SEC", 1800)  # 30분

    while True:
        try:
            geo = check_geoblock()
            logging.info(f"Loop geoblock result: {geo}")

            if is_geo_blocked(geo):
                logging.warning("지리 제한 감지 - 거래 루프 일시 중지")
                safe_notify(notifier, f"지리 제한 감지로 거래 일시 중지 | geo={geo}")
                time.sleep(300)
                continue

            cfg = load_adaptive_config()
            if not isinstance(cfg, dict):
                cfg = {}

            enabled_strategies = cfg.get("enabled_strategies", {
                "weather": True,
                "news": True
            })

            try:
                daily_report_hour_utc = int(cfg.get("daily_report_hour_utc", 1))
            except Exception:
                daily_report_hour_utc = 1

            # paper 트레이드 정리/업데이트
            try:
                update_paper_trades(order_engine, notifier)
            except Exception:
                logging.exception("paper trade 업데이트 실패")

            # weather 전략
            if enabled_strategies.get("weather", True):
                logging.info("Running weather cycle")
                try:
                    weather_strategy.run_cycle()
                except Exception:
                    logging.exception("Weather strategy 실행 실패")
            else:
                logging.info("Weather strategy disabled by performance filter")

            time.sleep(60)

            # news 전략
            if enabled_strategies.get("news", True):
                logging.info("Running news cycle")
                try:
                    news_strategy.run_cycle()
                except Exception:
                    logging.exception("News strategy 실행 실패")
            else:
                logging.info("News strategy disabled by performance filter")

            # 분석/튜닝은 너무 자주 하지 않도록 간격 적용
            now_ts = time.time()
            if now_ts - last_analysis_ts >= analysis_interval_sec:
                try:
                    summary = analyze_and_save()
                    logging.info(f"Performance summary: {summary}")
                except Exception:
                    logging.exception("성과 분석 실패")

                try:
                    new_cfg = tune_config()
                    logging.info(f"Tuned config: {new_cfg}")
                except Exception:
                    logging.exception("자동 튜닝 실패")

                try:
                    updated_cfg = update_strategy_selection()
                    logging.info(
                        f"Strategy selection updated: "
                        f"{updated_cfg.get('enabled_strategies') if isinstance(updated_cfg, dict) else updated_cfg}"
                    )
                except Exception:
                    logging.exception("전략 선택 업데이트 실패")

                last_analysis_ts = now_ts

            # 일일 리포트
            send_now, current_day = should_send_daily_report(last_report_day, daily_report_hour_utc)
            if send_now:
                try:
                    build_daily_report(notifier)
                    last_report_day = current_day
                except Exception:
                    logging.exception("일일 리포트 전송 실패")

            time.sleep(180)

        except Exception as e:
            logging.exception("Bot loop error")
            safe_notify(notifier, f"오류 발생: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
