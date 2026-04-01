# polymarket-bot

폴리마켓 트레이딩봇 기본 골조 프로젝트

## 구조
- `bot.py` : 메인 실행
- `config.py` : 환경변수 및 전략 설정
- `strategy/` : 전략
- `risk/` : 리스크 관리
- `utils/` : 시장 필터

## 설치
```bash
pip install -r requirements.txt
```

## 실행
```bash
python bot.py
```

## 현재 상태
- 테스트용 더미 market 데이터 사용
- 실제 주문 API는 아직 연결 전
- 전략 / 필터 / 리스크 엔진까지 연결 완료
