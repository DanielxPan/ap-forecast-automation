"""Settings, loaded from environment variables (see .env.example).

Every path that used to be hardcoded in the original script lives here
instead, so the same code runs on any machine by just supplying a
`.env` file - no source edits required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


@dataclass(frozen=True)
class FinanceSettings:
    statements_dir: str = field(default_factory=lambda: _env("FINANCE_STATEMENTS_DIR"))
    ap_forecast_output_dir: str = field(default_factory=lambda: _env("FINANCE_AP_FORECAST_OUTPUT_DIR"))
