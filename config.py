import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_env(name: str, default=None):
    return os.getenv(name, default)

def require_env():
    required = [
        "POLYMARKET_PRIVATE_KEY",
        "POLYMARKET_WALLET",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TRADING_MODE",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"필수 환경변수 누락: {', '.join(missing)}")

def as_bool(name: str, default=False) -> bool:
    value = str(os.getenv(name, str(default))).strip().lower()
    return value in ("1", "true", "yes", "y", "on")

def as_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))

def as_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))

def load_adaptive_config(path: str = "adaptive_config.json") -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_adaptive_config(data: dict, path: str = "adaptive_config.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

TRADING_CONFIG = {
    # 자본
    "capital": 300.0,

    # 리스크
    "risk_per_trade": 0.02,
    "max_total_exposure": 0.35,
    "max_market_exposure": 0.10,
    "max_event_exposure": 0.15,
    "daily_stop_loss": 0.07,
    "max_consecutive_losses": 3,

    # 시장 필터
    "max_spread": 0.03,
    "min_depth": 400,
    "min_trades_15m": 10,
    "min_time_to_expiry_hours": 6,
    "min_market_score": 70,

    # 체결 관련
    "max_slippage": 0.015,
    "reprice_seconds": 20,
    "max_requotes": 2,

    # 전략 ON/OFF
    "use_momentum": True,
    "use_mean_reversion": True,
    "use_market_maker": False,

    # 모멘텀 전략
    "momentum_min_move": 0.04,
    "momentum_min_volume": 300,
    "momentum_min_imbalance": 1.8,

    # 평균회귀 전략
    "meanrev_min_negative_momentum": -0.04,
    "meanrev_deviation_from_mid": 0.05,

    # 메이커 전략
    "maker_min_spread": 0.025,

    # 테스트/운영
    "paper_trading": True
}
