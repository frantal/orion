import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./services/api.js";
import { useI18n } from "./i18n.jsx";
import DecisionPipeline from "./components/DecisionPipeline.jsx";
import ScoreBar from "./components/ScoreBar.jsx";

const money = (v) =>
  v == null ? "—" : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

export default function App() {
  const { lang, setLang, t, tk } = useI18n();
  const [symbol, setSymbol] = useState("SPY");
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null); // opportunities response
  const [account, setAccount] = useState(null);
  const [clock, setClock] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [decision, setDecision] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState(null);
  const [recent, setRecent] = useState([]);
  const [positions, setPositions] = useState([]);
  const [backtest, setBacktest] = useState(null);
  const [btLoading, setBtLoading] = useState(false);

  const selected = useMemo(
    () => data?.opportunities?.find((o) => o.id === selectedId) || null,
    [data, selectedId]
  );

  const refreshJournals = useCallback(async () => {
    try {
      const [d, p] = await Promise.all([api.decisions(), api.positions()]);
      setRecent(d);
      setPositions(p);
    } catch (_) {
      /* non-fatal */
    }
  }, []);

  const loadDetail = useCallback(
    async (id) => {
      setDetailLoading(true);
      setAnalysis(null);
      setDecision(null);
      setExecResult(null);
      try {
        const [a, d] = await Promise.all([api.analyze(id, lang), api.decide(id, lang)]);
        setAnalysis(a);
        setDecision(d);
        refreshJournals();
      } catch (e) {
        setError(e.message);
      } finally {
        setDetailLoading(false);
      }
    },
    [refreshJournals, lang]
  );

  const scan = useCallback(
    async (sym) => {
      setScanning(true);
      setError("");
      setSelectedId(null);
      setAnalysis(null);
      setDecision(null);
      setExecResult(null);
      try {
        const res = await api.opportunities(sym, 10);
        setData(res);
        if (res.opportunities.length) {
          setSelectedId(res.opportunities[0].id);
          loadDetail(res.opportunities[0].id);
        }
      } catch (e) {
        setError(e.message);
        setData(null);
      } finally {
        setScanning(false);
      }
    },
    [loadDetail]
  );

  useEffect(() => {
    (async () => {
      try {
        const [a, c] = await Promise.all([api.account(), api.clock()]);
        setAccount(a);
        setClock(c);
      } catch (_) {
        /* backend may be booting */
      }
      scan("SPY");
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-fetch the narrative (thesis / decision) in the newly selected language.
  useEffect(() => {
    if (selectedId) loadDetail(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  const onExecute = async () => {
    if (!selectedId) return;
    setExecuting(true);
    setError("");
    try {
      const r = await api.execute(selectedId, true);
      setExecResult(r);
      refreshJournals();
      setAccount(await api.account());
    } catch (e) {
      setError(e.message);
    } finally {
      setExecuting(false);
    }
  };

  const onBacktest = async () => {
    setBtLoading(true);
    setError("");
    try {
      setBacktest(await api.backtest(symbol, 3000, 5));
    } catch (e) {
      setError(e.message);
    } finally {
      setBtLoading(false);
    }
  };

  const stages = useMemo(
    () => buildStages({ data, selected, analysis, decision, execResult, tk }),
    [data, selected, analysis, decision, execResult, tk]
  );

  const highAlpha = data?.opportunities?.filter((o) => o.alpha_score >= 80).length || 0;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <h1>ORION</h1>
          <span className="tag">{t("tagline")}</span>
        </div>
        <div className="header-right">
          <div className="controls">
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && scan(symbol)}
              maxLength={6}
            />
            <button onClick={() => scan(symbol)} disabled={scanning}>
              {scanning ? t("scanning") : t("scan")}
            </button>
          </div>
          <div className="lang">
            <button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button>
            <button className={lang === "pt" ? "active" : ""} onClick={() => setLang("pt")}>PT</button>
          </div>
          <span className="pill paper">{t("paper")}</span>
          <span className="pill">{clock ? (clock.is_open ? t("marketOpen") : t("marketClosed")) : "…"}</span>
        </div>
      </header>

      <DecisionPipeline stages={stages} title={t("decisionEngine")} />

      <div className="grid" style={{ marginTop: 18 }}>
        <div className="col">
          <MarketPanel regime={data?.regime} />
          <StatusPanel data={data} highAlpha={highAlpha} />
          <OpportunitiesPanel
            data={data}
            selectedId={selectedId}
            onSelect={(id) => {
              setSelectedId(id);
              loadDetail(id);
            }}
          />
        </div>

        <div className="col">
          <OpportunityDetail selected={selected} decision={decision} loading={detailLoading} />
          <ThesisPanel analysis={analysis} loading={detailLoading} />
          <DecisionPanel
            decision={decision}
            executing={executing}
            execResult={execResult}
            onExecute={onExecute}
            loading={detailLoading}
          />
          {error && <div className="error">⚠ {error}</div>}
        </div>

        <div className="col">
          <GovernorPanel decision={decision} />
          <PreviewPanel decision={decision} />
          <PortfolioPanel account={account} positions={positions} />
          <BacktestPanel backtest={backtest} loading={btLoading} onRun={onBacktest} />
          <RecentPanel recent={recent} />
        </div>
      </div>

      <div className="footnote">{t("footnote")}</div>

      {execResult && (
        <div className="toast">
          {t("order")} {tk(execResult.status)} · {execResult.broker_order_id || "—"}
        </div>
      )}
    </div>
  );
}

/* ---------- Panels ---------- */

function MarketPanel({ regime }) {
  const { t, tk } = useI18n();
  if (!regime) return <SkeletonPanel title={t("marketRegime")} />;
  const chg = regime.change_percent;
  return (
    <div className="panel">
      <h2>{t("marketRegime")}</h2>
      <div className={`regime-badge regime-${regime.regime}`}>{tk(regime.regime)}</div>
      <div className="price">
        {regime.symbol} <small>{money(regime.price)}</small>
      </div>
      <div className={`change ${chg >= 0 ? "up" : "down"}`} style={{ fontFamily: "var(--mono)", marginTop: 4 }}>
        {chg == null ? "" : `${chg >= 0 ? "+" : ""}${chg.toFixed(2)}%`}
        <span className={`bias-${regime.directional_bias}`} style={{ marginLeft: 10, fontSize: 12 }}>
          {tk(regime.directional_bias)}
        </span>
      </div>
      {regime.implied_volatility != null && (
        <div className="stat-row" style={{ marginTop: 12 }}>
          <span className="k">{t("impliedVolatility")}</span>
          <span className="v">{(regime.implied_volatility * 100).toFixed(1)}%</span>
        </div>
      )}
    </div>
  );
}

function StatusPanel({ data, highAlpha }) {
  const { t } = useI18n();
  return (
    <div className="panel">
      <h2>{t("orionStatus")}</h2>
      <div className="metrics">
        <div className="metric">
          <div className="n">{data?.candidates_considered ?? "—"}</div>
          <div className="l">{t("candidates")}</div>
        </div>
        <div className="metric">
          <div className="n">{data?.qualified ?? "—"}</div>
          <div className="l">{t("qualified")}</div>
        </div>
        <div className="metric">
          <div className="n">{data ? highAlpha : "—"}</div>
          <div className="l">{t("highAlpha")}</div>
        </div>
      </div>
    </div>
  );
}

function OpportunitiesPanel({ data, selectedId, onSelect }) {
  const { t, tk } = useI18n();
  if (!data) return <SkeletonPanel title={t("opportunities")} />;
  return (
    <div className="panel">
      <h2>{t("opportunities")}</h2>
      <div className="opp-list">
        {data.opportunities.length === 0 && <div className="muted">{t("noCandidates")}</div>}
        {data.opportunities.map((o) => {
          const pass = o.risk_governor.status === "PASS";
          return (
            <div
              key={o.id}
              className={`opp ${o.id === selectedId ? "selected" : ""}`}
              onClick={() => onSelect(o.id)}
            >
              <div>
                <div className="strat">{tk(o.strategy)}</div>
                <div className="sub">
                  {o.dte}DTE · {t("ev")} {money(o.expected_value)} ·{" "}
                  <span className={pass ? "tag-pass" : "tag-veto"}>{tk(o.risk_governor.status)}</span>
                </div>
              </div>
              <div className="alpha">{o.alpha_score.toFixed(0)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function OpportunityDetail({ selected, decision, loading }) {
  const { t, tk } = useI18n();
  if (!selected) return <SkeletonPanel title={t("topOpportunity")} spinner={loading} />;
  const alpha = decision?.alpha_score ?? selected.alpha_score;
  return (
    <div className="panel">
      <h2>{t("topOpportunity")} — {selected.symbol}</h2>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
        <div style={{ fontSize: 18, fontWeight: 700 }}>{tk(selected.strategy)}</div>
        <div className="muted" style={{ fontFamily: "var(--mono)" }}>
          {selected.expiration} · {selected.dte}DTE
        </div>
      </div>
      <div className="scores">
        <ScoreBar label={t("alphaScore")} value={alpha} kind="alpha" />
        <ScoreBar label={t("riskScore")} value={selected.risk_score} kind="risk" />
        <ScoreBar label={t("liquidity")} value={selected.liquidity_score} kind="liq" />
        <ScoreBar label={t("probProfit")} value={selected.probability_of_profit * 100} kind="pop" suffix="%" />
      </div>
      <div style={{ display: "flex", gap: 18, marginTop: 14, fontFamily: "var(--mono)", fontSize: 13 }}>
        <span className="muted">{t("ev")}</span> {money(selected.expected_value)}
        <span className="muted">{t("rr")}</span> {selected.risk_reward.toFixed(2)}
        <span className="muted">{t("maxLoss")}</span> {money(selected.max_loss)}
        <span className="muted">{t("maxProfit")}</span> {selected.max_profit == null ? "∞" : money(selected.max_profit)}
      </div>
    </div>
  );
}

function ThesisPanel({ analysis, loading }) {
  const { t, tk } = useI18n();
  if (!analysis) return <SkeletonPanel title={t("aiThesis")} spinner={loading} />;
  const a = analysis.analyst;
  const adv = analysis.adversarial;
  return (
    <div className="panel">
      <h2>
        {t("aiThesis")}
        <span className={`reco ${a.recommendation}`}>{tk(a.recommendation)}</span>
        <span className="muted" style={{ marginLeft: 8, fontSize: 11 }}>
          {analysis.llm_used ? t("llm") : t("deterministic")} · {t("conf")} {a.confidence.toFixed(0)}
        </span>
      </h2>
      <div className="thesis-text">{a.thesis}</div>
      {a.evidence?.length > 0 && (
        <ul className="list">
          {a.evidence.slice(0, 4).map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}
      <h2 style={{ marginTop: 18 }}>
        {t("adversarialChallenge")}
        <span className={`reco ${adv.recommended_action}`}>{tk(adv.recommended_action)}</span>
        <span className="muted" style={{ marginLeft: 8, fontSize: 11 }}>
          {t("penalty")} −{adv.alpha_penalty.toFixed(1)}
        </span>
      </h2>
      <div className="counter-text">{adv.counter_thesis}</div>
      {adv.risk_factors?.length > 0 && (
        <ul className="list">
          {adv.risk_factors.slice(0, 4).map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function GovernorPanel({ decision }) {
  const { t, tk } = useI18n();
  if (!decision) return <SkeletonPanel title={t("riskGovernor")} />;
  return (
    <div className="panel">
      <h2>{t("riskGovernor")}</h2>
      <div className={`verdict ${decision.risk_governor}`}>
        <span className="big">{tk(decision.risk_governor)}</span>
        <span className="muted">{t("governorSub")}</span>
      </div>
    </div>
  );
}

function DecisionPanel({ decision, executing, execResult, onExecute, loading }) {
  const { t, tk } = useI18n();
  if (!decision) return <SkeletonPanel title={t("finalDecision")} spinner={loading} />;
  const isExec = decision.decision === "EXECUTE";
  return (
    <div className={`decision ${decision.decision}`}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="big">{tk(decision.decision)}</span>
        {isExec && !execResult && (
          <button className="exec" onClick={onExecute} disabled={executing}>
            {executing ? t("submitting") : t("executePaperTrade")}
          </button>
        )}
        {execResult && <span className="reco TRADE">{tk(execResult.status)}</span>}
      </div>
      <div className="reason">{decision.reason}</div>
    </div>
  );
}

function PreviewPanel({ decision }) {
  const { t, tk } = useI18n();
  if (!decision) return <SkeletonPanel title={t("executionPreview")} />;
  const p = decision.preview;
  return (
    <div className="panel">
      <h2>{t("executionPreview")}</h2>
      <div className="preview">
        <Row k={t("strategy")} v={tk(p.strategy)} />
        <Row k={t("underlying")} v={p.underlying} />
        <Row k={t("expiration")} v={p.expiration} />
        {p.legs.map((l, i) => (
          <Row key={i} k={i === 0 ? t("legs") : ""} v={l} />
        ))}
        <Row k={p.net_type === "debit" ? t("estDebit") : t("estCredit")} v={`$${p.net_amount.toFixed(2)}`} />
        <Row k={t("contracts")} v={p.contracts} />
        <Row k={t("total")} v={money(p.total_debit_credit)} />
        <Row k={t("maxLoss")} v={money(p.max_loss)} />
        <Row k={t("maxProfit")} v={p.max_profit == null ? "∞" : money(p.max_profit)} />
        <Row k={t("riskReward")} v={`1 : ${p.risk_reward.toFixed(2)}`} />
        <Row k={t("adversarialConf")} v={`${p.adversarial_confidence.toFixed(0)}%`} />
      </div>
    </div>
  );
}

function PortfolioPanel({ account, positions }) {
  const { t } = useI18n();
  if (!account) return <SkeletonPanel title={t("portfolio")} />;
  return (
    <div className="panel">
      <h2>{t("portfolio")}</h2>
      <div className="stat-row"><span className="k">{t("equity")}</span><span className="v">{money(account.equity)}</span></div>
      <div className="stat-row"><span className="k">{t("buyingPower")}</span><span className="v">{money(account.buying_power)}</span></div>
      <div className="stat-row"><span className="k">{t("cash")}</span><span className="v">{money(account.cash)}</span></div>
      <div className="stat-row"><span className="k">{t("openPositions")}</span><span className="v">{positions.length}</span></div>
    </div>
  );
}

function BacktestPanel({ backtest, loading, onRun }) {
  const { t, tk } = useI18n();
  const best = backtest?.per_strategy?.reduce(
    (b, s) => (!b || s.performance.expectancy > b.performance.expectancy ? s : b),
    null
  );
  return (
    <div className="panel">
      <h2>
        {t("backtestTitle")}
        <button style={{ float: "right", padding: "4px 10px", fontSize: 11 }} onClick={onRun} disabled={loading}>
          {loading ? t("running") : t("run")}
        </button>
      </h2>
      {!backtest && <div className="muted">{t("backtestHint")}</div>}
      {backtest && (
        <>
          <div className="stat-row"><span className="k">{t("simulatedTrades")}</span><span className="v">{backtest.aggregate.num_trades.toLocaleString()}</span></div>
          <div className="stat-row"><span className="k">{t("winRate")}</span><span className="v">{(backtest.aggregate.win_rate * 100).toFixed(1)}%</span></div>
          <div className="stat-row"><span className="k">{t("expectancyTrade")}</span><span className="v">{money(backtest.aggregate.expectancy)}</span></div>
          <div className="stat-row"><span className="k">{t("profitFactor")}</span><span className="v">{backtest.aggregate.profit_factor ?? "∞"}</span></div>
          <div className="stat-row"><span className="k">{t("sharpe")}</span><span className="v">{backtest.aggregate.sharpe ?? "—"}</span></div>
          {best && (
            <div className="muted" style={{ marginTop: 10 }}>
              {t("best")}: <b style={{ color: "var(--accent)" }}>{tk(best.strategy)}</b> · exp {money(best.performance.expectancy)} · {(best.performance.win_rate * 100).toFixed(0)}%
            </div>
          )}
          <div className="muted" style={{ marginTop: 8, fontSize: 10, lineHeight: 1.4 }}>{backtest.disclaimer}</div>
        </>
      )}
    </div>
  );
}

function RecentPanel({ recent }) {
  const { t, tk } = useI18n();
  return (
    <div className="panel">
      <h2>{t("recentDecisions")}</h2>
      <div className="recent">
        {recent.length === 0 && <div className="muted">{t("noDecisions")}</div>}
        {recent.slice(0, 8).map((r, i) => (
          <div className="r" key={i}>
            <span className="sym">{r.symbol} · {tk(r.strategy)}</span>
            <span className={`badge ${r.decision}`}>{tk(r.decision)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Helpers ---------- */

function Row({ k, v }) {
  return (
    <div className="row">
      <span className="k">{k}</span>
      <span>{v}</span>
    </div>
  );
}

function SkeletonPanel({ title, spinner }) {
  const { t } = useI18n();
  return (
    <div className="panel">
      <h2>{title}</h2>
      <div className={spinner ? "spinner" : "muted"}>{spinner ? t("analyzing") : "—"}</div>
    </div>
  );
}

function buildStages({ data, selected, analysis, decision, execResult, tk }) {
  const s = (name, ok, value, cls) => ({ name, value: ok ? value : "—", cls: ok ? cls : "pending" });
  return [
    s("s_market", !!data?.regime, tk(data?.regime?.regime), "pass"),
    s("s_opportunity", !!data, data ? `${data.qualified}/${data.candidates_considered}` : "", "pass"),
    s("s_quant", !!selected, selected?.alpha_score?.toFixed(0), "pass"),
    s("s_aiThesis", !!analysis, tk(analysis?.analyst?.recommendation), analysis?.analyst?.recommendation === "NO_TRADE" ? "veto" : "pass"),
    s("s_adversarial", !!analysis, tk(analysis?.adversarial?.recommended_action), analysis?.adversarial?.recommended_action === "REJECT" ? "veto" : "pass"),
    s("s_risk", !!decision, tk(decision?.risk_governor), decision?.risk_governor === "VETO" ? "veto" : "pass"),
    s("s_decision", !!decision, tk(decision?.decision), decision?.decision === "NO_TRADE" ? "veto" : "pass"),
    s("s_execution", !!execResult, tk(execResult?.status), "pass"),
  ];
}
