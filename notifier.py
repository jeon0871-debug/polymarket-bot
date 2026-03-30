import requests

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send(self, text):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text[:4000]}
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            pass
