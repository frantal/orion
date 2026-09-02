"""Backend localization helpers for user-facing narrative text.

Only presentation strings are localized (thesis, reasons, labels). Decision
logic, scores and thresholds are never affected by the chosen language.
"""

from __future__ import annotations

SUPPORTED_LANGUAGES = {"en", "pt"}
DEFAULT_LANGUAGE = "en"


def normalize_language(lang: str | None) -> str:
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def L(lang: str, en: str, pt: str) -> str:
    """Pick the English or Portuguese variant."""
    return pt if lang == "pt" else en


_STRATEGY_PT = {
    "Long Call": "Compra de Call",
    "Long Put": "Compra de Put",
    "Bull Call Spread": "Spread de Alta (Call)",
    "Bear Put Spread": "Spread de Baixa (Put)",
    "Bull Put Spread": "Spread de Alta (Put)",
    "Bear Call Spread": "Spread de Baixa (Call)",
}

_REGIME_PT = {
    "BULLISH": "ALTA",
    "BEARISH": "BAIXA",
    "NEUTRAL": "NEUTRO",
    "HIGH_VOLATILITY": "VOLAT. ALTA",
    "LOW_VOLATILITY": "VOLAT. BAIXA",
    "EVENT_DRIVEN": "EVENTOS",
    "UNCERTAIN": "INCERTO",
}

_TOKEN_PT = {
    "EXECUTE": "EXECUTAR",
    "NO_TRADE": "NÃO OPERAR",
    "TRADE": "OPERAR",
    "WATCH": "OBSERVAR",
    "PROCEED": "PROSSEGUIR",
    "REDUCE": "REDUZIR",
    "REJECT": "REJEITAR",
    "PASS": "APROVADO",
    "VETO": "VETO",
}


def strategy_name(value: str, lang: str) -> str:
    return _STRATEGY_PT.get(value, value) if lang == "pt" else value


def regime_name(value: str, lang: str) -> str:
    return _REGIME_PT.get(value, value) if lang == "pt" else value


def token(value: str, lang: str) -> str:
    return _TOKEN_PT.get(value, value) if lang == "pt" else value
