"""
Polymarket 실제 주문 모듈 v13
httpx 0.28+ proxy 파라미터 사용
"""
import os, json, requests
from datetime import datetime

def load_env():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

PRIVATE_KEY  = os.environ.get('POLYMARKET_PRIVATE_KEY', '')
WALLET       = os.environ.get('POLYMARKET_WALLET', '')
TRADING_MODE = os.environ.get('TRADING_MODE', 'paper')
PROXY_URL    = os.environ.get('PROXY_URL', '')

PROXIES = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else {}

def patch_httpx_with_proxy():
    """httpx 0.28+ proxy 파라미터로 클라이언트 교체"""
    if not PROXY_URL:
        return False
    try:
        import httpx
        import py_clob_client.http_helpers.helpers as helpers

        # httpx 0.28+는 proxy= 파라미터 사용
        proxy_client = httpx.Client(
            http2=True,
            proxy=PROXY_URL,
            timeout=30.0,
        )
        helpers._http_client = proxy_client
        print(f"  🌍 httpx 프록시 주입 완료!")
        return True
    except Exception as e:
        print(f"  ⚠️  httpx 오류: {e}")
        # 대안: mounts 방식
        try:
            import httpx
            import py_clob_client.http_helpers.helpers as helpers

            transport = httpx.HTTPTransport(proxy=PROXY_URL)
            proxy_client = httpx.Client(
                http2=False,
                transport=transport,
                timeout=30.0,
            )
            helpers._http_client = proxy_client
            print(f"  🌍 httpx transport 프록시 주입 완료!")
            return True
        except Exception as e2:
            print(f"  ❌ 프록시 주입 완전 실패: {e2}")
            return False

_client = None

def get_client():
    global _client
    if _client: return _client
    if not PRIVATE_KEY:
        print("  ⚠️  PRIVATE_KEY 없음")
        return None
    try:
        patch_httpx_with_proxy()

        from py_clob_client.client import ClobClient
        _client = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=137,
            key=PRIVATE_KEY,
            signature_type=1,
            funder=WALLET,
        )
        _client.set_api_creds(_client.create_or_derive_api_creds())
        print("  ✅ CLOB 초기화 완료")
        return _client
    except Exception as e:
        print(f"  ❌ CLOB 오류: {e}")
        return None

def get_active_markets(limit=20):
    results = []
    try:
        r = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={
                'active': 'true', 'closed': 'false',
                'limit': limit, 'order': 'volume24hr',
                'ascending': 'false',
            },
            proxies=PROXIES, timeout=8
        )
        if r.status_code == 200:
            for m in r.json():
                if not m.get('active', False): continue
                if m.get('closed', True): continue
                clob_ids = m.get('clobTokenIds', [])
                if isinstance(clob_ids, str):
                    try: clob_ids = json.loads(clob_ids)
                    except: continue
                if not isinstance(clob_ids, list) or len(clob_ids) < 2: continue
                vol = float(m.get('volume24hr', 0) or 0)
                if vol < 10000: continue
                results.append({
                    'condition_id': m.get('conditionId', ''),
                    'title':        m.get('question', m.get('title', ''))[:60],
                    'yes_token':    str(clob_ids[0]),
                    'no_token':     str(clob_ids[1]),
                    'volume':       vol,
                })
    except Exception as e:
        print(f"  ❌ 시장 조회 오류: {e}")
    return results

def get_midpoint(token_id):
    try:
        client = get_client()
        if client:
            mid = client.get_midpoint(token_id)
            if isinstance(mid, dict):
                return float(mid.get('mid', 0.5))
            return float(mid)
    except: pass
    return 0.5

def place_order_by_token(token_id, side, amount_usdc, price=None):
    ts = datetime.now().strftime('%H:%M:%S')

    if TRADING_MODE != 'live':
        return {'success': True, 'paper': True}

    client = get_client()
    if not client:
        return {'success': False, 'error': 'client 없음'}

    try:
        from py_clob_client.clob_types import OrderArgs, OrderType

        if price is None:
            price = get_midpoint(token_id)

        price = round(max(0.02, min(0.98, float(price))), 4)
        size  = round(amount_usdc / price, 2)

        print(f"  [{ts}] 주문: {side} ${amount_usdc:.2f} @ {price:.0%}")

        order_args = OrderArgs(
            token_id=str(token_id),
            price=price,
            size=size,
            side='BUY',
        )

        signed = client.create_order(order_args)
        resp   = client.post_order(signed, OrderType.GTC)

        if resp:
            order_id = resp.get('orderID', resp.get('id', ''))
            print(f"  [{ts}] ✅ 주문 체결! {side} ${amount_usdc:.2f}")
            return {
                'success':  True,
                'order_id': order_id,
                'side':     side,
                'amount':   amount_usdc,
                'price':    price,
            }
        return {'success': False, 'error': '응답 없음'}

    except Exception as e:
        print(f"  [{ts}] ❌ 오류: {e}")
        return {'success': False, 'error': str(e)}

def place_order(condition_id, side, amount_usdc, price=None):
    markets = get_active_markets(50)
    for m in markets:
        if m['condition_id'] == condition_id:
            token_id = m['yes_token'] if side == 'YES' else m['no_token']
            return place_order_by_token(token_id, side, amount_usdc, price)
    return {'success': False, 'error': '시장 없음'}


if __name__ == '__main__':
    print(f"모드: {TRADING_MODE}")
    print(f"프록시: {PROXY_URL[:35]}..." if PROXY_URL else "프록시: 없음")

    # IP 확인
    try:
        r = requests.get('https://ipv4.webshare.io/', proxies=PROXIES, timeout=5)
        print(f"현재 IP: {r.text.strip()}")
    except: pass

    client = get_client()
    if not client:
        print("❌ 연결 실패"); exit()
    print("✅ CLOB 연결 성공\n")

    markets = get_active_markets(3)
    if not markets:
        print("❌ 활성 시장 없음"); exit()

    mkt = markets[0]
    print(f"✅ 시장: {mkt['title']}")

    ans = input("\n$3 YES 베팅 테스트? (y/n): ").strip().lower()
    if ans == 'y':
        result = place_order_by_token(mkt['yes_token'], 'YES', 3.0)
        print(f"\n결과: {result}")
        if result.get('success'):
            print("🎉 실제 베팅 성공!")
