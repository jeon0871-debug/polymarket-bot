from performance_analyzer import analyze_performance
from config import load_adaptive_config

def build_daily_report(notifier):
    summary = analyze_performance()
    cfg = load_adaptive_config()

    by_category = summary.get("by_category", {})
    if by_category:
        top = sorted(by_category.items(), key=lambda x: x[1]["total_pnl"], reverse=True)[:3]
        bottom = sorted(by_category.items(), key=lambda x: x[1]["total_pnl"])[:3]
        top_text = "\n".join([f"- {k}: pnl {v['total_pnl']}, win {v['win_rate']:.0%}" for k, v in top])
        bottom_text = "\n".join([f"- {k}: pnl {v['total_pnl']}, win {v['win_rate']:.0%}" for k, v in bottom])
    else:
        top_text = "없음"
        bottom_text = "없음"

    text = (
        f"📊 일일 리포트\n"
        f"총 종료 거래: {summary['total_closed']}\n"
        f"총 PnL: {summary['total_pnl']:+.2f}\n"
        f"승률: {summary['win_rate']:.0%}\n"
        f"평균 PnL: {summary['avg_pnl']:+.2f}\n\n"
        f"상위 카테고리:\n{top_text}\n\n"
        f"하위 카테고리:\n{bottom_text}\n\n"
        f"현재 설정:\n"
        f"- min_confidence: {cfg.get('min_confidence')}\n"
        f"- max_order_usdc: {cfg.get('max_order_usdc')}"
    )

    notifier.send(text)
