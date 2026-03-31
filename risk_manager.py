import time

class RiskManager:
    def __init__(self, max_daily_loss: float, max_open_positions: int, cooldown_sec: int = 900):
        self.max_daily_loss = abs(max_daily_loss)
        self.max_open_positions = max_open_positions
        self.cooldown_sec = cooldown_sec
        self.daily_pnl = 0.0
        self.open_markets = set()
        self.recent_entries = {}

    def can_enter(self, market_id: str) -> bool:
        if self.daily_pnl <= -self.max_daily_loss:
            return False

        if len(self.open_markets) >= self.max_open_positions:
            return False

        last = self.recent_entries.get(market_id)
        if last and (time.time() - last < self.cooldown_sec):
            return False

        return True

    def mark_enter(self, market_id: str):
        self.open_markets.add(market_id)
        self.recent_entries[market_id] = time.time()

    def mark_exit(self, market_id: str, pnl: float = 0.0):
        if market_id in self.open_markets:
            self.open_markets.remove(market_id)
        self.daily_pnl += pnl
