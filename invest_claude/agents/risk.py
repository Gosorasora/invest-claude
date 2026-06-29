"""리스크 매니저(Risk) 에이전트.

변동성과 거래량 쏠림, 과열 여부로 포지션 크기와 안전성을 평가한다.
대체로 보수적이며 목표 비중을 낮게 잡는다.
"""

from __future__ import annotations

from ..models import Action, MarketSnapshot
from .base import BaseAgent


class RiskAgent(BaseAgent):
    name = "리스크 매니저"
    role = "리스크/포지션 관리자"

    def system_prompt(self) -> str:
        return (
            "당신은 리스크 매니저입니다. 수익보다 손실 방어와 변동성 관리를 우선합니다. "
            "변동성(일간 변동률), 거래량 쏠림, RSI 과열을 보고 포지션 크기를 보수적으로 "
            "제안하세요. 다른 분석가의 의견에 반응하며 한국어로 2~3문장으로 답하세요."
        )

    def _volatility(self, snapshot: MarketSnapshot) -> float:
        """최근 히스토리의 일간 변동률 표준편차 근사(%)."""
        h = snapshot.history
        if len(h) < 3:
            return abs(snapshot.change_pct)
        rets = []
        for prev, cur in zip(h, h[1:]):
            if prev:
                rets.append((cur - prev) / prev * 100.0)
        if not rets:
            return abs(snapshot.change_pct)
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / len(rets)
        return var ** 0.5

    def _analyze(self, snapshot: MarketSnapshot):
        vol = self._volatility(snapshot)
        notes = [f"일간 변동성 약 {vol:.1f}%"]
        risk_score = 0.0

        if vol > 3.0:
            risk_score += 0.4
            notes.append("변동성 과다")
        elif vol > 2.0:
            risk_score += 0.2

        if snapshot.rsi > 75 or snapshot.rsi < 25:
            risk_score += 0.2
            notes.append(f"RSI {snapshot.rsi:.0f} 극단")

        if snapshot.volume_ratio > 2.0:
            risk_score += 0.2
            notes.append(f"거래량 평균比 {snapshot.volume_ratio:.1f}배 쏠림")

        # 리스크가 높으면 매수에 반대(HOLD/관망), 낮으면 신중한 매수 허용
        if risk_score >= 0.5:
            action = Action.HOLD
            confidence = min(0.9, 0.5 + risk_score / 2)
            verdict = "리스크가 높아 신규 진입은 보류하거나 비중을 최소화해야"
        elif risk_score <= 0.2:
            action = Action.BUY
            confidence = 0.55
            verdict = "리스크가 통제 가능한 수준이라 소규모 분할 매수는 허용할 만"
        else:
            action = Action.HOLD
            confidence = 0.55
            verdict = "중간 수준 리스크로 관망하며 분할 접근을"

        rationale = (
            f"{snapshot.name} 리스크 점검: " + ", ".join(notes) + f". {verdict} 합니다."
        )
        return action, confidence, rationale

    def _target_weight(self, stance, confidence):
        # 리스크 매니저는 항상 보수적인 비중을 제안한다.
        from ..models import Action as _A

        if stance == _A.BUY:
            return min(0.25, 0.05 + confidence * 0.2)
        if stance == _A.SELL:
            return 0.0
        return 0.03
