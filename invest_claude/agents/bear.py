"""약세론자(Bear) 에이전트.

하락 신호, 과열, 고평가를 경계하며 매도/관망 의견을 낸다.
"""

from __future__ import annotations

from ..models import Action, MarketSnapshot
from .base import BaseAgent


class BearAgent(BaseAgent):
    name = "약세론자"
    role = "회의적 가치투자자"

    def system_prompt(self) -> str:
        return (
            "당신은 회의적인 가치투자자(약세론자)입니다. 하락 추세, 과열(고RSI), "
            "고평가(높은 PER/PBR), 거래량 둔화에서 위험을 봅니다. 시장 데이터를 "
            "근거로 매도 또는 관망 논리를 냉정하게 제시하세요. 다른 분석가의 의견에 "
            "반응하며 한국어로 2~3문장으로 답하세요."
        )

    def _analyze(self, snapshot: MarketSnapshot):
        reasons = []
        score = 0.5

        if snapshot.change_pct < 0:
            score += min(0.2, abs(snapshot.change_pct) / 10.0)
            reasons.append(f"전일比 {snapshot.change_pct:.2f}% 하락")
        if snapshot.sma20 > 0 and snapshot.price < snapshot.sma20:
            score += 0.15
            reasons.append(
                f"가격({snapshot.price:,.0f})이 20일선({snapshot.sma20:,.0f}) 하회"
            )
        if snapshot.rsi > 70:
            score += 0.15
            reasons.append(f"RSI {snapshot.rsi:.0f} 과매수 부담")
        if snapshot.per > 25:
            score += 0.1
            reasons.append(f"PER {snapshot.per:.1f}배 고평가")
        if snapshot.pbr > 3.0:
            score += 0.1
            reasons.append(f"PBR {snapshot.pbr:.1f}배 부담")

        score = min(0.95, score)

        if reasons and score >= 0.55:
            rationale = (
                f"{snapshot.name}({snapshot.symbol})은 위험이 큽니다. "
                + ", ".join(reasons)
                + " — 매도 또는 비중 축소를 권합니다."
            )
            action = Action.SELL
        else:
            rationale = (
                f"{snapshot.name}는 당장 급락 위험은 제한적이나, 추격 매수는 "
                "경계해야 합니다. 관망을 권합니다."
            )
            action = Action.HOLD
            score = max(score, 0.5)

        return action, score, rationale
