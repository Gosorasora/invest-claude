"""강세론자(Bull) 에이전트.

상승 모멘텀, 거래량 증가, 저평가 신호를 적극적으로 해석해 매수 의견을 낸다.
"""

from __future__ import annotations

from ..models import Action, MarketSnapshot
from .base import BaseAgent


class BullAgent(BaseAgent):
    name = "강세론자"
    role = "낙관적 성장주 투자자"

    def system_prompt(self) -> str:
        return (
            "당신은 낙관적인 성장주 투자자(강세론자)입니다. 상승 모멘텀, "
            "거래량 증가, 낮은 밸류에이션에서 기회를 찾습니다. 시장 데이터를 "
            "근거로 매수 논리를 자신감 있게, 그러나 숫자에 기반해 제시하세요. "
            "다른 분석가의 의견에 반응하며 한국어로 2~3문장으로 답하세요."
        )

    def _analyze(self, snapshot: MarketSnapshot):
        reasons = []
        score = 0.5  # 기본 확신

        if snapshot.change_pct > 0:
            score += min(0.2, snapshot.change_pct / 10.0)
            reasons.append(f"전일比 +{snapshot.change_pct:.2f}% 상승 흐름")
        if snapshot.price >= snapshot.sma5 >= snapshot.sma20 and snapshot.sma20 > 0:
            score += 0.15
            reasons.append(
                f"가격({snapshot.price:,.0f})이 5일선({snapshot.sma5:,.0f})·"
                f"20일선({snapshot.sma20:,.0f}) 위 정배열"
            )
        if snapshot.volume_ratio > 1.2:
            score += 0.1
            reasons.append(f"거래량이 평균의 {snapshot.volume_ratio:.1f}배로 활발")
        if 0 < snapshot.per < 15:
            score += 0.1
            reasons.append(f"PER {snapshot.per:.1f}배로 밸류 매력")
        if snapshot.rsi < 35:
            score += 0.1
            reasons.append(f"RSI {snapshot.rsi:.0f} 과매도 반등 기대")

        score = min(0.95, score)

        if reasons:
            rationale = (
                f"{snapshot.name}({snapshot.symbol})은 매수 기회로 봅니다. "
                + ", ".join(reasons)
                + " — 적극 매수 의견입니다."
            )
            action = Action.BUY if score >= 0.55 else Action.HOLD
        else:
            rationale = (
                f"{snapshot.name}는 뚜렷한 상승 신호가 약합니다만, 장기 성장 관점에서 "
                "분할 매수 여지는 있습니다."
            )
            action = Action.HOLD
            score = 0.5

        return action, score, rationale
