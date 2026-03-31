import json
import os
from performance_analyzer import analyze_performance

CONFIG_FILE = os.getenv("ADAPTIVE_CONFIG_FILE", "adaptive_config.json")

def load_adaptive_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "min_confidence": 0.70,
            "max_order_usdc": 3.0,
            "weather_edge_threshold": 0.05,
            "news_edge_threshold": 0.05,
            "category_weights": {},
            "blocked_keywords": [],
        }
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_adaptive_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def tune_config():
    cfg = load_adaptive_config()
    perf = analyze_performance()

    if perf["count"] < 10:
        return cfg, {"changed": False, "reason": "데이터 부족"}

    if perf["win_rate"] < 0.45:
        cfg["min_confidence"] = min(0.90, round(cfg.get("min_confidence", 0.70) + 0.02, 2))
    elif perf["win_rate"] > 0.60:
        cfg["min_confidence"] = max(0.55, round(cfg.get("min_confidence", 0.70) - 0.01, 2))

    category_weights = cfg.get("category_weights", {})
    for category, stats in perf["by_category"].items():
        weight = category_weights.get(category, 1.0)
        if stats["count"] >= 5:
            if stats["win_rate"] < 0.40:
                weight = max(0.5, round(weight - 0.05, 2))
            elif stats["win_rate"] > 0.60:
                weight = min(1.5, round(weight + 0.05, 2))
        category_weights[category] = weight

    cfg["category_weights"] = category_weights
    save_adaptive_config(cfg)
    return cfg, {"changed": True, "reason": "성과 기반 파라미터 조정 완료"}
