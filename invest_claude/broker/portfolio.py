"""포트폴리오 자료구조와 헬퍼."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Position:
    """단일 종목 보유 현황."""

    symbol: str
    quantity: int = 0
    avg_price: float = 0.0  # 평균 매입 단가

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price


@dataclass
class Portfolio:
    """현금 + 보유 종목."""

    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)

    def get_position(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol=symbol))

    def shares(self, symbol: str) -> int:
        return self.get_position(symbol).quantity

    def market_value(self, prices: Dict[str, float]) -> float:
        """현재가 기준 보유 종목 평가액 합계."""
        total = 0.0
        for sym, pos in self.positions.items():
            price = prices.get(sym, pos.avg_price)
            total += pos.quantity * price
        return total

    def total_value(self, prices: Dict[str, float]) -> float:
        """현금 + 평가액."""
        return self.cash + self.market_value(prices)

    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "positions": {
                sym: {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_price": pos.avg_price,
                }
                for sym, pos in self.positions.items()
                if pos.quantity != 0
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        positions: Dict[str, Position] = {}
        for sym, p in (data.get("positions") or {}).items():
            positions[sym] = Position(
                symbol=p.get("symbol", sym),
                quantity=int(p.get("quantity", 0)),
                avg_price=float(p.get("avg_price", 0.0)),
            )
        return cls(cash=float(data.get("cash", 0.0)), positions=positions)
