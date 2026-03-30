import requests

def check_geoblock() -> dict:
    url = "https://polymarket.com/api/geoblock"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("blocked") is True:
        raise RuntimeError(
            f"Geoblock 차단 상태: country={data.get('country')} region={data.get('region')} ip={data.get('ip')}"
        )
    return data
