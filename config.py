[config.py](https://github.com/user-attachments/files/26362821/config.py)
[config.py](https://github.com/user-attachments/files/26362821/config.py)
import os
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
