class RiskManager:
    def __init__(self, config):
        self.config = config
        self.daily_loss_ratio = 0.0
        self.consecutive_losses = 0
        self.total_exposure_ratio = 0.0
        self.market_exposures = {}
        self.event_exposures = {}

    def can_trade(self, signal: dict) -> bool:
        market_id = signal.get("market_id")
        event_id = signal.get("event_id")
        size_fraction = signal.get("size_fraction", 0)

        if self.daily_loss_ratio >= self.config["daily_stop_loss"]:
            return False

        if self.consecutive_losses >= self.config["max_consecutive_losses"]:
            return False

        if self.total_exposure_ratio + size_fraction > self.config["max_total_exposure"]:
            return False

        current_market_exposure = self.market_exposures.get(market_id, 0.0)
        if current_market_exposure + size_fraction > self.config["max_market_exposure"]:
            return False

        current_event_exposure = self.event_exposures.get(event_id, 0.0)
        if current_event_exposure + size_fraction > self.config["max_event_exposure"]:
            return False

        return True

    def register_open_exposure(self, signal: dict):
        market_id = signal.get("market_id")
        event_id = signal.get("event_id")
        size_fraction = signal.get("size_fraction", 0)

        self.total_exposure_ratio += size_fraction
        self.market_exposures[market_id] = self.market_exposures.get(market_id, 0.0) + size_fraction
        self.event_exposures[event_id] = self.event_exposures.get(event_id, 0.0) + size_fraction

    def register_close_result(self, pnl_ratio: float, signal: dict):
        market_id = signal.get("market_id")
        event_id = signal.get("event_id")
        size_fraction = signal.get("size_fraction", 0)

        self.total_exposure_ratio = max(0.0, self.total_exposure_ratio - size_fraction)
        self.market_exposures[market_id] = max(
            0.0,
            self.market_exposures.get(market_id, 0.0) - size_fraction
        )
        self.event_exposures[event_id] = max(
            0.0,
            self.event_exposures.get(event_id, 0.0) - size_fraction
        )

        if pnl_ratio < 0:
            self.daily_loss_ratio += abs(pnl_ratio)
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
