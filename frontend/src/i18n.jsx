import React, { createContext, useCallback, useContext, useState } from "react";

// UI string catalogue. The decision pipeline is unaffected — only presentation.
const STRINGS = {
  en: {
    tagline: "Autonomous Options Alpha Agent",
    paper: "Paper",
    marketOpen: "Market Open",
    marketClosed: "Market Closed",
    scan: "SCAN",
    scanning: "SCANNING…",
    decisionEngine: "Decision Engine",
    s_market: "Market",
    s_opportunity: "Opportunity",
    s_quant: "Quant",
    s_aiThesis: "AI Thesis",
    s_adversarial: "Adversarial",
    s_risk: "Risk",
    s_decision: "Decision",
    s_execution: "Execution",
    marketRegime: "Market Regime",
    orionStatus: "ORION Status",
    candidates: "Candidates",
    qualified: "Qualified",
    highAlpha: "High Alpha",
    opportunities: "Opportunities",
    noCandidates: "No candidates found.",
    impliedVolatility: "Implied Volatility",
    topOpportunity: "Top Opportunity",
    alphaScore: "Alpha Score",
    riskScore: "Risk Score",
    liquidity: "Liquidity",
    probProfit: "Prob. of Profit",
    ev: "EV",
    rr: "R:R",
    maxLoss: "Max Loss",
    maxProfit: "Max Profit",
    aiThesis: "AI Thesis",
    adversarialChallenge: "Adversarial Challenge",
    conf: "conf",
    penalty: "penalty",
    deterministic: "deterministic",
    llm: "LLM",
    riskGovernor: "Risk Governor",
    governorSub: "deterministic · independent",
    finalDecision: "Final Decision",
    executePaperTrade: "EXECUTE PAPER TRADE",
    submitting: "SUBMITTING…",
    executionPreview: "Execution Preview",
    strategy: "Strategy",
    underlying: "Underlying",
    expiration: "Expiration",
    legs: "Legs",
    estDebit: "Est. Debit",
    estCredit: "Est. Credit",
    contracts: "Contracts",
    total: "Total",
    riskReward: "Risk / Reward",
    adversarialConf: "Adversarial Conf",
    portfolio: "Portfolio",
    equity: "Equity",
    buyingPower: "Buying Power",
    cash: "Cash",
    openPositions: "Open Positions",
    backtestTitle: "Backtest — Simulated",
    run: "RUN",
    running: "RUNNING…",
    backtestHint: "Monte-Carlo simulation of top opportunities.",
    simulatedTrades: "Simulated Trades",
    winRate: "Win Rate",
    expectancyTrade: "Expectancy / Trade",
    profitFactor: "Profit Factor",
    sharpe: "Sharpe (approx)",
    best: "Best",
    recentDecisions: "Recent Decisions",
    noDecisions: "No decisions yet.",
    footnote:
      "ORION — “The agent that has to prove its trade.” · Paper trading only · No live orders.",
    analyzing: "ANALYZING…",
    order: "Order",
  },
  pt: {
    tagline: "Agente Autónomo de Alpha em Opções",
    paper: "Simulado",
    marketOpen: "Mercado Aberto",
    marketClosed: "Mercado Fechado",
    scan: "ANALISAR",
    scanning: "A ANALISAR…",
    decisionEngine: "Motor de Decisão",
    s_market: "Mercado",
    s_opportunity: "Oportunidade",
    s_quant: "Quant",
    s_aiThesis: "Tese IA",
    s_adversarial: "Adversarial",
    s_risk: "Risco",
    s_decision: "Decisão",
    s_execution: "Execução",
    marketRegime: "Regime de Mercado",
    orionStatus: "Estado do ORION",
    candidates: "Candidatos",
    qualified: "Qualificados",
    highAlpha: "Alto Alpha",
    opportunities: "Oportunidades",
    noCandidates: "Nenhum candidato encontrado.",
    impliedVolatility: "Volatilidade Implícita",
    topOpportunity: "Melhor Oportunidade",
    alphaScore: "Score Alpha",
    riskScore: "Score de Risco",
    liquidity: "Liquidez",
    probProfit: "Prob. de Lucro",
    ev: "VE",
    rr: "R:R",
    maxLoss: "Perda Máx.",
    maxProfit: "Lucro Máx.",
    aiThesis: "Tese IA",
    adversarialChallenge: "Desafio Adversarial",
    conf: "conf",
    penalty: "penalização",
    deterministic: "determinístico",
    llm: "LLM",
    riskGovernor: "Governador de Risco",
    governorSub: "determinístico · independente",
    finalDecision: "Decisão Final",
    executePaperTrade: "EXECUTAR (SIMULADO)",
    submitting: "A SUBMETER…",
    executionPreview: "Pré-visualização da Execução",
    strategy: "Estratégia",
    underlying: "Ativo Base",
    expiration: "Vencimento",
    legs: "Pernas",
    estDebit: "Débito Est.",
    estCredit: "Crédito Est.",
    contracts: "Contratos",
    total: "Total",
    riskReward: "Risco / Retorno",
    adversarialConf: "Conf. Adversarial",
    portfolio: "Carteira",
    equity: "Património",
    buyingPower: "Poder de Compra",
    cash: "Numerário",
    openPositions: "Posições Abertas",
    backtestTitle: "Backtest — Simulado",
    run: "CORRER",
    running: "A CORRER…",
    backtestHint: "Simulação Monte-Carlo das melhores oportunidades.",
    simulatedTrades: "Trades Simulados",
    winRate: "Taxa de Acerto",
    expectancyTrade: "Expectativa / Trade",
    profitFactor: "Fator de Lucro",
    sharpe: "Sharpe (aprox.)",
    best: "Melhor",
    recentDecisions: "Decisões Recentes",
    noDecisions: "Ainda sem decisões.",
    footnote:
      "ORION — “O agente que tem de provar o seu trade.” · Apenas simulado · Sem ordens reais.",
    analyzing: "A ANALISAR…",
    order: "Ordem",
  },
};

// Enum-like tokens returned by the backend. Class names always use the raw token;
// only the displayed text is localised here.
const TOKENS = {
  en: {
    NO_TRADE: "NO TRADE",
    EXECUTE: "EXECUTE",
  },
  pt: {
    // Decision / recommendation / action
    EXECUTE: "EXECUTAR",
    NO_TRADE: "NÃO OPERAR",
    TRADE: "OPERAR",
    WATCH: "OBSERVAR",
    PROCEED: "PROSSEGUIR",
    REDUCE: "REDUZIR",
    REJECT: "REJEITAR",
    PASS: "APROVADO",
    VETO: "VETO",
    // Regime
    BULLISH: "ALTA",
    BEARISH: "BAIXA",
    NEUTRAL: "NEUTRO",
    HIGH_VOLATILITY: "VOLAT. ALTA",
    LOW_VOLATILITY: "VOLAT. BAIXA",
    EVENT_DRIVEN: "EVENTOS",
    UNCERTAIN: "INCERTO",
    // Directional bias
    bullish: "alta",
    bearish: "baixa",
    neutral: "neutro",
    // Strategies
    "Long Call": "Compra de Call",
    "Long Put": "Compra de Put",
    "Bull Call Spread": "Spread de Alta (Call)",
    "Bear Put Spread": "Spread de Baixa (Put)",
    "Bull Put Spread": "Spread de Alta (Put)",
    "Bear Call Spread": "Spread de Baixa (Call)",
    // Execution status
    PAPER_SIMULATED: "SIMULADO",
    PAPER_SUBMITTED: "SUBMETIDO",
    REJECTED: "REJEITADO",
    ERROR: "ERRO",
  },
};

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(
    () => (typeof localStorage !== "undefined" && localStorage.getItem("orion_lang")) || "en"
  );

  const setLang = useCallback((l) => {
    try {
      localStorage.setItem("orion_lang", l);
    } catch (_) {
      /* ignore */
    }
    setLangState(l);
  }, []);

  const t = useCallback(
    (key) => (STRINGS[lang] && STRINGS[lang][key]) || STRINGS.en[key] || key,
    [lang]
  );

  // Localise a backend enum/token for display (falls back to the raw token).
  const tk = useCallback(
    (token) => {
      if (token == null) return token;
      const map = TOKENS[lang] || {};
      if (map[token] != null) return map[token];
      return TOKENS.en[token] != null ? TOKENS.en[token] : token;
    },
    [lang]
  );

  return (
    <I18nContext.Provider value={{ lang, setLang, t, tk }}>{children}</I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
