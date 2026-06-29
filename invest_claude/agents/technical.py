"""기술적 분석가(Technical) 에이전트.

이동평균 배열, RSI, 거래량 등 차트 지표 위주로 판단한다.
"""

from __future__ import annotations

from ..models import Action, MarketSnapshot
from .base import BaseAgent


class TechnicalAgent(BaseAgent):
    name = "기술적 분석가"
    role = "차트/모멘텀 분석가"

    def system_prompt(self) -> str:
        return (
            "당신은 기술적 분석가입니다. 이동평균(5일/20일) 배열, RSI, 거래량 같은 "
            "차트 지표로만 판단합니다. 밸류에이션이나 내러티브가 아니라 지표 신호에 "
            "충실하세요. 다른 분석가의 의견에 반응하며 한국어로 2~3문장으로 답하세요."
        )

    def _analyze(self, snapshot: MarketSnapshot):
        signals = []
        bullish = 0
        bearish = 0

        # 골든/데드 크로스 성격 판단
        if snapshot.sma20 > 0:
            if snapshot.sma5 > snapshot.sma20:
                bullish += 1
                signals.append(
                    f"5일선({snapshot.sma5:,.0f})>20일선({snapshot.sma20:,.0f}) 정배열"
                )
            else:
                bearish += 1
                signals.append(
                    f"5일선({snapshot.sma5:,.0f})<20일선({snapshot.sma20:,.0f}) 역배열"
                )

        # RSI
        if snapshot.rsi < 30:
            bullish += 1
            signals.append(f"RSI {snapshot.rsi:.0f} 과매도")
        elif snapshot.rsi > 70:
            bearish += 1
            signals.append(f"RSI {snapshot.rsi:.0f} 과매수")
        else:
            signals.append(f"RSI {snapshot.rsi:.0f} 중립")

        # 거래량
        if snapshot.volume_ratio > 1.3:
            signals.append(f"거래량 평균比 {snapshot.volume_ratio:.1f}배 동반")
            if snapshot.change_pct >= 0:
                bullish += 1
            else:
                bearish += 1

        if bullish > bearish:
            action = Action.BUY
            confidence = min(0.9, 0.55 + 0.12 * (bullish - bearish))
            verdict = "매수 우위 신호"
        elif bearish > bullish:
            action = Action.SELL
            confidence = min(0.9, 0.55 + 0.12 * (bearish - bullish))
            verdict = "매도 우위 신호"
        else:
            action = Action.HOLD
            confidence = 0.5
            verdict = "신호 혼조, 관망"

        rationale = (
            f"{snapshot.name} 차트는 {verdict}입니다. " + ", ".join(signals) + "."
        )
        return action, confidence, rationale
