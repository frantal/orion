# ORION — AUTONOMOUS OPTIONS ALPHA AGENT
## MASTER BUILD INSTRUCTION

Você é o principal engenheiro de software, arquiteto de sistemas, engenheiro quantitativo e agente de desenvolvimento responsável por construir o ORION.

O ORION será desenvolvido para o Alpaca AI Trading Agents Hackathon 2026.

NÃO construa um simples chatbot de trading.

NÃO construa apenas uma interface que chama uma LLM.

NÃO construa um sistema que depende da LLM para cálculos financeiros.

Construa um verdadeiro AI Trading Agent com arquitetura modular, quantitativa, auditável e orientada à decisão.

==================================================
1. OBJETIVO DO PROJETO
==================================================

Nome:

ORION

Nome completo:

ORION — Autonomous Options Alpha Agent

Tagline:

"The Agent That Has to Prove Its Trade."

Objetivo:

Criar um agente autônomo especializado em identificar oportunidades de opções com potencial de alpha, analisar quantitativamente essas oportunidades, tentar invalidar cada tese através de uma camada adversarial, aplicar um Risk Governor independente e somente permitir uma execução quando todas as condições de segurança e qualidade forem satisfeitas.

O ORION deve ter capacidade de responder:

1. Existe uma oportunidade?
2. Por que ela existe?
3. Qual é a tese?
4. Qual é a evidência?
5. Qual é a expectativa matemática?
6. Quais são os riscos?
7. O que poderia invalidar a tese?
8. A liquidez é suficiente?
9. O custo da operação é aceitável?
10. O risco/recompensa é aceitável?
11. A oportunidade sobrevive à análise adversarial?
12. O Risk Governor permite a operação?
13. Devemos executar ou NÃO negociar?

A resposta final deve sempre poder ser:

EXECUTE

ou

NO TRADE

O sistema deve tratar "NO TRADE" como uma decisão válida e importante.

==================================================
2. PRINCÍPIO CENTRAL
==================================================

O ORION não deve tentar negociar o máximo possível.

O objetivo é:

MAXIMIZAR A QUALIDADE DAS DECISÕES.

Uma decisão de NO TRADE deve ser considerada melhor que uma operação de baixa qualidade.

Princípio:

Opportunity
    ↓
Evidence
    ↓
Quantitative Analysis
    ↓
Alpha Thesis
    ↓
Adversarial Challenge
    ↓
Risk Governor
    ↓
Trade Validation
    ↓
EXECUTE / NO TRADE

==================================================
3. REGRAS ABSOLUTAS
==================================================

REGRA 1:
Nunca operar dinheiro real.

REGRA 2:
O ambiente padrão deve ser Alpaca Paper Trading.

REGRA 3:
Nunca alterar ALPACA_PAPER_TRADE para false automaticamente.

REGRA 4:
Nunca armazenar API keys no código.

REGRA 5:
Nunca colocar API keys no frontend.

REGRA 6:
Nunca criar credenciais fictícias.

REGRA 7:
Nunca assumir que uma ordem foi executada sem confirmar através da API.

REGRA 8:
Nunca permitir que a LLM seja a autoridade final de risco.

REGRA 9:
O Risk Governor pode vetar qualquer decisão da LLM.

REGRA 10:
Os cálculos quantitativos devem ser determinísticos e realizados por código Python.

REGRA 11:
A LLM deve ser utilizada principalmente para:
- raciocínio
- interpretação
- geração de hipóteses
- análise qualitativa
- explicação
- crítica adversarial
- síntese

REGRA 12:
O código deve continuar funcionando mesmo que a LLM fique indisponível para tarefas determinísticas.

REGRA 13:
Toda decisão deve gerar um audit log.

REGRA 14:
Toda ordem deve possuir um client_order_id único.

REGRA 15:
Nunca duplicar uma ordem devido a retry.

==================================================
4. ARQUITETURA
==================================================

Construa a seguinte arquitetura:

ORION
│
├── Market Intelligence
│
├── Options Scanner
│
├── Quant Engine
│
├── Alpha Engine
│   ├── AI Analyst
│   └── Quantitative Analyst
│
├── Adversarial Agent
│
├── Risk Governor
│
├── Trade Validator
│
├── Execution Engine
│
├── Alpaca MCP Adapter
│
├── Backtesting / Replay Engine
│
├── Portfolio Monitor
│
├── Performance Engine
│
├── Decision Journal
│
├── Audit Logger
│
└── Dashboard


Fluxo:

Market Data
    ↓
Market Intelligence
    ↓
Options Scanner
    ↓
Candidate Opportunities
    ↓
Quant Engine
    ↓
Alpha Engine
    ↓
Adversarial Agent
    ↓
Risk Governor
    ↓
Trade Validator
    ↓
Execution Engine
    ↓
Alpaca Paper Trading
    ↓
Portfolio Monitor
    ↓
Performance
    ↓
Learning / Journal


==================================================
5. TECNOLOGIA
==================================================

Use:

Backend:
Python 3.10+

API:
FastAPI

Async:
asyncio

Data:
pandas
numpy

Quantitative calculations:
numpy
scipy quando necessário

Database:
SQLite inicialmente

Arquitetura preparada para:
PostgreSQL

Frontend:
React

Build:
Vite

Charts:
Recharts ou biblioteca equivalente leve

Styling:
CSS moderno

Communication:
REST API

Real-time:
WebSocket

Testing:
pytest

Environment:
python-dotenv

Validation:
Pydantic

Logging:
logging estruturado

Use type hints em todo o código relevante.

Use dataclasses ou Pydantic models para objetos importantes.

==================================================
6. ESTRUTURA DO PROJETO
==================================================

Crie:

ORION/

├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── requirements.txt
├── pyproject.toml
│
├── backend/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   │
│   ├── alpaca/
│   │   ├── client.py
│   │   ├── mcp_adapter.py
│   │   └── models.py
│   │
│   ├── market/
│   │   ├── intelligence.py
│   │   ├── scanner.py
│   │   └── models.py
│   │
│   ├── options/
│   │   ├── chain.py
│   │   ├── scanner.py
│   │   ├── greeks.py
│   │   ├── spreads.py
│   │   └── models.py
│   │
│   ├── quant/
│   │   ├── engine.py
│   │   ├── probability.py
│   │   ├── expected_value.py
│   │   ├── volatility.py
│   │   ├── liquidity.py
│   │   ├── scoring.py
│   │   └── models.py
│   │
│   ├── agents/
│   │   ├── analyst.py
│   │   ├── adversarial.py
│   │   └── models.py
│   │
│   ├── risk/
│   │   ├── governor.py
│   │   ├── limits.py
│   │   ├── position_sizing.py
│   │   └── models.py
│   │
│   ├── execution/
│   │   ├── validator.py
│   │   ├── executor.py
│   │   └── models.py
│   │
│   ├── portfolio/
│   │   ├── monitor.py
│   │   └── performance.py
│   │
│   ├── journal/
│   │   ├── decisions.py
│   │   └── audit.py
│   │
│   ├── backtesting/
│   │   ├── engine.py
│   │   ├── replay.py
│   │   └── models.py
│   │
│   └── api/
│       ├── routes.py
│       ├── websocket.py
│       └── schemas.py
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── styles/
│
├── data/
│
├── tests/
│   ├── test_quant.py
│   ├── test_risk.py
│   ├── test_options.py
│   ├── test_execution.py
│   └── test_scoring.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── STRATEGY.md
│   ├── RISK.md
│   ├── MCP.md
│   └── DECISION_ENGINE.md
│
└── scripts/
    ├── start_backend.py
    └── seed_demo.py


==================================================
7. ALPACA MCP
==================================================

Use o Alpaca Trading MCP Server atual.

A integração deve utilizar as capacidades disponíveis para:

- account
- options-data
- stock-data
- assets
- trading
- news

O Alpaca MCP atual fornece dados de opções incluindo:
- option chains
- quotes
- trades
- snapshots
- Greeks
- IV

Também permite execução de opções e spreads.

Configure o projeto para Paper Trading.

O MCP deve ser configurado através do ambiente/configuração do VS Code.

Nunca inserir credenciais diretamente no código.

Criar:

.env.example

com:

ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_PAPER_TRADE=true

Se possível, limitar os toolsets inicialmente para reduzir superfície e contexto:

account,
assets,
stock-data,
options-data,
news,
trading

A integração deve ser abstraída por:

backend/alpaca/mcp_adapter.py

Não espalhar chamadas Alpaca pelo projeto.

==================================================
8. MARKET INTELLIGENCE
==================================================

Criar um módulo capaz de analisar:

- preço
- volume
- tendência
- volatilidade
- momentum
- market regime
- eventos
- notícias
- earnings quando disponível
- movimentos anormais
- relação preço/volatilidade

Criar um Market Regime Classifier simples.

Classificar:

BULLISH
BEARISH
NEUTRAL
HIGH_VOLATILITY
LOW_VOLATILITY
EVENT_DRIVEN
UNCERTAIN

Não usar uma LLM para calcular indicadores.

==================================================
9. OPTIONS SCANNER
==================================================

Criar scanner capaz de analisar option chains.

Considerar:

- strike
- expiration
- bid
- ask
- spread
- volume
- open interest
- implied volatility
- Greeks
- moneyness
- days to expiration

Eliminar contratos com:

- liquidez insuficiente
- spread excessivo
- dados incompletos
- volume muito baixo
- risco inadequado
- vencimento inadequado

Criar suporte inicial para:

1. Long Call
2. Long Put
3. Bull Call Spread
4. Bear Put Spread
5. Bull Put Spread
6. Bear Call Spread

Priorizar estratégias de risco definido.

==================================================
10. QUANT ENGINE
==================================================

O Quant Engine é uma das partes mais importantes do projeto.

NÃO utilizar LLM para os cálculos.

Implementar:

- expected value
- risk/reward
- probability estimates
- IV analysis
- liquidity score
- spread cost
- max profit
- max loss
- breakeven
- Greeks
- position sizing
- confidence score

Criar um score de oportunidade:

Alpha Score =

30% Expected Value
20% Risk/Reward
15% Liquidity
15% Volatility Edge
10% Market Regime Alignment
10% Catalyst/Evidence

Normalizar para:

0 — 100

Criar também:

Risk Score

0 — 100

Onde:

0 = baixo risco relativo
100 = risco elevado

==================================================
11. ALPHA ENGINE
==================================================

O Alpha Engine recebe candidatos quantitativamente filtrados.

Cada oportunidade deve possuir:

symbol
strategy
legs
expiration
entry_price
max_profit
max_loss
breakeven
probability
expected_value
risk_reward
liquidity_score
volatility_score
alpha_score
risk_score
market_regime
catalysts
invalidation_conditions

==================================================
12. AI ANALYST
==================================================

Criar um agente de análise.

A LLM deve receber dados estruturados.

Ela NÃO deve receber autoridade para executar ordens diretamente.

Ela deve responder:

THESIS

EVIDENCE

CATALYST

EXPECTED_BEHAVIOR

INVALIDATION

RISKS

WHY_NOW

CONFIDENCE

RECOMMENDATION

A recomendação deve ser:

TRADE
WATCH
NO_TRADE

O agente deve explicar claramente sua decisão.

==================================================
13. ADVERSARIAL AGENT
==================================================

Esta é uma característica central do ORION.

Depois que o Alpha Engine gera uma oportunidade:

NÃO executar imediatamente.

Enviar a oportunidade para o Adversarial Agent.

O Adversarial Agent deve tentar provar que a operação está errada.

Perguntas:

1. O que a tese está ignorando?
2. Qual é o pior cenário?
3. Existe um catalisador contrário?
4. A volatilidade está precificada incorretamente?
5. O spread está caro?
6. Existe risco de liquidez?
7. A probabilidade estimada é realista?
8. A oportunidade depende demais de uma previsão?
9. O risco/recompensa é enganador?
10. Existe uma alternativa melhor?
11. Qual é a principal razão para NÃO executar?

Produzir:

counter_thesis
failure_modes
risk_factors
confidence
recommended_action

O resultado deve poder reduzir o Alpha Score.

==================================================
14. RISK GOVERNOR
==================================================

O Risk Governor NÃO deve ser controlado pela LLM.

É uma camada determinística.

Ele pode VETAR qualquer operação.

Implementar limites configuráveis.

Exemplo inicial:

MAX_PORTFOLIO_RISK = 0.02

MAX_SINGLE_TRADE_RISK = 0.01

MIN_ALPHA_SCORE = 70

MIN_LIQUIDITY_SCORE = 60

MAX_RISK_SCORE = 60

MIN_RISK_REWARD = 1.5

MAX_SPREAD_PERCENT = 5

MIN_OPEN_INTEREST = 100

MIN_VOLUME = 20

Evitar hardcode quando possível.

Configurar em:

backend/risk/limits.py

O Risk Governor deve verificar:

- portfolio exposure
- position size
- max loss
- liquidity
- spread
- Alpha Score
- Risk Score
- market regime
- duplicate positions
- existing correlated exposure
- daily loss limit
- maximum open trades

Resultado:

PASS

ou

VETO

Com razão explícita.

Exemplo:

RISK GOVERNOR

STATUS: VETO

Reason:
Expected value acceptable, but liquidity insufficient.

==================================================
15. TRADE VALIDATOR
==================================================

Antes da execução:

Alpha Engine
+
Adversarial Agent
+
Risk Governor

devem convergir.

O Trade Validator deve verificar:

- symbol válido
- option contract válido
- market open
- quote válido
- bid/ask disponível
- preço plausível
- position size válido
- max loss conhecido
- client_order_id único
- paper trading ativo
- Risk Governor PASS

Somente depois:

READY_FOR_EXECUTION

==================================================
16. EXECUTION ENGINE
==================================================

Implementar execução através do Alpaca.

Começar por paper trading.

Suportar:

- single option
- multi-leg spread

Antes de enviar ordem:

gerar Trade Execution Preview.

Exemplo:

ORION EXECUTION PREVIEW

Strategy:
Bull Call Spread

Underlying:
SPY

Buy:
540 Call

Sell:
545 Call

Expiration:
2026-09-18

Estimated Debit:
$1.82

Maximum Loss:
$182

Maximum Profit:
$318

Risk/Reward:
1 : 1.75

Alpha Score:
84

Risk Score:
24

Liquidity:
91

Adversarial Confidence:
68%

Risk Governor:
PASS

ACTION:

EXECUTE PAPER TRADE

==================================================
17. NO TRADE
==================================================

NO TRADE deve ser uma decisão de primeira classe.

Exemplo:

ORION DECISION

STATUS:
NO TRADE

Reason:

Alpha score below threshold.

ou:

NO TRADE

Reason:

Adversarial agent identified excessive event risk.

ou:

NO TRADE

Reason:

Risk Governor vetoed due to poor liquidity.

Registrar todas essas decisões.

Isso será importante para demonstrar inteligência e disciplina do agente.

==================================================
18. POSITION SIZING
==================================================

Implementar position sizing conservador.

Nunca arriscar uma porcentagem arbitrária do portfolio.

Usar:

account_equity
max_trade_risk
max_loss

Fórmula base:

max_position_risk =
account_equity * MAX_SINGLE_TRADE_RISK

contracts =
floor(max_position_risk / max_loss_per_contract)

Nunca permitir:

contracts < 1

sem sinalizar que a oportunidade não pode ser executada.

==================================================
19. BACKTEST / REPLAY
==================================================

Criar um mecanismo simples de replay/backtesting.

O objetivo inicial não é criar um backtester institucional.

O objetivo é permitir:

historical market snapshot
→
candidate generation
→
quant analysis
→
decision
→
simulated result

Registrar:

trade
entry
exit
P/L
max drawdown
win rate
average win
average loss
expectancy
Sharpe aproximado quando aplicável

Nunca afirmar que um backtest garante resultados futuros.

==================================================
20. DECISION JOURNAL
==================================================

Cada decisão deve ser armazenada.

Modelo:

Decision:

timestamp
symbol
strategy
market_regime
thesis
counter_thesis
alpha_score
risk_score
liquidity_score
expected_value
risk_reward
decision
reason
risk_governor
execution_status
order_id
result
pnl

Criar histórico pesquisável.

==================================================
21. AUDIT LOG
==================================================

Registrar:

timestamp
agent
action
input
output
decision
execution
errors

Exemplo:

09:42:11
OPTIONS_SCANNER
SPY
23 candidates

09:42:13
QUANT_ENGINE
5 candidates passed

09:42:15
AI_ANALYST
Candidate SPY spread

09:42:17
ADVERSARIAL_AGENT
Risk identified

09:42:18
RISK_GOVERNOR
PASS

09:42:19
TRADE_VALIDATOR
PASS

09:42:20
EXECUTION
Paper order submitted

==================================================
22. DASHBOARD
==================================================

Criar uma interface premium, moderna e profissional.

Não criar aparência de dashboard genérico.

Tema:

dark
quantitative
financial
minimal
high-tech

Tela principal:

ORION

AUTONOMOUS OPTIONS ALPHA AGENT

--------------------------------------------------

MARKET REGIME

BULLISH

SPY
$XXX.XX
+X.XX%

--------------------------------------------------

ORION STATUS

SCANNING

Candidates:
27

Qualified:
5

High Alpha:
2

--------------------------------------------------

TOP OPPORTUNITY

SPY

Bull Call Spread

Alpha Score:
84

Risk Score:
24

Liquidity:
91

Expected Value:
+$XX

Risk/Reward:
1:1.75

--------------------------------------------------

AI THESIS

[texto]

--------------------------------------------------

ADVERSARIAL CHALLENGE

[texto]

--------------------------------------------------

RISK GOVERNOR

PASS

--------------------------------------------------

FINAL DECISION

EXECUTE

--------------------------------------------------

Execution Preview

[detalhes]

--------------------------------------------------

RECENT DECISIONS

EXECUTE
NO TRADE
NO TRADE
EXECUTE

--------------------------------------------------

PORTFOLIO

Equity
Buying Power
Daily P/L
Open Risk
Positions

==================================================
23. DECISION ENGINE VISUAL
==================================================

Criar uma visualização do pipeline:

MARKET

↓

OPPORTUNITY

↓

QUANT

↓

AI THESIS

↓

ADVERSARIAL

↓

RISK

↓

DECISION

↓

EXECUTION

Cada etapa deve mostrar:

status
score
timestamp

Quando estiver processando:

SCANNING
ANALYZING
CHALLENGING
VALIDATING
EXECUTING

==================================================
24. API
==================================================

Criar endpoints:

GET /api/health

GET /api/account

GET /api/market/{symbol}

GET /api/options/{symbol}

GET /api/opportunities

GET /api/opportunities/{id}

POST /api/analyze

POST /api/scan

POST /api/decision

POST /api/execute

GET /api/positions

GET /api/orders

GET /api/performance

GET /api/decisions

GET /api/audit

WebSocket:

/ws/orion

para eventos em tempo real.

==================================================
25. ERROR HANDLING
==================================================

Implementar tratamento de:

MCP unavailable
Alpaca unavailable
invalid quote
market closed
invalid option contract
rate limit
timeout
LLM unavailable
invalid LLM output
duplicate order
database error
network error

Nenhum erro pode causar execução automática insegura.

Se houver dúvida:

NO TRADE.

==================================================
26. LLM OUTPUT VALIDATION
==================================================

Nunca confiar diretamente em texto produzido pela LLM.

Criar schemas Pydantic.

Exemplo:

AnalystOutput

{
    thesis: str,
    evidence: list[str],
    catalysts: list[str],
    risks: list[str],
    invalidation: list[str],
    confidence: float,
    recommendation: str
}

Validar tudo.

Se a resposta não passar:

REJECT LLM OUTPUT

e continuar sem execução.

==================================================
27. SECURITY
==================================================

Criar:

.env
.env.example

Adicionar .env ao .gitignore.

Nunca registrar secrets nos logs.

Nunca enviar API keys ao frontend.

Nunca colocar secrets em README.

Nunca colocar secrets em commits.

Nunca usar live trading.

==================================================
28. TESTES
==================================================

Criar testes unitários para:

Quant Engine

Risk Engine

Position Sizing

Options Scoring

Trade Validator

Duplicate Order Protection

LLM Output Validation

Decision Engine

Criar pelo menos:

20 testes automatizados.

Testar especialmente:

Risk Governor veto

invalid quote

low liquidity

high spread

insufficient buying power

max loss exceeded

Alpha Score below threshold

duplicate order

market closed

paper trading enforcement

==================================================
29. DEMO MODE
==================================================

Criar modo:

DEMO_MODE=true

Nesse modo:

não depender de mercado ao vivo para demonstrar a interface.

Criar dataset controlado.

Permitir mostrar uma decisão completa:

SCAN
→
ANALYZE
→
CHALLENGE
→
RISK
→
EXECUTE

O modo DEMO nunca deve enviar uma ordem real.

==================================================
30. OBSERVABILITY
==================================================

Adicionar:

structured logs

decision logs

latency

agent execution time

market data latency

MCP latency

LLM latency

execution latency

Mostrar no dashboard:

Decision Time

Data Latency

AI Latency

Execution Latency

==================================================
31. PERFORMANCE
==================================================

Evitar chamadas desnecessárias.

Não pedir a option chain inteira repetidamente.

Usar cache quando apropriado.

Evitar enviar grandes datasets para a LLM.

Filtrar quantitativamente antes da análise da LLM.

Pipeline:

RAW DATA
↓
FILTER
↓
QUANT
↓
TOP CANDIDATES
↓
LLM

Nunca:

RAW DATA
↓
LLM
↓
CALCULATIONS

==================================================
32. INTELIGÊNCIA HÍBRIDA
==================================================

O ORION deve separar:

DETERMINISTIC INTELLIGENCE

de

GENERATIVE INTELLIGENCE.

Deterministic:

pricing
Greeks
risk
probability calculations
position sizing
liquidity
scores
limits
validation

Generative:

thesis
explanation
counter-thesis
news interpretation
market narrative
reasoning

Esta separação é fundamental.

==================================================
33. FUTURE ARCHITECTURE
==================================================

A arquitetura deve permitir futuramente adicionar:

Income Agent

Volatility Agent

Hedging Agent

Options Alpha Agent

Stock Agent

Crypto Agent

Portfolio Agent

Risk Agent

Não implemente todos agora.

Deixe interfaces extensíveis.

==================================================
34. AGENT INTERFACE
==================================================

Criar uma interface base:

TradingAgent

com:

name
analyze()
evaluate()
explain()
validate()

Criar:

OptionsAlphaAgent

como implementação principal.

==================================================
35. DESIGN PRINCIPLE
==================================================

O sistema deve parecer um agente financeiro autônomo.

Não um chatbot.

Não colocar a conversa como elemento principal da interface.

O principal elemento deve ser:

DECISION ENGINE.

O usuário deve conseguir entender em segundos:

O que o ORION encontrou?

Por que encontrou?

Qual o risco?

O que tentou invalidar?

O Risk Governor aprovou?

Qual foi a decisão?

==================================================
36. DOCUMENTAÇÃO
==================================================

Criar documentação clara:

README.md

ARCHITECTURE.md

STRATEGY.md

RISK.md

MCP.md

DECISION_ENGINE.md

DEMO.md

Todos devem explicar:

o problema
a solução
a arquitetura
o diferencial
a utilização da IA
a utilização do Alpaca
a segurança
o papel do Risk Governor
o papel do Adversarial Agent

==================================================
37. DESENVOLVIMENTO INCREMENTAL
==================================================

NÃO tente implementar tudo de uma vez.

Divida o desenvolvimento em fases.

FASE 1:

Repository
Python
FastAPI
configuration
logging
database
tests

FASE 2:

Alpaca MCP
account
market data
options chain

FASE 3:

Options Scanner
Quant Engine
Risk Engine

FASE 4:

AI Analyst
Adversarial Agent

FASE 5:

Decision Engine
Trade Validator
Paper Execution

FASE 6:

Dashboard

FASE 7:

Backtesting
Decision Journal
Performance

FASE 8:

Demo
Testing
Polishing

==================================================
38. PRIMEIRA ENTREGA
==================================================

Comece agora.

Primeiro:

1. Inspecione o workspace atual.

2. Não apague arquivos existentes sem verificar.

3. Identifique se o projeto está vazio.

4. Crie a arquitetura.

5. Crie os arquivos base.

6. Configure Python.

7. Configure FastAPI.

8. Configure .env.example.

9. Configure logging.

10. Configure testes.

11. Configure database.

12. Configure o Alpaca MCP.

13. Criar health endpoint.

14. Criar um comando de diagnóstico:

python -m backend.main --diagnostic

O diagnóstico deve verificar:

Python
environment
database
Alpaca MCP
Alpaca authentication
paper trading status

NÃO execute nenhuma ordem nesta fase.

==================================================
39. MCP VERIFICATION
==================================================

Depois de configurar o MCP:

verificar:

account information

buying power

market clock

SPY latest quote

SPY option chain

Não executar ordens.

Se qualquer uma dessas operações falhar:

pare a implementação dependente do MCP,
diagnostique,
corrija,
teste novamente.

==================================================
40. PRIMEIRO VERTICAL SLICE
==================================================

Depois da infraestrutura:

implementar apenas um fluxo completo:

SPY

↓

Market Data

↓

Options Chain

↓

Filter

↓

Quant Score

↓

AI Thesis

↓

Adversarial Challenge

↓

Risk Governor

↓

Decision

Se:

Risk Governor = PASS

então preparar:

Paper Trade Preview

NÃO executar automaticamente sem validação explícita do modo de execução.

==================================================
41. QUALIDADE DO CÓDIGO
==================================================

Use:

SOLID quando fizer sentido.

Separation of concerns.

Dependency injection onde útil.

Type hints.

Docstrings em módulos críticos.

Small functions.

No giant files.

No duplicated logic.

No magic numbers.

Configuration centralizada.

Clear naming.

Automated tests.

==================================================
42. O QUE NÃO FAZER
==================================================

Não criar microservices.

Não criar Kubernetes.

Não criar infraestrutura cloud complexa.

Não criar autenticação multiusuário agora.

Não criar pagamentos.

Não criar mobile app.

Não criar quatro agentes completos.

Não implementar live trading.

Não construir um LLM próprio.

Não treinar modelos.

Não adicionar funcionalidades apenas para aumentar quantidade de código.

Priorize:

DEMO FUNCIONAL
+
DECISION QUALITY
+
RISK CONTROL
+
ALPACA INTEGRATION
+
CLEAR DIFFERENTIATION

==================================================
43. PRIORIDADE DO HACKATHON
==================================================

A ordem de prioridade é:

1. Funcionamento
2. Alpaca integration
3. Autonomous decision pipeline
4. Quantitative reasoning
5. Risk Governor
6. Adversarial Agent
7. Paper execution
8. Dashboard
9. Explainability
10. Documentation
11. Visual polish

==================================================
44. DIFERENCIAL COMPETITIVO
==================================================

O ORION deve ser apresentado como:

"An options trading agent that must prove its trade before executing it."

Diferencial:

A maioria dos agentes:

Find → Trade

ORION:

Find
→
Quantify
→
Explain
→
Attack
→
Risk Check
→
Validate
→
Trade / NO TRADE

A arquitetura deve tornar esse diferencial visível na interface.

==================================================
45. FINAL DECISION OBJECT
==================================================

Toda decisão deve produzir:

{
    "symbol": "...",
    "strategy": "...",
    "alpha_score": 0,
    "risk_score": 0,
    "liquidity_score": 0,
    "expected_value": 0,
    "risk_reward": 0,
    "thesis": "...",
    "counter_thesis": "...",
    "risk_governor": "PASS",
    "decision": "EXECUTE",
    "reason": "...",
    "timestamp": "...",
    "execution_status": "PAPER"
}

==================================================
46. CLAUDE CODE BEHAVIOR
==================================================

Você é responsável pelo desenvolvimento.

Não peça confirmação para cada arquivo.

Tome decisões técnicas razoáveis.

Quando houver ambiguidade:

escolha a solução mais simples,
segura,
testável
e adequada para hackathon.

Não faça overengineering.

Não invente APIs.

Não invente Alpaca MCP tools.

Quando precisar usar uma ferramenta Alpaca:

verifique a ferramenta disponível no MCP.

Se uma ferramenta não estiver disponível:

adapte a arquitetura.

Não simule integração Alpaca se o MCP estiver disponível.

==================================================
47. WORKFLOW DE DESENVOLVIMENTO
==================================================

Para cada fase:

1. Planejar
2. Implementar
3. Testar
4. Corrigir
5. Documentar
6. Executar novamente

Depois de cada fase:

mostrar:

- arquivos criados
- arquivos modificados
- funcionalidades implementadas
- testes executados
- testes aprovados
- problemas encontrados
- próxima fase

==================================================
48. PRIMEIRA AÇÃO AGORA
==================================================

COMECE.

Não escreva apenas uma explicação.

Inspecione o workspace.

Depois construa a FASE 1.

Quando terminar:

execute os testes.

Depois execute o diagnóstico.

Depois me informe:

ORION INITIALIZATION COMPLETE

com:

Project structure:
Backend:
Frontend:
Database:
Tests:
Alpaca MCP:
Paper Trading:
Next step:

Não avance para live trading em nenhuma circunstância.

O objetivo é construir um sistema funcional, demonstrável, seguro e competitivo dentro do prazo do hackathon.

COMECE AGORA.