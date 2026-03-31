import os
import requests

def check_geoblock() -> dict:
    url = "https://polymarket.com/api/geoblock"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    blocked = data.get("blocked", False)
    mode = os.getenv("TRADING_MODE", "paper").lower()

    # live 모드에서는 차단 상태면 즉시 종료
    if blocked and mode == "live":
        raise RuntimeError(
            f"Geoblock 차단 상태: country={data.get('country')} "
            f"region={data.get('region')} ip={data.get('ip')}"
        )

    # paper 모드에서는 경고만 남기고 계속 진행
    if blocked and mode != "live":
        print(
            f"[PAPER MODE] Geoblock 차단 감지: "
            f"country={data.get('country')} "
            f"region={data.get('region')} "
            f"ip={data.get('ip')}"
        )

    return data
