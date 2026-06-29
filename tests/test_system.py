"""시스템 통합 테스트.

표준 라이브러리 + pytest 만으로 동작한다(외부 API/네트워크 없음).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invest_claude.agents import default_analysts, default_portfolio_manager
from invest_claude.config import Config
from invest_claude.debate import DebateRoom
from invest_claude.llm import MockLLM, create_llm
from invest_claude.market.mock import MockMarketData
from invest_claude.broker.paper import PaperBroker
from invest_claude.models import Action, Decision


# ---------------------------------------------------------------------------
# 시장 데이터: 결정론적이어야 한다
# ---------------------------------------------------------------------------
def test_mock_data_is_deterministic():
    provider = MockMarketData()
    a = provider.get_snapshot("005930")
    b = provider.get_snapshot("005930")
    assert a.price == b.price
    assert a.history == b.history
    assert a.sma5 == b.sma5
    assert a.rsi == b.rsi


def test_different_symbols_differ():
    provider = MockMarketData()
    a = provider.get_snapshot("005930")
    b = provider.get_snapshot("000660")
    assert a.symbol != b.symbol
    # 서로 다른 시드 → 가격 히스토리가 달라야 한다
    assert a.history != b.history


def test_snapshot_indicators_present():
    s = MockMarketData().get_snapshot("035420")
    assert len(s.history) == 30
    assert s.sma5 > 0
    assert s.sma20 > 0
    assert 0 <= s.rsi <= 100
    assert s.per > 0
    assert s.pbr > 0


# ---------------------------------------------------------------------------
# 토론: Decision 을 만들어내야 한다
# ---------------------------------------------------------------------------
def _make_room(rounds: int = 2) -> DebateRoom:
    llm = MockLLM()
    analysts = default_analysts(llm)
    pm = default_portfolio_manager(llm, agent_weights=Config().agent_weights)
    return DebateRoom(analysts=analysts, portfolio_manager=pm, rounds=rounds)


def test_debate_produces_decision():
    snapshot = MockMarketData().get_snapshot("005930")
    room = _make_room(rounds=2)
    decision = room.run(snapshot=snapshot, cash=10_000_000, current_shares=0)

    assert isinstance(decision, Decision)
    assert decision.symbol == "005930"
    assert decision.action in (Action.BUY, Action.SELL, Action.HOLD)
    # 4명 분석가 × 2라운드 = 8개 발언
    assert len(decision.transcript) == 8
    # 분석가 4명의 추천
    assert len(decision.recommendations) == 4
    assert 0.0 <= decision.confidence <= 1.0


def test_debate_is_conversational():
    """후속 발언자는 이전 발언자를 언급해야 대화처럼 보인다."""
    snapshot = MockMarketData().get_snapshot("000660")
    room = _make_room(rounds=2)
    decision = room.run(snapshot=snapshot, cash=10_000_000)
    # 첫 발언 이후의 메시지 중 적어도 하나는 다른 에이전트 이름을 언급
    later = decision.transcript[1:]
    mentions = [m for m in later if any(name in m.content for name in
                ["강세론자", "약세론자", "기술적 분석가", "리스크 매니저"])]
    assert mentions, "후속 발언이 이전 발언자를 언급하지 않음"


def test_debate_rounds_respected():
    snapshot = MockMarketData().get_snapshot("035720")
    room = _make_room(rounds=3)
    decision = room.run(snapshot=snapshot, cash=10_000_000)
    assert len(decision.transcript) == 4 * 3


def test_hold_means_zero_quantity():
    """HOLD 결정은 수량 0 이어야 한다."""
    snapshot = MockMarketData().get_snapshot("005930")
    room = _make_room()
    decision = room.run(snapshot=snapshot, cash=10_000_000)
    if decision.action == Action.HOLD:
        assert decision.quantity == 0


# ---------------------------------------------------------------------------
# 모의 브로커: 현금/포지션을 올바르게 갱신해야 한다
# ---------------------------------------------------------------------------
def test_paper_broker_buy_updates_cash_and_positions(tmp_path: Path):
    state = tmp_path / "pf.json"
    broker = PaperBroker(starting_cash=1_000_000, state_path=state)
    snapshot = MockMarketData().get_snapshot("005930")

    qty = 3
    decision = Decision(
        symbol="005930",
        action=Action.BUY,
        quantity=qty,
        confidence=0.8,
        rationale="test",
    )
    fill = broker.execute(decision, snapshot)

    assert fill.action == Action.BUY
    assert fill.quantity == qty
    expected_cost = qty * snapshot.price
    assert fill.cost == pytest.approx(expected_cost)
    assert broker.portfolio.cash == pytest.approx(1_000_000 - expected_cost)
    assert broker.portfolio.shares("005930") == qty


def test_paper_broker_does_not_exceed_cash(tmp_path: Path):
    state = tmp_path / "pf.json"
    broker = PaperBroker(starting_cash=10_000, state_path=state)
    snapshot = MockMarketData().get_snapshot("005930")
    # 현금보다 훨씬 많은 수량 요청
    decision = Decision(
        symbol="005930", action=Action.BUY, quantity=1_000_000,
        confidence=0.9, rationale="test",
    )
    broker.execute(decision, snapshot)
    assert broker.portfolio.cash >= 0  # 현금이 음수가 되면 안 됨


def test_paper_broker_sell_returns_cash(tmp_path: Path):
    state = tmp_path / "pf.json"
    broker = PaperBroker(starting_cash=1_000_000, state_path=state)
    snapshot = MockMarketData().get_snapshot("005930")

    buy = Decision(symbol="005930", action=Action.BUY, quantity=2,
                   confidence=0.8, rationale="buy")
    broker.execute(buy, snapshot)
    cash_after_buy = broker.portfolio.cash

    sell = Decision(symbol="005930", action=Action.SELL, quantity=2,
                    confidence=0.8, rationale="sell")
    fill = broker.execute(sell, snapshot)

    assert fill.action == Action.SELL
    assert fill.quantity == 2
    assert broker.portfolio.shares("005930") == 0
    assert broker.portfolio.cash > cash_after_buy  # 현금 유입


def test_paper_broker_persists_state(tmp_path: Path):
    state = tmp_path / "pf.json"
    broker = PaperBroker(starting_cash=1_000_000, state_path=state)
    snapshot = MockMarketData().get_snapshot("005930")
    broker.execute(
        Decision(symbol="005930", action=Action.BUY, quantity=1,
                 confidence=0.8, rationale="x"),
        snapshot,
    )
    assert state.exists()
    # 새 브로커가 같은 파일을 읽으면 상태가 유지돼야 한다
    broker2 = PaperBroker(starting_cash=1_000_000, state_path=state)
    assert broker2.portfolio.shares("005930") == 1


def test_mark_to_market(tmp_path: Path):
    state = tmp_path / "pf.json"
    broker = PaperBroker(starting_cash=1_000_000, state_path=state)
    snapshot = MockMarketData().get_snapshot("005930")
    broker.execute(
        Decision(symbol="005930", action=Action.BUY, quantity=2,
                 confidence=0.8, rationale="x"),
        snapshot,
    )
    total = broker.mark_to_market({"005930": snapshot.price})
    # 총액 = 현금 + 보유 평가액 ≈ 초기 자본
    assert total == pytest.approx(1_000_000, rel=1e-6)


# ---------------------------------------------------------------------------
# LLM 팩토리: 오프라인에서 MockLLM 으로 폴백
# ---------------------------------------------------------------------------
def test_llm_factory_falls_back_to_mock():
    cfg = Config(llm="mock")
    assert create_llm(cfg).name == "mock"


def test_llm_factory_anthropic_without_package_falls_back():
    # anthropic 패키지가 없으면 auto 든 anthropic 이든 mock 으로 폴백
    cfg = Config(llm="anthropic")
    client = create_llm(cfg)
    assert client.name in ("mock", "anthropic")  # 환경에 따라 다르나 예외는 없어야 함
