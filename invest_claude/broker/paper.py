"""모의 투자(Paper Trading) 브로커.

실제 돈을 쓰지 않고 현금/보유 종목을 추적한다. 상태는 JSON 으로
./state/portfolio.json 에 저장/로드한다. 표준 라이브러리만 사용.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from ..models import Action, Decision, Fill, MarketSnapshot
from .portfolio import Portfolio, Position


DEFAULT_STATE_PATH = Path("state") / "portfolio.json"


class PaperBroker:
    """현금 + 포지션을 관리하는 모의 브로커."""

    def __init__(
        self,
        starting_cash: float = 10_000_000.0,
        state_path: Optional[Path | str] = None,
    ) -> None:
        self.state_path = Path(state_path) if state_path else DEFAULT_STATE_PATH
        self.portfolio = self._load_or_init(starting_cash)

    # ------------------------------------------------------------------
    # 상태 영속화
    # ------------------------------------------------------------------
    def _load_or_init(self, starting_cash: float) -> Portfolio:
        if self.state_path.exists():
            try:
                with self.state_path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                return Portfolio.from_dict(data)
            except Exception:
                # 손상된 파일이면 새로 시작
                return Portfolio(cash=starting_cash)
        return Portfolio(cash=starting_cash)

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as fh:
            json.dump(self.portfolio.to_dict(), fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 매매 실행
    # ------------------------------------------------------------------
    def execute(self, decision: Decision, snapshot: MarketSnapshot) -> Fill:
        """의사결정을 체결한다. 현금 부족 시 가능한 수량만 매수한다."""
        price = max(1.0, snapshot.price)
        symbol = decision.symbol

        if decision.action == Action.BUY and decision.quantity > 0:
            qty = decision.quantity
            cost = qty * price
            # 현금을 넘지 않도록 보정(이중 안전장치)
            if cost > self.portfolio.cash:
                qty = int(self.portfolio.cash // price)
                cost = qty * price
            if qty <= 0:
                return Fill(symbol=symbol, action=Action.HOLD, quantity=0, price=price, cost=0.0)

            pos = self.portfolio.positions.get(symbol, Position(symbol=symbol))
            new_qty = pos.quantity + qty
            # 평균 단가 갱신
            new_avg = (
                ((pos.quantity * pos.avg_price) + (qty * price)) / new_qty
                if new_qty
                else price
            )
            pos.quantity = new_qty
            pos.avg_price = round(new_avg, 2)
            self.portfolio.positions[symbol] = pos
            self.portfolio.cash -= cost
            self.save()
            return Fill(symbol=symbol, action=Action.BUY, quantity=qty, price=price, cost=cost)

        if decision.action == Action.SELL:
            pos = self.portfolio.positions.get(symbol)
            held = pos.quantity if pos else 0
            qty = min(decision.quantity or held, held)
            if qty <= 0:
                return Fill(symbol=symbol, action=Action.HOLD, quantity=0, price=price, cost=0.0)
            proceeds = qty * price
            pos.quantity -= qty
            if pos.quantity == 0:
                pos.avg_price = 0.0
            self.portfolio.cash += proceeds
            self.save()
            # 매도는 현금 유입이므로 cost 를 음수로 표기
            return Fill(symbol=symbol, action=Action.SELL, quantity=qty, price=price, cost=-proceeds)

        # HOLD 또는 수량 0
        return Fill(symbol=symbol, action=Action.HOLD, quantity=0, price=price, cost=0.0)

    # ------------------------------------------------------------------
    # 평가
    # ------------------------------------------------------------------
    def mark_to_market(self, prices: Dict[str, float]) -> float:
        """현재가 기준 총 평가액(현금+보유)."""
        return self.portfolio.total_value(prices)
