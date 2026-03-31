from config import get_env
from geo_check import check_geoblock

def ensure_live_trading_allowed():
    mode = get_env("TRADING_MODE", "paper").lower()
    if mode != "live":
        return {"allowed": False, "reason": "paper mode"}

    geo = check_geoblock()
    if geo.get("blocked"):
        raise RuntimeError(
            f"실거래 불가 지역: country={geo.get('country')} region={geo.get('region')} ip={geo.get('ip')}"
        )
    return {"allowed": True, "reason": "live mode allowed", "geo": geo}
