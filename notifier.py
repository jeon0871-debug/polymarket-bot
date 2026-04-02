import logging
import requests


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN 값이 비어 있습니다.")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID 값이 비어 있습니다.")

        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send(self, text: str, parse_mode: str = None) -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": str(text)[:4000],
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            resp = requests.post(url, json=payload, timeout=10)

            if resp.status_code != 200:
                logging.error(
                    f"Telegram 전송 실패 | status={resp.status_code} | body={resp.text}"
                )
                return False

            return True

        except Exception as e:
            logging.exception(f"Telegram 요청 예외 발생: {e}")
            return False
