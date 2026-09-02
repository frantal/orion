"""Risk Governor — deterministic veto authority.

The Governor is NOT controlled by the LLM and can veto any opportunity. It
evaluates score thresholds, liquidity, spread, duplicate/aggregate exposure and
position sizing. Any failed hard check produces a VETO with an explicit reason.
Missing-data checks (spread/OI/volume) are soft unless required by the limits.
"""

from __future__ import annotations

from backend.core.i18n import L, normalize_language
from backend.core.logging import get_logger
from backend.quant.models import Opportunity
from backend.risk.limits import RiskLimits, default_limits
from backend.risk.models import PositionSizing, RiskCheck, RiskStatus, RiskVerdict
from backend.risk.position_sizing import size_position

logger = get_logger("risk.governor")


class RiskGovernor:
    """Deterministic gate that returns PASS or VETO for an opportunity."""

    def __init__(self, limits: RiskLimits | None = None) -> None:
        self._limits = limits or default_limits()

    def evaluate(
        self,
        opportunity: Opportunity,
        account_equity: float,
        open_trades_count: int = 0,
        existing_position_keys: set[str] | None = None,
        lang: str = "en",
    ) -> RiskVerdict:
        lang = normalize_language(lang)
        limits = self._limits
        existing_position_keys = existing_position_keys or set()
        checks: list[RiskCheck] = []
        reasons: list[str] = []

        def record(name: str, passed: bool, detail: str, *, hard: bool = True) -> None:
            checks.append(RiskCheck(name=name, passed=passed, detail=detail))
            if hard and not passed:
                reasons.append(detail)

        m = opportunity.metrics
        cand = opportunity.candidate

        record(
            "alpha_score",
            m.alpha_score >= limits.min_alpha_score,
            L(lang,
              f"Alpha Score {m.alpha_score:.0f} vs min {limits.min_alpha_score:.0f}",
              f"Score Alpha {m.alpha_score:.0f} vs mín {limits.min_alpha_score:.0f}"),
        )
        record(
            "liquidity_score",
            m.liquidity_score >= limits.min_liquidity_score,
            L(lang,
              f"Liquidity {m.liquidity_score:.0f} vs min {limits.min_liquidity_score:.0f}",
              f"Liquidez {m.liquidity_score:.0f} vs mín {limits.min_liquidity_score:.0f}"),
        )
        record(
            "risk_score",
            m.risk_score <= limits.max_risk_score,
            L(lang,
              f"Risk Score {m.risk_score:.0f} vs max {limits.max_risk_score:.0f}",
              f"Score de Risco {m.risk_score:.0f} vs máx {limits.max_risk_score:.0f}"),
        )
        record(
            "risk_reward",
            m.risk_reward >= limits.min_risk_reward,
            L(lang,
              f"Risk/Reward {m.risk_reward:.2f} vs min {limits.min_risk_reward:.2f}",
              f"Risco/Retorno {m.risk_reward:.2f} vs mín {limits.min_risk_reward:.2f}"),
        )
        record(
            "expected_value",
            m.expected_value >= limits.min_expected_value,
            L(lang,
              f"Expected value ${m.expected_value:.2f} vs min ${limits.min_expected_value:.2f}",
              f"Valor esperado ${m.expected_value:.2f} vs mín ${limits.min_expected_value:.2f}"),
        )

        # Spread (worst leg). Soft when unknown.
        spread = cand.worst_spread_percent()
        if spread is None:
            record("spread", True, L(lang, "Spread unknown (soft pass)", "Spread desconhecido (passagem leve)"), hard=False)
        else:
            record(
                "spread",
                spread <= limits.max_spread_percent,
                L(lang,
                  f"Spread {spread:.2f}% vs max {limits.max_spread_percent:.2f}%",
                  f"Spread {spread:.2f}% vs máx {limits.max_spread_percent:.2f}%"),
            )

        # Open interest — soft unless required.
        oi = cand.min_open_interest()
        if oi is None:
            record(
                "open_interest",
                not limits.require_open_interest,
                L(lang, "Open interest unknown", "Interesse em aberto desconhecido")
                + ("" if not limits.require_open_interest else L(lang, " (required)", " (obrigatório)")),
                hard=limits.require_open_interest,
            )
        else:
            record(
                "open_interest",
                oi >= limits.min_open_interest,
                L(lang,
                  f"Open interest {oi:.0f} vs min {limits.min_open_interest:.0f}",
                  f"Interesse em aberto {oi:.0f} vs mín {limits.min_open_interest:.0f}"),
            )

        # Volume — soft unless required.
        vol = cand.min_volume()
        if vol is None:
            record(
                "volume",
                not limits.require_volume,
                L(lang, "Volume unknown", "Volume desconhecido")
                + ("" if not limits.require_volume else L(lang, " (required)", " (obrigatório)")),
                hard=limits.require_volume,
            )
        else:
            record(
                "volume",
                vol >= limits.min_volume,
                L(lang,
                  f"Volume {vol:.0f} vs min {limits.min_volume:.0f}",
                  f"Volume {vol:.0f} vs mín {limits.min_volume:.0f}"),
            )

        # Duplicate position.
        key = f"{opportunity.symbol}:{cand.strategy.value}"
        record(
            "duplicate_position",
            key not in existing_position_keys,
            L(lang, f"Duplicate open position for {key}", f"Posição aberta duplicada para {key}"),
        )

        # Max open trades.
        record(
            "max_open_trades",
            open_trades_count < limits.max_open_trades,
            L(lang,
              f"Open trades {open_trades_count} vs max {limits.max_open_trades}",
              f"Trades abertos {open_trades_count} vs máx {limits.max_open_trades}"),
        )

        # Position sizing.
        sizing = size_position(account_equity, cand.max_loss, limits, lang)
        record(
            "position_size",
            sizing.executable,
            sizing.reason or L(lang, f"Sized {sizing.contracts} contract(s)", f"Dimensionado em {sizing.contracts} contrato(s)"),
        )

        # Aggregate portfolio risk for this trade.
        portfolio_cap = round(account_equity * limits.max_portfolio_risk, 2)
        record(
            "portfolio_risk",
            sizing.total_max_loss <= portfolio_cap,
            L(lang,
              f"Trade risk ${sizing.total_max_loss:.2f} vs portfolio cap ${portfolio_cap:.2f}",
              f"Risco do trade ${sizing.total_max_loss:.2f} vs limite da carteira ${portfolio_cap:.2f}"),
        )

        status = RiskStatus.PASS if not reasons else RiskStatus.VETO
        verdict = RiskVerdict(status=status, reasons=reasons, checks=checks, sizing=sizing)
        logger.info(
            "risk verdict",
            extra={"symbol": opportunity.symbol, "status": status.value, "reasons": len(reasons)},
        )
        return verdict
