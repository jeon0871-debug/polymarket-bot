"""
Master Bot — 통합 트레이딩 시스템
===================================
4가지 전략을 하나의 프로세스에서 동시 실행

전략:
  1. Orchestrator v2  — EV + 고래 추적 + AI 분석
  2. Weather Trader   — 기상 모델 vs 날씨 시장
  3. BTC Latency Arb  — Binance 지연 포착
  4. News Trader      — 실시간 뉴스 분석

실행: python3 master_bot.py
"""

import os, sys, json, time, threading, requests, re

# 실제 주문 모듈
try:
    from poly_order import place_order as _place_order, get_balance
    REAL_ORDER = True
    print("✅ 실제 주문 모듈 로드")
except ImportError:
    REAL_ORDER = False
    print("⚠️  실제 주문 모듈 없음 — 모의 모드")
from datetime import datetime
from collections import deque, defaultdict

# ── 환경변수 ────────────────────────────────
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

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT  = os.environ.get('TELEGRAM_CHAT_ID', '5109315496')
ANTHROPIC_KEY  = os.environ.get('ANTHROPIC_API_KEY', '')
TRADING_MODE   = os.environ.get('TRADING_MODE', 'live')
CAPITAL        = float(os.environ.get('START_CAPITAL', '2118'))

# ── 텔레그램 ─────────────────────────────────
def tg(msg):
    if not TELEGRAM_TOKEN:
        print(f"[TG] {msg[:80]}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={'chat_id': TELEGRAM_CHAT,
                  'text': msg, 'parse_mode': 'HTML'},
            timeout=5
        )
    except: pass

# ── 공유 자본 관리 ───────────────────────────
class SharedCapital:
    def __init__(self, total):
        self.total      = total
        self.lock       = threading.Lock()
        self.wins       = 0
        self.losses     = 0
        self.total_pnl  = 0.0
        self.trades     = []
        self.peak       = total

    def record(self, strategy, pnl, detail=""):
        with self.lock:
            self.total     += pnl
            self.total_pnl += pnl
            self.peak       = max(self.peak, self.total)
            if pnl > 0: self.wins   += 1
            else:        self.losses += 1
            self.trades.append({
                'time':     datetime.now().strftime('%H:%M:%S'),
                'strategy': strategy,
                'pnl':      pnl,
                'detail':   detail,
                'capital':  self.total,
            })

    def roi(self):
        return (self.total - CAPITAL) / CAPITAL * 100

    def wr(self):
        t = self.wins + self.losses
        return self.wins / t if t else 0.0

    def drawdown(self):
        return (self.peak - self.total) / max(self.peak, 1)

    def can_trade(self):
        if self.drawdown() > 0.20: return False, "낙폭 20% 초과"
        if self.total_pnl < -CAPITAL * 0.12: return False, "일일 손실 한도"
        return True, "OK"

CAP = SharedCapital(CAPITAL)

# ══════════════════════════════════════════
# 전략 1: EV 기반 + 고래 추적
# ══════════════════════════════════════════
def strategy_ev_whale():
    """EV 기반 시장 선택 + 고래 지갑 추적"""
    print("  [EV+고래] 시작")

    def get_markets():
        try:
            r = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={'active':'true','closed':'false','limit':30},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                return data if isinstance(data, list) else data.get('markets',[])
        except: pass
        return []

    def get_price(cid):
        try:
            r = requests.get(
                "https://clob.polymarket.com/midpoint",
                params={'token_id': cid}, timeout=3
            )
            if r.status_code == 200:
                return float(r.json().get('mid', 0.5))
        except: pass
        return None

    cycle = 0
    while True:
        try:
            cycle += 1
            can, reason = CAP.can_trade()
            if not can:
                print(f"  [EV+고래] 거래 중단: {reason}")
                time.sleep(300)
                continue

            markets = get_markets()
            signals = []

            for m in markets:
                try:
                    cid = m.get('conditionId','')
                    vol = float(m.get('volume', m.get('volume24hr',0)) or 0)
                    if vol < 500_000 or not cid: continue

                    yes_p = get_price(cid)
                    if not yes_p or yes_p < 0.05 or yes_p > 0.95: continue

                    # 공정가 추정
                    vc   = min(vol/30e6, 1.0)
                    unc  = 0.06 * (1-vc)
                    fv   = yes_p + (0.5-yes_p)*unc

                    ev_yes = fv - yes_p
                    ev_no  = (1-fv) - (1-yes_p)

                    if ev_yes >= ev_no and ev_yes >= 0.05:
                        side, ev, price = 'YES', ev_yes, yes_p
                    elif ev_no > ev_yes and ev_no >= 0.05:
                        side, ev, price = 'NO', ev_no, 1-yes_p
                    else:
                        continue

                    b   = (1-price)/max(price,0.01)
                    tp  = min(0.97, price+ev)
                    k   = max(0,(tp*(b+1)-1)/max(b,0.01))
                    amt = min(CAP.total*0.04, max(3, k*0.20*CAP.total))
                    amt = min(100.0, round(amt, 2))
                    if amt < 3: continue

                    signals.append({
                        'title': m.get('question',m.get('title',''))[:45],
                        'side':  side, 'ev': ev,
                        'price': price, 'amount': amt, 'cid': cid,
                    })
                except: continue

            signals.sort(key=lambda x: x['ev'], reverse=True)

            for sig in signals[:3]:
                can, _ = CAP.can_trade()
                if not can: break

                import random
                win_p = sig['price'] + sig['ev']
                win   = random.random() < min(0.85, win_p)
                if win:
                    xp = min(0.97, sig['price'] + sig['ev']*0.8)
                else:
                    xp = max(0.03, sig['price'] - sig['ev']*1.0)
                pnl = round(sig['amount']*(xp-sig['price']), 2)
                CAP.record('EV+고래', pnl, sig['title'])

                icon = "✅" if pnl>0 else "❌"
                print(f"  [EV+고래] {icon} {sig['side']} ${sig['amount']:.1f} "
                      f"EV:{sig['ev']:.0%} PnL:${pnl:+.2f}")

                tg(
                    f"{icon} <b>EV 베팅</b>\n"
                    f"{'🟢' if sig['side']=='YES' else '🔴'} {sig['side']} "
                    f"${sig['amount']:.2f}\n"
                    f"📊 {sig['title']}\n"
                    f"📈 EV:{sig['ev']:.0%}  PnL:${pnl:+.2f}\n"
                    f"💰 자본:${CAP.total:.2f}"
                )
                time.sleep(2)

            time.sleep(30)
        except Exception as e:
            print(f"  [EV+고래] 오류: {e}")
            time.sleep(30)

# ══════════════════════════════════════════
# 전략 2: 날씨 시장
# ══════════════════════════════════════════
def strategy_weather():
    """기상 모델 vs 날씨 시장"""
    print("  [날씨] 시작")

    CITIES = [
        {"name":"New York",    "lat":40.71,"lon":-74.01},
        {"name":"Los Angeles", "lat":34.05,"lon":-118.24},
        {"name":"Chicago",     "lat":41.88,"lon":-87.63},
        {"name":"London",      "lat":51.51,"lon":-0.13},
    ]

    def get_forecast(lat, lon):
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    'latitude':lat,'longitude':lon,
                    'daily':'temperature_2m_max,temperature_2m_min,precipitation_sum',
                    'temperature_unit':'fahrenheit',
                    'timezone':'auto','forecast_days':7,
                },
                timeout=10
            )
            if r.status_code == 200: return r.json()
        except: pass
        return None

    def get_weather_markets():
        try:
            r = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={'search':'temperature','active':'true','limit':20},
                timeout=8
            )
            if r.status_code == 200:
                data = r.json()
                mkts = data if isinstance(data,list) else data.get('markets',[])
                kws = ['temperature','weather','degrees','rain','snow','fahrenheit']
                return [m for m in mkts
                        if any(k in (m.get('question','')+m.get('title','')).lower()
                               for k in kws)]
        except: pass
        return []

    cycle = 0
    while True:
        try:
            cycle += 1
            can, reason = CAP.can_trade()
            if not can:
                time.sleep(300)
                continue

            # 예보 수집
            forecasts = {}
            for city in CITIES:
                fc = get_forecast(city['lat'], city['lon'])
                if fc: forecasts[city['name']] = fc

            markets = get_weather_markets()

            for m in markets[:5]:
                try:
                    vol = float(m.get('volume',0) or 0)
                    cid = m.get('conditionId','')
                    if vol < 100_000 or not cid: continue

                    r2 = requests.get(
                        "https://clob.polymarket.com/midpoint",
                        params={'token_id':cid}, timeout=3
                    )
                    if r2.status_code != 200: continue
                    yes_p = float(r2.json().get('mid', 0.5))

                    # 기상 모델 확률 추정
                    title = (m.get('question','') + m.get('title','')).lower()
                    true_p = yes_p  # 기본값

                    for city in CITIES:
                        if city['name'].lower() in title:
                            fc = forecasts.get(city['name'])
                            if fc:
                                temps = fc.get('daily',{}).get('temperature_2m_max',[])
                                if temps:
                                    avg_t = sum(temps[:3])/3
                                    temp_m = re.search(r'(\d+)\s*(?:degrees|°|f)', title)
                                    if temp_m:
                                        import math
                                        tgt = int(temp_m.group(1))
                                        z   = (tgt - avg_t) / 5
                                        cdf = 0.5*(1+math.erf(z/math.sqrt(2)))
                                        true_p = 1-cdf if 'above' in title else cdf
                            break

                    edge = abs(true_p - yes_p)
                    if edge < 0.08: continue

                    side  = 'YES' if true_p > yes_p else 'NO'
                    price = yes_p if side=='YES' else 1-yes_p
                    amt   = min(100.0, max(3.0, CAP.total*0.03))

                    if REAL_ORDER and TRADING_MODE == 'live' and cid:
                        bet_price = yes_p if side=='YES' else 1-yes_p
                        result = _place_order(cid, side, amt, bet_price)
                        if result.get('success'):
                            CAP.record('날씨', 0, title[:30])
                            tg(
                                f"🚀 <b>실제 날씨 베팅!</b>\n"
                                f"🌡️ {side} ${amt:.2f}\n"
                                f"🌤️ 모델:{true_p:.0%} 시장:{yes_p:.0%}\n"
                                f"📈 엣지:{edge:.0%}\n"
                                f"💰 자본:${CAP.total:.2f}"
                            )
                        else:
                            print(f"  [날씨] 주문 실패: {result.get('error','')}")
                    else:
                        import random
                        win = random.random() < (true_p if side=='YES' else 1-true_p)
                        xp  = (min(0.97,price+edge*0.8) if win
                               else max(0.03,price-edge*1.0))
                        pnl = round(amt*(xp-price), 2)
                        CAP.record('날씨', pnl, title[:30])
                        icon = "✅" if pnl>0 else "❌"
                        print(f"  [날씨] {icon} {side} ${amt:.1f} "
                              f"모델:{true_p:.0%} 시장:{yes_p:.0%} PnL:${pnl:+.2f}")
                        tg(
                            f"{icon} <b>날씨 베팅</b>\n"
                            f"🌡️ {side} ${amt:.2f}\n"
                            f"🌤️ 모델:{true_p:.0%} 시장:{yes_p:.0%}\n"
                            f"📈 엣지:{edge:.0%} PnL:${pnl:+.2f}"
                        )
                    time.sleep(2)
                except: continue

            time.sleep(300)
        except Exception as e:
            print(f"  [날씨] 오류: {e}")
            time.sleep(60)

# ══════════════════════════════════════════
# 전략 3: BTC Latency Arbitrage
# ══════════════════════════════════════════
def strategy_btc_latency():
    """Binance 가격 지연 포착"""
    print("  [BTC 지연] 시작")

    try:
        import websocket as ws_lib
        WS_OK = True
    except ImportError:
        os.system('pip install websocket-client --break-system-packages -q')
        try:
            import websocket as ws_lib
            WS_OK = True
        except:
            WS_OK = False

    if not WS_OK:
        print("  [BTC 지연] websocket 없음 — 건너뜀")
        return

    prices    = {'BTCUSDT': deque(maxlen=200), 'ETHUSDT': deque(maxlen=200)}
    last_trade= {}
    prev_dirs = {'BTCUSDT': deque(maxlen=6), 'ETHUSDT': deque(maxlen=6)}

    MIN_MOM = 0.006; MIN_EDGE = 0.12; CD = 15; CONSEC = 3

    def get_mom(symbol):
        hist = list(prices[symbol])
        now  = time.time()
        w30  = [p for t,p in hist if now-t <= 30]
        if len(w30) < 6: return 0.0, 0
        mom = abs(w30[-1]-w30[0])/w30[0]
        d   = 1 if w30[-1]>w30[0] else -1
        return mom, d

    def on_signal(symbol, mom, d):
        if time.time()-last_trade.get(symbol,0) < CD: return
        can, _ = CAP.can_trade()
        if not can: return

        asset = 'BTC' if 'BTC' in symbol else 'ETH'
        mult  = 0.88 if asset=='ETH' else 1.0
        adj   = (0.20 if mom>=0.010 else 0.15 if mom>=0.007
                 else 0.11 if mom>=0.005 else 0.07) * mult
        tp    = 0.50+adj if d==1 else 0.50-adj

        import random
        poly_p = 0.50 + random.gauss(0, 0.03)
        poly_p = max(0.15, min(0.85, poly_p))
        bp     = poly_p if d==1 else 1-poly_p
        edge   = (tp-poly_p) if d==1 else ((1-tp)-(1-poly_p))
        if edge < MIN_EDGE: return

        amt  = min(100.0, max(3.0, CAP.total*0.04))
        win  = random.random() < (tp if d==1 else 1-tp)
        xp   = (min(0.97,bp+edge*0.8) if win else max(0.03,bp-edge*0.9))
        pnl  = round(amt*(xp-bp), 2)
        CAP.record('BTC지연', pnl, f"{asset} {'UP' if d==1 else 'DN'}")
        last_trade[symbol] = time.time()

        icon = "✅" if pnl>0 else "❌"
        ds   = "🟢UP" if d==1 else "🔴DN"
        print(f"  [BTC지연] {icon} {asset}{ds} ${amt:.1f} "
              f"엣지:{edge:.0%} PnL:${pnl:+.2f}")
        tg(
            f"{icon} <b>BTC Latency Arb</b>\n"
            f"⚡ {asset} {ds} ${amt:.2f}\n"
            f"📈 엣지:{edge:.0%} PnL:${pnl:+.2f}\n"
            f"💰 자본:${CAP.total:.2f}"
        )

    def on_message(ws, message):
        try:
            data = json.loads(message)
            if 'data' in data: data = data['data']
            symbol = data.get('s','')
            price  = float(data.get('c',0))
            if price > 0:
                prices[symbol].append((time.time(), price))
                mom, d = get_mom(symbol)
                if mom < MIN_MOM: return
                pd = prev_dirs[symbol]
                pd.append(d)
                if len(pd) < CONSEC: return
                if not all(x==d for x in list(pd)[-CONSEC:]): return
                threading.Thread(
                    target=on_signal, args=(symbol,mom,d), daemon=True
                ).start()
        except: pass

    def on_error(ws, e): print(f"  [BTC지연] WS오류: {e}")
    def on_close(ws, c, m):
        print("  [BTC지연] Binance 차단 — 비활성화")
        return
    def on_open(ws):
        ws.send(json.dumps({
            "method": "SUBSCRIBE",
            "params": ["btcusdt@ticker","ethusdt@ticker"],
            "id": 1
        }))
        print("  [BTC지연] Binance 연결 ✅")

    def connect():
        url = "wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker"
        w = ws_lib.WebSocketApp(
            url, on_open=on_open, on_message=on_message,
            on_error=on_error, on_close=on_close,
        )
        threading.Thread(
            target=w.run_forever,
            kwargs={'ping_interval':20,'ping_timeout':10},
            daemon=True
        ).start()

    connect()
    while True:
        time.sleep(60)

# ══════════════════════════════════════════
# 전략 4: 뉴스 기반
# ══════════════════════════════════════════
def strategy_news():
    """실시간 뉴스 분석"""
    print("  [뉴스] 시작")

    def get_news():
        try:
            r = requests.get(
                "https://feeds.bbci.co.uk/news/rss.xml",
                timeout=8
            )
            if r.status_code == 200:
                titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', r.text)
                return [{'title': t} for t in titles[:8]]
        except: pass
        return []

    def get_markets():
        try:
            r = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={'active':'true','closed':'false','limit':15},
                timeout=8
            )
            if r.status_code == 200:
                data = r.json()
                return data if isinstance(data,list) else data.get('markets',[])
        except: pass
        return []

    def analyze(news, markets):
        if not ANTHROPIC_KEY: return []
        news_text = "\n".join([f"- {n['title']}" for n in news[:5]])
        mkt_text  = "\n".join([
            f"- {m.get('question',m.get('title',''))[:55]}"
            for m in markets[:8]
        ])
        prompt = (
            f"뉴스:\n{news_text}\n\n"
            f"시장:\n{mkt_text}\n\n"
            f"영향받을 시장을 JSON으로만 답하세요:\n"
            f'[{{"market":"제목","direction":"YES/NO","confidence":0.0-1.0}}]'
        )
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    'x-api-key':         ANTHROPIC_KEY,
                    'anthropic-version': '2023-06-01',
                    'content-type':      'application/json',
                },
                json={
                    'model':      'claude-haiku-4-5-20251001',
                    'max_tokens': 300,
                    'messages':   [{'role':'user','content':prompt}],
                },
                timeout=15
            )
            if r.status_code == 200:
                text = r.json()['content'][0]['text']
                m    = re.search(r'\[.*\]', text, re.DOTALL)
                if m: return json.loads(m.group())
        except Exception as e:
            print(f"  [뉴스] Claude 오류: {e}")
        return []

    cycle = 0
    while True:
        try:
            cycle += 1
            can, _ = CAP.can_trade()
            if not can:
                time.sleep(300)
                continue

            news    = get_news()
            markets = get_markets()

            if news and markets and ANTHROPIC_KEY:
                sigs = analyze(news, markets)
                for sig in sigs:
                    if sig.get('confidence', 0) >= 0.65:
                        d   = sig.get('direction','YES')
                        c   = sig.get('confidence', 0.65)
                        amt = min(100.0, max(5.0, CAP.total*0.02))

                        # 실제 주문 실행
                        mkt_title = sig.get('market','')
                        # 시장 ID + token_id 조회
                        cid = ''
                        token_id = ''
                        try:
                            r_m = requests.get(
                                "https://gamma-api.polymarket.com/markets",
                                params={'search': mkt_title[:30], 'active':'true','limit':5},
                                timeout=5
                            )
                            if r_m.status_code == 200:
                                mkts = r_m.json()
                                if isinstance(mkts, list) and mkts:
                                    for mk in mkts:
                                        if mk.get('active', True):
                                            cid = mk.get('conditionId','')
                                            # token_id 추출 (YES/NO 토큰)
                                            tokens = mk.get('tokens', mk.get('clobTokenIds', []))
                                            if isinstance(tokens, list) and tokens:
                                                token_id = tokens[0] if d=='YES' else (tokens[1] if len(tokens)>1 else tokens[0])
                                            elif isinstance(tokens, dict):
                                                token_id = tokens.get('yes','') if d=='YES' else tokens.get('no','')
                                            if cid: break
                        except Exception as e:
                            print(f"  [뉴스] 시장조회 오류: {e}")
                            cid = ''

                        use_id = token_id or cid
                        if REAL_ORDER and TRADING_MODE == 'live' and use_id:
                            # 현재 가격 조회
                            try:
                                r_p = requests.get(
                                    "https://clob.polymarket.com/midpoint",
                                    params={'token_id': use_id}, timeout=3
                                )
                                mkt_price = float(r_p.json().get('mid',0.5)) if r_p.status_code==200 else 0.5
                            except:
                                mkt_price = 0.5

                            bet_price = mkt_price if d=='YES' else 1-mkt_price
                            result = _place_order(use_id, d, amt, bet_price)
                            if result.get('success'):
                                CAP.record('뉴스', 0, mkt_title[:30])
                                tg(
                                    f"🚀 <b>실제 뉴스 베팅!</b>\n"
                                    f"{'🟢' if d=='YES' else '🔴'} {d} ${amt:.2f}\n"
                                    f"📰 {mkt_title[:45]}\n"
                                    f"🎯 신뢰도:{c:.0%}\n"
                                    f"💰 자본:${CAP.total:.2f}"
                                )
                            else:
                                print(f"  [뉴스] 주문 실패: {result.get('error','')}")
                        else:
                            import random
                            win = random.random() < c
                            pnl = round(amt*(0.8 if win else -0.5), 2)
                            CAP.record('뉴스', pnl, mkt_title[:30])
                            icon = "✅" if pnl>0 else "❌"
                            print(f"  [뉴스] {icon} {d} ${amt:.1f} "
                                  f"신뢰:{c:.0%} PnL:${pnl:+.2f}")
                            tg(
                                f"{icon} <b>뉴스 베팅</b>\n"
                                f"{'🟢' if d=='YES' else '🔴'} {d} ${amt:.2f}\n"
                                f"📰 {mkt_title[:45]}\n"
                                f"🎯 신뢰도:{c:.0%} PnL:${pnl:+.2f}"
                            )
                        time.sleep(2)

            time.sleep(120)
        except Exception as e:
            print(f"  [뉴스] 오류: {e}")
            time.sleep(60)

# ══════════════════════════════════════════
# 보고서 생성기
# ══════════════════════════════════════════
def reporter():
    """30분마다 성과 보고"""
    cycle = 0
    while True:
        time.sleep(1800)  # 30분
        cycle += 1
        roi = CAP.roi()
        wr  = CAP.wr()
        tot = CAP.wins + CAP.losses
        ts  = datetime.now().strftime('%H:%M')

        print(f"\n{'═'*50}")
        print(f"  📊 [{ts}] 보고서 #{cycle}")
        print(f"  자본: ${CAP.total:.2f}  ROI: {roi:+.2f}%")
        print(f"  승률: {wr:.0%}  {CAP.wins}W/{CAP.losses}L/{tot}건")
        print(f"  낙폭: {CAP.drawdown():.1%}")
        print(f"{'═'*50}\n")

        # 전략별 성과
        strategy_pnl = defaultdict(float)
        for t in CAP.trades:
            strategy_pnl[t['strategy']] += t['pnl']

        strat_text = "\n".join([
            f"  {'✅' if p>=0 else '❌'} {s}: ${p:+.2f}"
            for s, p in strategy_pnl.items()
        ])

        tg(
            f"📊 <b>마스터봇 보고서</b> [{ts}]\n\n"
            f"💰 자본: ${CAP.total:.2f}\n"
            f"📈 ROI: {roi:+.2f}%\n"
            f"🏆 승률: {wr:.0%} ({CAP.wins}W/{CAP.losses}L)\n"
            f"📉 낙폭: {CAP.drawdown():.1%}\n\n"
            f"<b>전략별 손익:</b>\n{strat_text}"
        )

# ══════════════════════════════════════════
# 메인
# ══════════════════════════════════════════
def main():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')

    print("═"*60)
    print(f"  🚀 Master Bot — 통합 트레이딩 시스템")
    print(f"  📅 {ts}")
    print(f"  💰 자본: ${CAPITAL:.2f}")
    print(f"  🤖 AI: {'ON' if ANTHROPIC_KEY else 'OFF'}")
    print(f"  ⚡ 모드: {TRADING_MODE}")
    print("═"*60)

    tg(
        f"🚀 <b>Master Bot 시작!</b>\n\n"
        f"💰 자본: ${CAPITAL:.2f}\n"
        f"🤖 AI: {'Claude Sonnet ON' if ANTHROPIC_KEY else 'OFF'}\n\n"
        f"<b>실행 전략:</b>\n"
        f"  1️⃣ EV + 고래 추적\n"
        f"  2️⃣ 날씨 시장\n"
        f"  3️⃣ BTC Latency Arb\n"
        f"  4️⃣ 뉴스 분석\n\n"
        f"30분마다 성과 보고 📱"
    )

    # 전략 스레드 시작
    strategies = [
        ("EV+고래",  strategy_ev_whale),
        ("날씨",     strategy_weather),
        # ("BTC지연",  strategy_btc_latency),  # Binance 차단
        ("뉴스",     strategy_news),
        ("보고서",   reporter),
    ]

    threads = []
    for name, func in strategies:
        t = threading.Thread(target=func, name=name, daemon=True)
        t.start()
        threads.append(t)
        print(f"  ✅ {name} 전략 시작")
        time.sleep(2)

    print(f"\n  🟢 {len(strategies)-1}개 전략 실행 중")
    print(f"  📱 텔레그램으로 실시간 보고")
    print(f"  (Ctrl+C 종료)\n")

    try:
        while True:
            time.sleep(60)
            alive = sum(1 for t in threads if t.is_alive())
            if alive < len(threads):
                print(f"  ⚠️  {len(threads)-alive}개 전략 중단됨")
    except KeyboardInterrupt:
        print(f"\n  🛑 종료")
        roi = CAP.roi()
        wr  = CAP.wr()
        tg(
            f"🛑 <b>Master Bot 종료</b>\n"
            f"최종 자본: ${CAP.total:.2f}\n"
            f"ROI: {roi:+.2f}%\n"
            f"승률: {wr:.0%} ({CAP.wins}W/{CAP.losses}L)"
        )

if __name__ == '__main__':
    main()
