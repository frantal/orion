"""REST API routes for ORION.

Phase 1 exposed health/diagnostics. Phase 2 adds read-only Alpaca-backed
endpoints: account, clock, market snapshot and option chain. No route places an
order — execution arrives in Phase 5.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend import __version__
from backend.agents.models import AlphaAssessment
from backend.agents.options_agent import OptionsAlphaAgent
from backend.alpaca.mcp_adapter import AlpacaAdapter, get_adapter
from backend.alpaca.models import OptionChain, StockQuote, StockSnapshot
from backend.api.schemas import (
    AccountResponse,
    AnalyzeRequest,
    BacktestRequest,
    CheckResult,
    ClockResponse,
    DecideRequest,
    ExecuteRequest,
    GreeksResponse,
    HealthResponse,
    LegResponse,
    MarketResponse,
    OpportunitiesResponse,
    OpportunityResponse,
    OptionChainResponse,
    OptionContractResponse,
    OrderResultResponse,
    PositionResponse,
    RegimeResponse,
    RiskVerdictResponse,
    SizingResponse,
)
from backend.backtesting.engine import BacktestEngine
from backend.backtesting.models import BacktestReport
from backend.core.config import get_settings
from backend.core.database import get_connection
from backend.core.diagnostics import run_diagnostics
from backend.core.exceptions import AlpacaUnavailableError, InvalidQuoteError
from backend.execution.decision import DecisionEngine
from backend.execution.executor import ExecutionEngine
from backend.execution.models import DecisionOutcome, ExecutionStatus, FinalDecision
from backend.execution.validator import TradeValidator
from backend.journal.audit import AuditLogger
from backend.journal.decisions import DecisionJournal
from backend.market.models import MarketContext
from backend.portfolio.monitor import PortfolioMonitor, PortfolioSnapshot
from backend.portfolio.performance import PerformanceStats, compute_performance
from backend.quant.models import Opportunity
from backend.quant.pipeline import generate_opportunities
from backend.risk.governor import RiskGovernor
from backend.risk.models import RiskVerdict

router = APIRouter(prefix="/api")

# In-memory cache of the most recent opportunities (id -> opportunity/verdict).
# Enough for the dashboard and Phase 5 decision/execution lookups.
_OPPORTUNITY_CACHE: "dict[str, tuple[Opportunity, RiskVerdict]]" = {}
# Cache of the most recent decisions (opportunity_id -> decision/opp/journal row id).
_DECISION_CACHE: "dict[str, tuple[FinalDecision, Opportunity, int]]" = {}
_CACHE_LIMIT = 200


def _require_alpaca() -> AlpacaAdapter:
    settings = get_settings()
    if not settings.use_demo_data and not settings.alpaca_configured:
        raise HTTPException(status_code=503, detail="Alpaca is not configured.")
    return get_adapter(settings)


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return system health based on the diagnostic report. Never trades."""
    settings = get_settings()
    report = run_diagnostics(settings)
    return HealthResponse(
        status="ok" if report.healthy else "degraded",
        version=__version__,
        demo_mode=settings.demo_mode,
        paper_trading=settings.alpaca_paper_trade,
        checks=[CheckResult(**c.__dict__) for c in report.checks],
    )


@router.get("/account", response_model=AccountResponse, tags=["account"])
async def account() -> AccountResponse:
    """Return the (paper) trading account snapshot."""
    adapter = _require_alpaca()
    try:
        acct = await adapter.get_account()
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AccountResponse(**acct.model_dump())


@router.get("/clock", response_model=ClockResponse, tags=["market"])
async def clock() -> ClockResponse:
    """Return the market clock."""
    adapter = _require_alpaca()
    try:
        c = await adapter.get_clock()
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ClockResponse(**c.model_dump())


@router.get("/market/{symbol}", response_model=MarketResponse, tags=["market"])
async def market(symbol: str) -> MarketResponse:
    """Return a market snapshot (price + latest quote) for a symbol."""
    adapter = _require_alpaca()
    symbol = symbol.upper()
    try:
        snapshot: StockSnapshot = await adapter.get_market_snapshot(symbol)
        quote: StockQuote = await adapter.get_stock_quote(symbol)
    except InvalidQuoteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return MarketResponse(
        symbol=symbol,
        price=snapshot.price,
        bid=quote.bid,
        ask=quote.ask,
        mid=quote.mid,
        change=snapshot.change,
        change_percent=snapshot.change_percent,
        day_high=snapshot.day_high,
        day_low=snapshot.day_low,
        day_volume=snapshot.day_volume,
    )


@router.get("/options/{symbol}", response_model=OptionChainResponse, tags=["options"])
async def options(
    symbol: str,
    expiration_gte: date | None = Query(default=None),
    expiration_lte: date | None = Query(default=None),
    strike_gte: float | None = Query(default=None),
    strike_lte: float | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
) -> OptionChainResponse:
    """Return an option chain snapshot for an underlying (read-only)."""
    adapter = _require_alpaca()
    symbol = symbol.upper()
    try:
        chain: OptionChain = await adapter.get_option_chain(
            symbol,
            expiration_gte=expiration_gte,
            expiration_lte=expiration_lte,
            strike_gte=strike_gte,
            strike_lte=strike_lte,
        )
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    contracts = [
        OptionContractResponse(
            symbol=c.symbol,
            underlying=c.underlying,
            expiration=c.expiration,
            strike=c.strike,
            option_type=c.option_type.value,
            bid=c.bid,
            ask=c.ask,
            mid=c.mid,
            last=c.last,
            volume=c.volume,
            open_interest=c.open_interest,
            implied_volatility=c.implied_volatility,
            spread_percent=c.spread_percent,
            greeks=GreeksResponse(**c.greeks.model_dump()),
        )
        for c in chain.contracts[:limit]
    ]
    return OptionChainResponse(
        underlying=chain.underlying,
        count=chain.count,
        expirations=chain.expirations(),
        contracts=contracts,
    )


def _regime_response(context: MarketContext) -> RegimeResponse:
    return RegimeResponse(
        symbol=context.symbol,
        price=context.price,
        regime=context.regime.value,
        directional_bias=context.directional_bias,
        change_percent=context.change_percent,
        implied_volatility=context.implied_volatility,
        notes=context.notes,
    )


def _verdict_response(verdict: RiskVerdict) -> RiskVerdictResponse:
    sizing = None
    if verdict.sizing is not None:
        sizing = SizingResponse(
            contracts=verdict.sizing.contracts,
            max_position_risk=verdict.sizing.max_position_risk,
            total_max_loss=verdict.sizing.total_max_loss,
            executable=verdict.sizing.executable,
            reason=verdict.sizing.reason,
        )
    return RiskVerdictResponse(status=verdict.status.value, reasons=verdict.reasons, sizing=sizing)


def _opportunity_response(opp: Opportunity, verdict: RiskVerdict) -> OpportunityResponse:
    legs = [
        LegResponse(
            symbol=leg.contract.symbol,
            strike=leg.contract.strike,
            option_type=leg.contract.option_type.value,
            action=leg.action.value,
        )
        for leg in opp.candidate.legs
    ]
    m = opp.metrics
    return OpportunityResponse(
        id=opp.id,
        symbol=opp.symbol,
        strategy=opp.strategy,
        expiration=opp.candidate.expiration,
        dte=opp.candidate.dte,
        legs=legs,
        entry_price=opp.candidate.entry_price,
        net_premium=opp.candidate.net_premium,
        max_profit=opp.candidate.max_profit,
        max_loss=opp.candidate.max_loss,
        breakevens=opp.candidate.breakevens,
        probability_of_profit=m.probability_of_profit,
        expected_value=m.expected_value,
        risk_reward=m.risk_reward,
        liquidity_score=m.liquidity_score,
        volatility_score=m.volatility_score,
        alpha_score=m.alpha_score,
        risk_score=m.risk_score,
        confidence=m.confidence,
        implied_volatility=m.implied_volatility,
        market_regime=opp.market_regime.value,
        invalidation_conditions=opp.invalidation_conditions,
        risk_governor=_verdict_response(verdict),
    )


def _cache_put(opp: Opportunity, verdict: RiskVerdict) -> None:
    if len(_OPPORTUNITY_CACHE) >= _CACHE_LIMIT:
        _OPPORTUNITY_CACHE.pop(next(iter(_OPPORTUNITY_CACHE)))
    _OPPORTUNITY_CACHE[opp.id] = (opp, verdict)


@router.get("/opportunities/{symbol}", response_model=OpportunitiesResponse, tags=["opportunities"])
async def opportunities(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> OpportunitiesResponse:
    """Run the deterministic pipeline and return ranked, risk-checked opportunities."""
    adapter = _require_alpaca()
    symbol = symbol.upper()
    try:
        account = await adapter.get_account()
        result = await generate_opportunities(adapter, symbol)
    except InvalidQuoteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    governor = RiskGovernor()
    items: list[OpportunityResponse] = []
    for opp in result.opportunities[:limit]:
        verdict = governor.evaluate(opp, account_equity=account.equity)
        _cache_put(opp, verdict)
        items.append(_opportunity_response(opp, verdict))

    qualified = sum(1 for i in items if i.risk_governor.status == "PASS")
    return OpportunitiesResponse(
        symbol=symbol,
        regime=_regime_response(result.context),
        candidates_considered=len(result.scan.candidates),
        qualified=qualified,
        opportunities=items,
    )


@router.post("/analyze", response_model=AlphaAssessment, tags=["agents"])
async def analyze(payload: AnalyzeRequest) -> AlphaAssessment:
    """Run the AI Analyst + Adversarial Agent over a cached opportunity.

    The opportunity must first appear via ``GET /api/opportunities/{symbol}``.
    The generative layer has no execution authority.
    """
    cached = _OPPORTUNITY_CACHE.get(payload.opportunity_id)
    if cached is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown opportunity_id. Run GET /api/opportunities/{symbol} first.",
        )
    opportunity, _verdict = cached
    agent = OptionsAlphaAgent()
    return await agent.analyze(opportunity, payload.language)


def _open_trades_count() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE status IN "
            "('pending', 'PAPER_SUBMITTED', 'PAPER_SIMULATED')"
        ).fetchone()
    return int(row["n"]) if row else 0


def _existing_client_order_ids() -> set[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT client_order_id FROM orders").fetchall()
    return {r["client_order_id"] for r in rows}


@router.post("/decision", response_model=FinalDecision, tags=["decision"])
async def decision(payload: DecideRequest) -> FinalDecision:
    """Converge agents + Risk Governor into a final EXECUTE / NO_TRADE decision.

    Persists the decision to the journal. Does NOT place an order.
    """
    cached = _OPPORTUNITY_CACHE.get(payload.opportunity_id)
    if cached is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown opportunity_id. Run GET /api/opportunities/{symbol} first.",
        )
    opportunity, _verdict = cached
    adapter = _require_alpaca()
    try:
        account = await adapter.get_account()
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    engine = DecisionEngine()
    final = await engine.decide(
        opportunity,
        account_equity=account.equity,
        open_trades_count=_open_trades_count(),
        lang=payload.language,
    )
    row_id = DecisionJournal().save(final)
    _DECISION_CACHE[payload.opportunity_id] = (final, opportunity, row_id)
    return final


@router.post("/execute", response_model=OrderResultResponse, tags=["execution"])
async def execute(payload: ExecuteRequest) -> OrderResultResponse:
    """Validate and submit a PAPER order for a prior EXECUTE decision.

    Requires ``confirm=true``. Never executes automatically.
    """
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Execution requires confirm=true.")

    cached = _DECISION_CACHE.get(payload.opportunity_id)
    if cached is None:
        raise HTTPException(
            status_code=404, detail="No decision for this opportunity. Run POST /api/decision first."
        )
    final, opportunity, row_id = cached
    if final.decision is not DecisionOutcome.EXECUTE:
        raise HTTPException(status_code=409, detail=f"Decision is {final.decision.value}; nothing to execute.")

    adapter = _require_alpaca()
    try:
        account = await adapter.get_account()
        clock = await adapter.get_clock()
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    validation = TradeValidator().validate(
        opportunity,
        final,
        account=account,
        clock=clock,
        existing_client_order_ids=_existing_client_order_ids(),
    )
    if not validation.ready:
        raise HTTPException(status_code=422, detail="; ".join(validation.reasons))

    result = await ExecutionEngine(adapter).execute(opportunity, final)
    final.order_id = result.broker_order_id
    final.execution_status = result.status
    DecisionJournal().update_execution(row_id, result.status.value, result.broker_order_id)
    return OrderResultResponse(**result.model_dump())


@router.get("/positions", response_model=list[PositionResponse], tags=["portfolio"])
async def positions() -> list[PositionResponse]:
    """Return open (paper) positions."""
    adapter = _require_alpaca()
    try:
        items = await adapter.get_positions()
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [
        PositionResponse(
            symbol=p.symbol,
            asset_class=p.asset_class,
            qty=p.qty,
            side=p.side,
            market_value=p.market_value,
            unrealized_pl=p.unrealized_pl,
        )
        for p in items
    ]


@router.get("/orders", tags=["execution"])
def orders() -> list[dict]:
    """Return ORION's order journal (locally tracked orders)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT created_at, client_order_id, symbol, strategy, status, broker_order_id "
            "FROM orders ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/decisions", tags=["decision"])
def decisions(symbol: str | None = Query(default=None), decision: str | None = Query(default=None)) -> list[dict]:
    """Return the decision journal (searchable by symbol / decision)."""
    journal = DecisionJournal()
    if symbol or decision:
        return journal.search(symbol=symbol, decision=decision, limit=100)
    return journal.recent(limit=100)


@router.get("/audit", tags=["system"])
def audit() -> list[dict]:
    """Return the audit trail."""
    return AuditLogger().recent(limit=100)


@router.get("/portfolio", response_model=PortfolioSnapshot, tags=["portfolio"])
async def portfolio() -> PortfolioSnapshot:
    """Return an aggregated portfolio snapshot."""
    adapter = _require_alpaca()
    try:
        return await PortfolioMonitor(adapter).snapshot()
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/performance", tags=["performance"])
def performance() -> dict:
    """Realized performance from the decision journal + decision-quality counts."""
    journal = DecisionJournal()
    stats = compute_performance(journal.performance_pnls())
    return {"realized": stats.model_dump(), "decision_counts": journal.decision_counts()}


@router.post("/backtest", response_model=BacktestReport, tags=["performance"])
async def backtest(payload: BacktestRequest) -> BacktestReport:
    """Monte-Carlo simulate the top opportunities for a symbol (not a guarantee)."""
    adapter = _require_alpaca()
    try:
        result = await generate_opportunities(adapter, payload.symbol)
    except InvalidQuoteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AlpacaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    opportunities = result.opportunities[: payload.limit]
    if not opportunities:
        raise HTTPException(status_code=404, detail="No opportunities to backtest.")
    return BacktestEngine().run(opportunities, spot=result.context.price, samples=payload.samples)





