import os
import logging
import requests


def check_geoblock() -> dict:
    url = "https://polymarket.com/api/geoblock"
    mode = os.getenv("TRADING_MODE", "paper").lower()

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        result = {
            "ok": True,
            "blocked": data.get("blocked", False),
            "country": data.get("country"),
            "region": data.get("region"),
            "ip": data.get("ip"),
            "mode": mode,
            "raw": data,
        }

        if result["blocked"]:
            if mode == "live":
                logging.warning(
                    f"[LIVE MODE] Geoblock 차단 감지 | "
                    f"country={result['country']} region={result['region']} ip={result['ip']}"
                )
            else:
                logging.warning(
                    f"[PAPER MODE] Geoblock 차단 감지 | "
                    f"country={result['country']} region={result['region']} ip={result['ip']}"
                )
        else:
            logging.info(
                f"Geoblock 허용 상태 | "
                f"country={result['country']} region={result['region']} ip={result['ip']}"
            )

        return result

    except Exception as e:
        logging.exception(f"Geoblock 확인 실패: {e}")
        return {
            "ok": False,
            "blocked": True,
            "country": None,
            "region": None,
            "ip": None,
            "mode": mode,
            "error": str(e),
            "raw": None,
        }
