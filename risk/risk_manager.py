import time


class RiskManager:
    def __init__(
        self,
        max_daily_loss: float,
        max_open_positions: int,
        cooldown_sec: int,
        max_total_exposure: float = 0.35,
        max_market_exposure: float = 0.10,
        max_event_exposure: float = 0.15,
        max_consecutive_losses: int = 3,
    ):
        self.max_daily_loss = max_daily_loss
        self.max_open_positions = max_open_positions
        self.cooldown_sec = cooldown_sec

        self.max_total_exposure = max_total_exposure
        self.max_market_exposure = max_market_exposure
        self.max_event_exposure = max_event_exposure
        self.max_consecutive_losses = max_consecutive_losses

        self.daily_loss_amount = 0.0
        self.consecutive_losses = 0
        self.total_exposure_ratio = 0.0

        self.market_exposures = {}
        self.event_exposures = {}

        self.open_positions = 0
        self.last_entry_time = 0

    def can_trade(self, signal: dict) -> bool:
        market_id = signal.get("market_id")
        event_id = signal.get("event_id")
        size_fraction = signal.get("size_fraction", 0)

        now = time.time()

        # 1) 일일 손실 제한
        if self.daily_loss_amount >= self.max_daily_loss:
            return False

        # 2) 연속 손실 제한
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False

        # 3) 쿨다운 제한
        if now - self.last_entry_time < self.cooldown_sec:
            return False

        # 4) 열린 포지션 수 제한
        if self.open_positions >= self.max_open_positions:
            return False

        # 5) 총 노출 제한
        if self.total_exposure_ratio + size_fraction > self.max_total_exposure:
            return False

        # 6) 시장별 노출 제한
        current_market_exposure = self.market_exposures.get(market_id, 0.0)
        if current_market_exposure + size_fraction > self.max_market_exposure:
            return False

        # 7) 이벤트별 노출 제한
        current_event_exposure = self.event_exposures.get(event_id, 0.0)
        if current_event_exposure + size_fraction > self.max_event_exposure:
            return False

        return True

    def register_open_exposure(self, signal: dict):
        market_id = signal.get("market_id")
        event_id = signal.get("event_id")
        size_fraction = signal.get("size_fraction", 0)

        self.total_exposure_ratio += size_fraction
        self.market_exposures[market_id] = self.market_exposures.get(market_id, 0.0) + size_fraction
        self.event_exposures[event_id] = self.event_exposures.get(event_id, 0.0) + size_fraction

        self.open_positions += 1
        self.last_entry_time = time.time()

    def register_close_result(self, pnl_amount: float, signal: dict):
        """
        pnl_amount 기준:
        +3.5 = +3.5달러 이익
        -2.0 = -2달러 손실
        """
        market_id = signal.get("market_id")
        event_id = signal.get("event_id")
        size_fraction = signal.get("size_fraction", 0)

        # 노출 감소
        self.total_exposure_ratio = max(0.0, self.total_exposure_ratio - size_fraction)
        self.market_exposures[market_id] = max(
            0.0,
            self.market_exposures.get(market_id, 0.0) - size_fraction
        )
        self.event_exposures[event_id] = max(
            0.0,
            self.event_exposures.get(event_id, 0.0) - size_fraction
        )

        # 열린 포지션 감소
        self.open_positions = max(0, self.open_positions - 1)

        # 손익 반영
        if pnl_amount < 0:
            self.daily_loss_amount += abs(pnl_amount)
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def reset_daily_stats(self):
        self.daily_loss_amount = 0.0
        self.consecutive_losses = 0
