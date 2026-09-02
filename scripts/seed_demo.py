"""Seed the decision journal with a controlled demo run.

Runs the full ORION pipeline against the offline demo market and records the
resulting decisions, so the dashboard's journals and performance panels are
populated on first launch. Never contacts a broker.

Usage:
    python -m scripts.seed_demo
"""

from __future__ import annotations

import asyncio

from backend.alpaca.demo_adapter import DemoAdapter
from backend.core.config import get_settings
from backend.core.database import init_db
from backend.core.logging import configure_logging, get_logger
from backend.execution.decision import DecisionEngine
from backend.execution.executor import ExecutionEngine
from backend.execution.models import DecisionOutcome
from backend.execution.validator import TradeValidator
from backend.journal.decisions import DecisionJournal
from backend.quant.pipeline import generate_opportunities

logger = get_logger("scripts.seed_demo")


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db(settings)

    adapter = DemoAdapter(settings)
    account = await adapter.get_account()
    clock = await adapter.get_clock()
    result = await generate_opportunities(adapter, "SPY")

    engine = DecisionEngine()
    journal = DecisionJournal(settings)
    executor = ExecutionEngine(adapter, settings)
    validator = TradeValidator(settings)

    executed = 0
    no_trade = 0
    # Decide on the top handful so the journal shows both outcomes.
    for opp in result.opportunities[:8]:
        decision = await engine.decide(opp, account_equity=account.equity)
        row_id = journal.save(decision)
        if decision.decision is DecisionOutcome.EXECUTE:
            validation = validator.validate(opp, decision, account=account, clock=clock)
            if validation.ready:
                order = await executor.execute(opp, decision)
                journal.update_execution(row_id, order.status.value, order.broker_order_id)
                executed += 1
        else:
            no_trade += 1

    print(
        f"Demo seed complete — regime={result.context.regime.value} "
        f"candidates={len(result.opportunities)} executed={executed} no_trade={no_trade}"
    )


if __name__ == "__main__":
    asyncio.run(main())
