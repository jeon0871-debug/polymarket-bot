from config import load_adaptive_config, save_adaptive_config
from performance_analyzer import analyze_performance

def tune_config():
    cfg = load_adaptive_config()
    summary = analyze_performance()

    if summary["total_closed"] < 10:
        return cfg

    min_conf = float(cfg.get("min_confidence", 0.7))
    max_order = float(cfg.get("max_order_usdc", 3.0))

    win_rate = float(summary.get("win_rate", 0.0))
    total_pnl = float(summary.get("total_pnl", 0.0))

    # 아주 보수적인 자동 조정
    if win_rate < 0.45 or total_pnl < 0:
        min_conf = min(0.9, round(min_conf + 0.02, 2))
        max_order = max(1.0, round(max_order - 0.5, 2))

    elif win_rate > 0.60 and total_pnl > 0:
        min_conf = max(0.55, round(min_conf - 0.01, 2))
        max_order = min(5.0, round(max_order + 0.25, 2))

    cfg["min_confidence"] = min_conf
    cfg["max_order_usdc"] = max_order

    save_adaptive_config(cfg)
    return cfg
