[README_UPGRADE.md](https://github.com/user-attachments/files/26390685/README_UPGRADE.md)
# 업그레이드 추가 파일 사용법

## 추가된 파일
- adaptive_config.json
- paper_trade_logger.py
- performance_analyzer.py
- self_tuner.py
- telegram_reporter.py
- live_guard.py

## 목적
1. paper trade 결과 저장
2. 성과 분석
3. 자동 파라미터 조정
4. 텔레그램 일일 리포트
5. live 모드 보호

## master_bot.py 에 추가할 import

```python
from self_tuner import tune_config
from telegram_reporter import build_daily_report
```

## 루프 안에서 주기적 튜닝/리포트 예시

```python
last_tune_ts = 0
last_report_ts = 0
```

```python
now = time.time()

if now - last_tune_ts > 3600:
    cfg, result = tune_config()
    notifier.send(f"자가개선 결과: {result} | min_confidence={cfg.get('min_confidence')}")
    last_tune_ts = now

if now - last_report_ts > 21600:
    notifier.send(build_daily_report())
    last_report_ts = now
```

## news_strategy.py 예시 수정 포인트

```python
from self_tuner import load_adaptive_config
from paper_trade_logger import log_paper_trade
```

```python
cfg = load_adaptive_config()
min_conf = cfg.get("min_confidence", 0.70)
news_edge_threshold = cfg.get("news_edge_threshold", 0.05)
category_weights = cfg.get("category_weights", {})
blocked_keywords = cfg.get("blocked_keywords", [])
```

```python
q = market.get("question", "").lower()
if any(k.lower() in q for k in blocked_keywords):
    continue
```

```python
def detect_category(text: str) -> str:
    text = text.lower()
    if "war" in text or "ceasefire" in text or "ukraine" in text or "russia" in text:
        return "war"
    if "election" in text or "president" in text or "trump" in text:
        return "election"
    if "bitcoin" in text or "btc" in text:
        return "bitcoin"
    if "inflation" in text or "fed" in text:
        return "macro"
    return "other"
```

## weather_strategy.py 예시 수정 포인트

```python
from self_tuner import load_adaptive_config
from paper_trade_logger import log_paper_trade
```

```python
cfg = load_adaptive_config()
edge_threshold = cfg.get("weather_edge_threshold", 0.05)
```

## 실거래 보호
실거래 켤 때는 `live_guard.py`를 사용하세요.

```python
from live_guard import ensure_live_trading_allowed
live_status = ensure_live_trading_allowed()
```
