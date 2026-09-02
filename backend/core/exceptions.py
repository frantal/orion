"""ORION exception hierarchy.

A single base exception (:class:`OrionError`) lets the API layer translate any
domain failure into a safe response. Critically, no error path is ever allowed
to trigger an unsafe automatic execution — when in doubt, the pipeline resolves
to NO TRADE.
"""

from __future__ import annotations


class OrionError(Exception):
    """Base class for all ORION domain errors."""


class ConfigurationError(OrionError):
    """Invalid or missing configuration."""


class DatabaseError(OrionError):
    """Persistence-layer failure."""


class AlpacaUnavailableError(OrionError):
    """Alpaca / MCP backend is unreachable or returned an error."""


class MarketClosedError(OrionError):
    """Operation requires an open market but the market is closed."""


class InvalidQuoteError(OrionError):
    """A quote is missing, stale, or otherwise implausible."""


class InvalidOptionContractError(OrionError):
    """An option contract is malformed or not tradable."""


class LLMUnavailableError(OrionError):
    """The generative layer is unavailable."""


class LLMOutputValidationError(OrionError):
    """LLM output failed schema validation and must be rejected."""


class RiskVetoError(OrionError):
    """The Risk Governor vetoed the operation."""


class DuplicateOrderError(OrionError):
    """An order with the same client_order_id already exists."""


class ValidationError(OrionError):
    """Trade validation failed."""
