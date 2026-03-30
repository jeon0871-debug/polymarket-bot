import requests

def check_geoblock():
    url = "https://polymarket.com/api/geoblock"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("blocked"):
        raise RuntimeError(f"Geoblock 차단: {data}")

    return data
