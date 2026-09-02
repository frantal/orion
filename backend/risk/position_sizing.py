"""Conservative position sizing.

Risk per trade is capped at a fraction of account equity. The number of
contracts is floored to keep total max loss within that cap. Fewer than one
contract means the opportunity is not executable — ORION never forces a
position it cannot size safely.
"""

from __future__ import annotations

import math

from backend.core.i18n import L
from backend.risk.limits import RiskLimits, default_limits
from backend.risk.models import PositionSizing


def size_position(
    account_equity: float,
    max_loss_per_contract: float,
    limits: RiskLimits | None = None,
    lang: str = "en",
) -> PositionSizing:
    """Compute a conservative contract count for a defined-risk trade."""
    limits = limits or default_limits()
    max_position_risk = round(account_equity * limits.max_single_trade_risk, 2)

    if max_loss_per_contract <= 0:
        return PositionSizing(
            contracts=0,
            max_position_risk=max_position_risk,
            max_loss_per_contract=max_loss_per_contract,
            total_max_loss=0.0,
            executable=False,
            reason=L(lang, "Max loss per contract is non-positive.", "A perda máxima por contrato é não-positiva."),
        )

    contracts = math.floor(max_position_risk / max_loss_per_contract)
    if contracts < 1:
        return PositionSizing(
            contracts=0,
            max_position_risk=max_position_risk,
            max_loss_per_contract=max_loss_per_contract,
            total_max_loss=0.0,
            executable=False,
            reason=L(
                lang,
                (
                    f"Single-contract max loss ${max_loss_per_contract:.2f} exceeds the "
                    f"per-trade risk budget ${max_position_risk:.2f}."
                ),
                (
                    f"A perda máxima de um contrato ${max_loss_per_contract:.2f} excede o "
                    f"orçamento de risco por trade ${max_position_risk:.2f}."
                ),
            ),
        )

    return PositionSizing(
        contracts=contracts,
        max_position_risk=max_position_risk,
        max_loss_per_contract=max_loss_per_contract,
        total_max_loss=round(contracts * max_loss_per_contract, 2),
        executable=True,
    )
