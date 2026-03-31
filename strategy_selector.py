from config import load_adaptive_config, save_adaptive_config
from performance_analyzer import analyze_performance

def update_strategy_selection():
    cfg = load_adaptive_config()
    summary = analyze_performance()

    min_trades = int(cfg.get("strategy_min_trades", 5))
    disable_pnl_threshold = float(cfg.get("strategy_disable_pnl_threshold", -5.0))
    reenable_pnl_threshold = float(cfg.get("strategy_reenable_pnl_threshold", 5.0))

    enabled = cfg.get("enabled_strategies", {
        "weather": True,
        "news": True
    })

    by_strategy = summary.get("by_strategy", {})

    for strategy_name in ["weather", "news"]:
        stats = by_strategy.get(strategy_name, None)
        if not stats:
            continue

        count = int(stats.get("count", 0))
        total_pnl = float(stats.get("total_pnl", 0.0))

        if count >= min_trades and total_pnl <= disable_pnl_threshold:
            enabled[strategy_name] = False

        if count >= min_trades and total_pnl >= reenable_pnl_threshold:
            enabled[strategy_name] = True

    cfg["enabled_strategies"] = enabled

    by_category = summary.get("by_category", {})
    new_blocked = []

    for category, stats in by_category.items():
        count = int(stats.get("count", 0))
        total_pnl = float(stats.get("total_pnl", 0.0))

        if count >= min_trades and total_pnl <= disable_pnl_threshold:
            new_blocked.append(category)

    cfg["blocked_categories"] = sorted(list(set(new_blocked)))
    save_adaptive_config(cfg)
    return cfg
