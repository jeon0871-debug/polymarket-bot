class RiskManager:
    def __init__(self, config):
        self.config = config
        self.daily_loss_ratio = 0.0
        self.total_exposure_ratio = 0.0

    def can_trade(self, signal):
        size = signal.get("size_fraction", 0)

        if self.daily_loss_ratio >= self.config["daily_stop_loss"]:
            return False

        if self.total_exposure_ratio + size > self.config["max_total_exposure"]:
            return False

        return True

    def register_open_exposure(self, signal):
        size = signal.get("size_fraction", 0)
        self.total_exposure_ratio += size
