"""커맨드라인 인터페이스.

서브커맨드:
- run: 종목별 토론을 실행하고 결과를 모의 투자 브로커로 체결한다.
- portfolio: 저장된 모의 포트폴리오를 현재가로 평가해 출력한다.

rich 가 설치돼 있으면 보기 좋게, 없으면 일반 print 로 출력한다.
"""

from __future__ import annotations

import argparse
from typing import List, Optional

from .agents import default_analysts, default_portfolio_manager
from .config import load_config
from .debate import DebateRoom
from .llm import create_llm
from .market import create_provider
from .broker import create_broker
from .models import Action, Decision, MarketSnapshot


# ---------------------------------------------------------------------------
# 출력 헬퍼 (rich 선택적)
# ---------------------------------------------------------------------------
def _get_console():
    try:
        from rich.console import Console  # type: ignore

        return Console()
    except Exception:
        return None


def _print(console, text: str = "") -> None:
    if console is not None:
        console.print(text)
    else:
        # rich 마크업 제거(대괄호 태그 등)는 단순화를 위해 그대로 두되 print
        print(_strip_markup(text))


def _strip_markup(text: str) -> str:
    """rich 미설치 시 [bold] 같은 마크업을 단순 제거."""
    import re

    return re.sub(r"\[/?[a-zA-Z0-9 _#=]+\]", "", text)


def _fmt_won(value: float) -> str:
    return f"{value:,.0f}원"


# ---------------------------------------------------------------------------
# run 서브커맨드
# ---------------------------------------------------------------------------
def _print_transcript(console, decision: Decision) -> None:
    _print(console, "[bold cyan]── 토론 기록 ──[/bold cyan]")
    for i, msg in enumerate(decision.transcript, 1):
        stance = f" ({msg.stance}, 확신 {msg.confidence:.0%})" if msg.stance else ""
        _print(console, f"[bold]{i:>2}. {msg.agent_name}[/bold]{stance}")
        _print(console, f"    {msg.content}")
    _print(console, "")

    _print(console, "[bold cyan]── 분석가 최종 추천 ──[/bold cyan]")
    for rec in decision.recommendations:
        _print(
            console,
            f"  • {rec.agent_name}: [bold]{rec.action}[/bold] "
            f"(확신 {rec.confidence:.0%}, 목표비중 {rec.target_weight:.0%})",
        )
    _print(console, "")


def _print_decision(console, decision: Decision, snapshot: MarketSnapshot) -> None:
    color = {
        Action.BUY: "green",
        Action.SELL: "red",
        Action.HOLD: "yellow",
    }[decision.action]
    _print(console, "[bold cyan]── 최종 의사결정 ──[/bold cyan]")
    qty = f" {decision.quantity}주" if decision.action != Action.HOLD else ""
    _print(
        console,
        f"  [bold {color}]{decision.action}{qty}[/bold {color}] "
        f"@ {_fmt_won(snapshot.price)} (확신 {decision.confidence:.0%})",
    )
    _print(console, f"  근거: {decision.rationale}")
    _print(console, "")


def _print_snapshot(console, s: MarketSnapshot) -> None:
    _print(
        console,
        f"[bold]{s.name} ({s.symbol})[/bold]  "
        f"현재가 {_fmt_won(s.price)}  전일比 {s.change_pct:+.2f}%",
    )
    _print(
        console,
        f"  SMA5 {s.sma5:,.0f} / SMA20 {s.sma20:,.0f} / RSI {s.rsi:.0f} / "
        f"PER {s.per:.1f} / PBR {s.pbr:.1f} / 거래량 평균比 {s.volume_ratio:.1f}배",
    )
    _print(console, "")


def cmd_run(args: argparse.Namespace) -> int:
    console = _get_console()
    config = load_config()

    # CLI 인자로 설정 덮어쓰기
    if args.rounds is not None:
        config.rounds = args.rounds
    if args.capital is not None:
        config.capital = float(args.capital)
    if args.llm is not None:
        config.llm = args.llm

    symbols: List[str] = _parse_symbols(args.symbols)
    if not symbols:
        _print(console, "[red]종목 코드를 하나 이상 입력하세요. 예: --symbols 005930[/red]")
        return 2

    llm = create_llm(config)
    provider = create_provider(config)
    broker = create_broker(config)

    analysts = default_analysts(llm)
    pm = default_portfolio_manager(llm, agent_weights=config.agent_weights)
    room = DebateRoom(analysts=analysts, portfolio_manager=pm, rounds=config.rounds)

    _print(console, "")
    _print(
        console,
        f"[bold magenta]=== invest-claude 멀티 에이전트 토론 ===[/bold magenta]",
    )
    _print(
        console,
        f"LLM: {llm.name} | 데이터: {config.data_provider} | 브로커: paper | "
        f"라운드: {config.rounds} | 초기자본: {_fmt_won(config.capital)}",
    )
    _print(console, "")

    snapshots: dict = {}
    for symbol in symbols:
        snapshot = provider.get_snapshot(symbol)
        snapshots[symbol] = snapshot

        _print(console, "[bold white on blue] 종목 분석 [/bold white on blue]")
        _print_snapshot(console, snapshot)

        current_shares = broker.portfolio.shares(symbol)
        decision = room.run(
            snapshot=snapshot,
            cash=broker.portfolio.cash,
            current_shares=current_shares,
        )

        _print_transcript(console, decision)
        _print_decision(console, decision, snapshot)

        fill = broker.execute(decision, snapshot)
        if fill.action == Action.HOLD or fill.quantity == 0:
            _print(console, "  [dim]체결: 없음 (관망)[/dim]")
        else:
            _print(
                console,
                f"  [bold]체결: {fill.action} {fill.quantity}주 @ {_fmt_won(fill.price)} "
                f"(금액 {_fmt_won(abs(fill.cost))})[/bold]",
            )
        _print(console, f"  잔여 현금: {_fmt_won(broker.portfolio.cash)}")
        _print(console, "")
        _print(console, "─" * 60)
        _print(console, "")

    # 최종 포트폴리오 요약
    _print_portfolio(console, broker, snapshots)
    return 0


# ---------------------------------------------------------------------------
# portfolio 서브커맨드
# ---------------------------------------------------------------------------
def _print_portfolio(console, broker, snapshots: Optional[dict] = None) -> None:
    config = load_config()
    provider = create_provider(config)

    p = broker.portfolio
    prices: dict = {}
    snapshots = snapshots or {}
    for sym in p.positions:
        if sym in snapshots:
            prices[sym] = snapshots[sym].price
        else:
            prices[sym] = provider.get_snapshot(sym).price

    _print(console, "[bold magenta]=== 포트폴리오 (모의 투자) ===[/bold magenta]")
    _print(console, f"  현금: {_fmt_won(p.cash)}")
    if not p.positions or all(pos.quantity == 0 for pos in p.positions.values()):
        _print(console, "  보유 종목: 없음")
    else:
        _print(console, "  보유 종목:")
        for sym, pos in p.positions.items():
            if pos.quantity == 0:
                continue
            price = prices.get(sym, pos.avg_price)
            value = pos.quantity * price
            pnl = value - pos.cost_basis
            pnl_pct = (pnl / pos.cost_basis * 100.0) if pos.cost_basis else 0.0
            _print(
                console,
                f"    • {sym}: {pos.quantity}주 @ 평단 {_fmt_won(pos.avg_price)} "
                f"→ 현재 {_fmt_won(price)} | 평가 {_fmt_won(value)} "
                f"(평가손익 {pnl:+,.0f}원, {pnl_pct:+.2f}%)",
            )
    total = p.total_value(prices)
    _print(console, f"  [bold]총 평가액: {_fmt_won(total)}[/bold]")
    _print(console, "")


def cmd_portfolio(args: argparse.Namespace) -> int:
    console = _get_console()
    config = load_config()
    broker = create_broker(config)
    _print_portfolio(console, broker)
    return 0


# ---------------------------------------------------------------------------
# 파서
# ---------------------------------------------------------------------------
def _parse_symbols(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [s.strip() for s in raw.replace(" ", ",").split(",") if s.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invest_claude",
        description="멀티 에이전트 토론 기반 자동 투자 시스템 (모의 투자)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="종목 토론 실행 후 모의 매매")
    run_p.add_argument(
        "--symbols",
        required=True,
        help="쉼표로 구분한 종목 코드. 예: 005930,000660",
    )
    run_p.add_argument("--rounds", type=int, default=None, help="토론 라운드 수 (기본 2)")
    run_p.add_argument("--capital", type=float, default=None, help="초기 자본(원)")
    run_p.add_argument(
        "--llm",
        choices=["mock", "anthropic", "auto"],
        default=None,
        help="LLM 모드 (기본 auto)",
    )
    run_p.set_defaults(func=cmd_run)

    pf_p = sub.add_parser("portfolio", help="저장된 모의 포트폴리오 조회")
    pf_p.set_defaults(func=cmd_portfolio)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
