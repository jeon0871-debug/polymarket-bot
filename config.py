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

RADING_CONFIG = {
    "capital": 300,

    "risk_per_trade": 0.02,
    "max_total_exposure": 0.35,
    "daily_stop_loss": 0.07,

    "max_spread": 0.03,
    "min_depth": 400,
    "min_trades_15m": 10,

    "max_slippage": 0.015,
    "reprice_seconds": 20,

    "use_momentum": True,
    "use_mean_reversion": True,
    "use_market_maker": False
}
