from performance_analyzer import analyze_performance

def build_daily_report():
    perf = analyze_performance()

    if perf["count"] == 0:
        return "📊 오늘의 성과 리포트\n기록된 paper trade가 아직 없습니다."

    lines = [
        "📊 오늘의 성과 리포트",
        f"총 거래수: {perf['count']}",
        f"전체 승률: {perf['win_rate'] * 100:.1f}%",
        f"평균 PnL: {perf['avg_pnl']:.2f}",
        "",
        "📁 카테고리별 성과"
    ]

    for category, stats in sorted(perf["by_category"].items()):
        lines.append(
            f"- {category}: 거래 {stats['count']} | 승률 {stats['win_rate'] * 100:.1f}% | 평균PnL {stats['avg_pnl']:.2f}"
        )

    lines.append("")
    lines.append("🧠 전략별 성과")

    for strategy, stats in sorted(perf["by_strategy"].items()):
        lines.append(
            f"- {strategy}: 거래 {stats['count']} | 승률 {stats['win_rate'] * 100:.1f}% | 평균PnL {stats['avg_pnl']:.2f}"
        )

    return "\n".join(lines)
