# invest-claude 🤖📈

**멀티 에이전트 토론 기반 자동 투자 시스템 (모의 투자 / 오프라인 우선)**

서로 다른 페르소나를 가진 여러 투자 "분석가" 봇들이 한 종목을 두고 **토론**하고,
**포트폴리오 매니저** 봇이 그 토론을 종합해 최종 **BUY / SELL / HOLD** 결정을 내립니다.
그 결정은 **모의 투자(paper trading) 브로커**로 실행됩니다.

> ⚠️ **면책 조항(DISCLAIMER):** 이 프로젝트는 **교육·학습용**입니다. 투자 자문이나
> 투자 권유가 아닙니다. 여기서 산출되는 어떤 신호도 실제 투자 판단의 근거로
> 사용하지 마세요. 실거래는 전적으로 **사용자 본인의 책임**입니다.

---

## 핵심 아이디어: 멀티 에이전트 토론

하나의 LLM 에게 "이 종목 살까?"라고 묻는 대신, 서로 다른 시각을 가진
**4명의 분석가**가 라운드로빈으로 발언하며 **서로의 의견에 반응**합니다.

| 분석가 | 시각 | 주로 보는 것 |
|--------|------|--------------|
| 🐂 **강세론자** | 낙관적 성장주 투자자 | 상승 모멘텀, 거래량, 저평가 |
| 🐻 **약세론자** | 회의적 가치투자자 | 하락 추세, 과열(RSI), 고평가(PER/PBR) |
| 📊 **기술적 분석가** | 차트/모멘텀 | 이동평균 배열, RSI, 거래량 |
| 🛡️ **리스크 매니저** | 리스크/포지션 관리 | 변동성, 거래량 쏠림, 포지션 크기 |

각 분석가는 발언할 때 **지금까지의 전체 토론 기록**을 보기 때문에, 직전 발언자의
입장을 언급하며 동의/반박합니다(진짜 대화처럼). 모든 라운드가 끝나면 각 분석가가
최종 추천을 내고, **포트폴리오 매니저**가 *확신도 가중 투표* 와 *리스크 한도* 를
종합해 최종 의사결정과 매수 수량을 산정합니다.

---

## 아키텍처

```
invest-claude/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── config.yaml
├── pyproject.toml            # python -m invest_claude 동작용 (flat 레이아웃)
├── invest_claude/
│   ├── __init__.py
│   ├── __main__.py           # cli.main() 으로 위임
│   ├── cli.py                # argparse CLI: run, portfolio 서브커맨드
│   ├── config.py             # config.yaml(pyyaml 선택) + 환경변수 덮어쓰기
│   ├── models.py             # dataclass + enum
│   ├── llm.py                # LLMClient 팩토리: AnthropicLLM | MockLLM
│   ├── debate.py             # DebateRoom 오케스트레이터(멀티 라운드)
│   ├── agents/
│   │   ├── __init__.py       # 기본 분석가 로스터 + 포트폴리오 매니저
│   │   ├── base.py           # BaseAgent.speak()/recommend()
│   │   ├── bull.py           # 강세론자
│   │   ├── bear.py           # 약세론자
│   │   ├── technical.py      # 기술적 분석가
│   │   ├── risk.py           # 리스크 매니저
│   │   └── portfolio_manager.py  # 토론 종합 → Decision
│   ├── market/
│   │   ├── __init__.py
│   │   ├── base.py           # MarketDataProvider 인터페이스
│   │   ├── mock.py           # hashlib 시드 기반 결정론적 합성 데이터
│   │   └── kis.py            # KIS Open API 스텁(자격증명 없으면 미구현)
│   └── broker/
│       ├── __init__.py
│       ├── base.py           # Broker 인터페이스
│       ├── paper.py          # PaperBroker: 현금/포지션, JSON 영속화
│       └── portfolio.py      # Portfolio dataclass + 헬퍼
└── tests/
    └── test_system.py        # pytest 통합 테스트
```

---

## 빠른 시작 (Quickstart)

**아무것도 설치하지 않아도** 표준 라이브러리만으로 동작합니다(오프라인).

```bash
# 저장소 루트에서
python -m invest_claude run --symbols 005930
```

여러 종목 / 옵션:

```bash
python -m invest_claude run --symbols 005930,000660 --rounds 2 --capital 10000000
```

저장된 모의 포트폴리오 조회:

```bash
python -m invest_claude portfolio
```

### `run` 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--symbols` | 쉼표로 구분한 종목 코드 (필수) | — |
| `--rounds` | 토론 라운드 수 | 2 |
| `--capital` | 초기 자본(원) | 10,000,000 |
| `--llm` | `mock` / `anthropic` / `auto` | auto |

> 모의 투자 상태는 `./state/portfolio.json` 에 저장됩니다. 다시 실행하면 이어집니다.
> (초기화하려면 `state/` 폴더를 삭제하세요.)

---

## 선택 사항: 실제 Claude LLM 으로 토론하기

기본값은 시장 숫자를 규칙 기반으로 해석하는 **결정론적 MockLLM** 입니다(재현 가능, 오프라인).
실제 Claude(`claude-opus-4-8`)로 분석가들이 토론하게 하려면:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic
python -m invest_claude run --symbols 005930 --llm anthropic
```

- `ANTHROPIC_API_KEY` 가 설정되어 있고 `anthropic` 패키지가 설치돼 있으면
  `--llm auto`(기본)에서도 자동으로 실제 Claude 를 사용합니다.
- 네트워크/인증 오류가 나도 전체 실행은 멈추지 않고 짧은 메시지로 폴백합니다.
- 모델 ID 는 `config.yaml` 의 `model` 또는 환경변수 `INVEST_MODEL` 로 바꿀 수 있습니다.

### 보기 좋은 출력 (선택)

```bash
pip install rich     # 설치하면 컬러/서식 출력, 없으면 일반 print
pip install pyyaml   # 설치하면 config.yaml 을 읽음, 없으면 코드 기본값
```

---

## 실거래는? — 토스증권 vs 한국투자증권(KIS)

**토스증권에는 공개된 자동매매(프로그램 매매) API 가 없습니다.** 따라서 국내 주식을
프로그램으로 자동 매매하려면 **한국투자증권(KIS)의 Open API** 가 사실상 표준 경로입니다.

이 프로젝트의 `invest_claude/market/kis.py` 는 KIS 연동을 위한 **스텁**입니다.
docstring 에 토큰 발급(OAuth) → 시세 조회 → (주문 시) hashkey 발급 흐름을 적어 두었으며,
`KIS_APP_KEY` / `KIS_APP_SECRET` 자격증명이 없으면 명확한 `NotImplementedError` 를 던집니다.
실거래 연동은 추후 직접 구현해야 합니다.

> 🚨 **모의 투자 vs 실거래 안전 경고:** 기본 브로커는 **모의 투자(PaperBroker)** 로,
> 실제 돈이 오가지 않습니다. 실거래 브로커를 연결하면 **실제 자금이 즉시 위험에
> 노출**됩니다. 충분한 검증과 소액 테스트 없이 실거래를 붙이지 마세요. 모든 책임은
> 사용자에게 있습니다.

---

## 동작 방식 (요약)

1. **시장 데이터** — `MockMarketData` 가 `sha256(종목코드)` 시드로 랜덤 워크 가격
   히스토리(약 30개)를 만들고 SMA5/SMA20/RSI/PER/PBR 을 계산합니다. `time`/`random`
   기반 시드를 쓰지 않아 **항상 동일한 결과**가 나옵니다.
2. **토론** — `DebateRoom` 이 분석가들을 라운드로빈으로 여러 라운드 발언시킵니다.
   각 발언은 전체 토론 기록을 입력으로 받습니다.
3. **추천** — 각 분석가가 (행동, 확신도, 목표 비중, 근거)를 담은 `Recommendation` 을 냅니다.
4. **종합** — `PortfolioManager` 가 확신도 가중 투표로 순(net) 컨빅션을 구하고,
   리스크 매니저의 목표 비중과 가용 현금/현재가로 매수 **수량**을 산정합니다.
   (HOLD → 수량 0, 현금 초과 금지)
5. **체결** — `PaperBroker` 가 현금/포지션을 갱신하고 `state/portfolio.json` 에 저장합니다.

---

## 테스트

```bash
pip install pytest
python -m pytest -q
```

테스트는 표준 라이브러리 + pytest 만으로 통과합니다(외부 API/네트워크 없음).
결정론적 데이터, 토론 → Decision 생성, 모의 브로커의 현금/포지션 갱신 등을 검증합니다.

---

## 라이선스

MIT (교육용 예제).
