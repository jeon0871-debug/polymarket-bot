import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from config import get_env, as_float

CLOB_HOST = "https://clob.polymarket.com"


class OrderEngine:
    def __init__(self):
        self.private_key = get_env("POLYMARKET_PRIVATE_KEY")
        self.wallet = get_env("POLYMARKET_WALLET")
        self.mode = get_env("TRADING_MODE", "paper").lower()
        self.max_order_usdc = as_float("MAX_ORDER_USDC", 3.0)

        if not self.private_key:
            raise ValueError("POLYMARKET_PRIVATE_KEY 환경변수가 없습니다.")

        if not self.wallet:
            raise ValueError("POLYMARKET_WALLET 환경변수가 없습니다.")

        self.client = None

        # live 모드일 때만 실제 CLOB 클라이언트 생성
        if self.mode == "live":
            self.client = ClobClient(
                host=CLOB_HOST,
                chain_id=137,
                key=self.private_key,
                signature_type=1,
                funder=self.wallet,
            )
            self.client.set_api_creds(self.client.create_or_derive_api_creds())

    def get_orderbook(self, token_id: str):
        if not token_id:
            raise ValueError("token_id가 비어 있습니다.")

        resp = requests.get(
            f"{CLOB_HOST}/book",
            params={"token_id": token_id},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    def get_best_prices(self, token_id: str):
        book = self.get_orderbook(token_id)
        bids = book.get("bids", [])
        asks = book.get("asks", [])

        best_bid = float(bids[0]["price"]) if bids else None
        best_ask = float(asks[0]["price"]) if asks else None

        return best_bid, best_ask, book

    def validate_order(self, price: float, size_usdc: float):
        if size_usdc <= 0:
            raise ValueError(f"주문 금액이 0 이하입니다: {size_usdc}")

        if size_usdc > self.max_order_usdc:
            raise ValueError(f"주문 크기 초과: {size_usdc} > {self.max_order_usdc}")

        if not (0.01 <= price <= 0.99):
            raise ValueError(f"비정상 가격: {price}")

    def place_limit_buy(self, token_id: str, price: float, size_usdc: float):
        self.validate_order(price, size_usdc)

        if self.mode != "live":
            return {
                "mode": "paper",
                "side": "BUY",
                "token_id": token_id,
                "price": price,
                "size_usdc": size_usdc,
                "message": "paper 모드이므로 실제 매수 주문 미실행"
            }

        if self.client is None:
            raise RuntimeError("live 모드인데 CLOB client가 초기화되지 않았습니다.")

        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size_usdc,
            side="BUY"
        )

        signed_order = self.client.create_order(order_args)
        result = self.client.post_order(signed_order, OrderType.GTC)

        return {
            "mode": "live",
            "side": "BUY",
            "token_id": token_id,
            "price": price,
            "size_usdc": size_usdc,
            "result": result
        }

    def place_limit_sell(self, token_id: str, price: float, size_usdc: float):
        self.validate_order(price, size_usdc)

        if self.mode != "live":
            return {
                "mode": "paper",
                "side": "SELL",
                "token_id": token_id,
                "price": price,
                "size_usdc": size_usdc,
                "message": "paper 모드이므로 실제 매도 주문 미실행"
            }

        if self.client is None:
            raise RuntimeError("live 모드인데 CLOB client가 초기화되지 않았습니다.")

        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size_usdc,
            side="SELL"
        )

        signed_order = self.client.create_order(order_args)
        result = self.client.post_order(signed_order, OrderType.GTC)

        return {
            "mode": "live",
            "side": "SELL",
            "token_id": token_id,
            "price": price,
            "size_usdc": size_usdc,
            "result": result
        }
