"""Convenience launcher for the ORION backend.

Equivalent to ``python -m backend.main``.
"""

from __future__ import annotations

from backend.main import main

if __name__ == "__main__":
    raise SystemExit(main([]))
