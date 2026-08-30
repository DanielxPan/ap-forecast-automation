# AP Forecast Automation

An automation I built and ran weekly while acting as the data/automation
function for a multi-site retail business, to forecast upcoming
accounts-payable without anyone manually re-typing supplier statements.

## Business problem

Forecasting upcoming accounts-payable meant manually opening each
supplier's statement PDF, reading off the overdue balance by due-date
bucket, and retyping it into a spreadsheet — for every store, every
supplier, every week.

## What it does

`ap_forecast.py` parses each supplier's statement PDF directly with
`pdfplumber`, extracting the overdue-balance table by locating it
between known header/footer text markers, pivots it into one row per
due-date bucket with one column per store, and writes a multi-sheet
Excel workbook (one sheet per supplier) with bank-transfer details
attached, ready to forward to the finance team.

## Project layout

```
src/ap_forecast_automation/
├── config.py       # settings loaded from .env — no hardcoded paths
└── ap_forecast.py  # PDF parsing + pivot + workbook export
scripts/
└── run_ap_forecast.py
```

## Running it locally

```bash
pip install -e ".[dev]"
cp .env.example .env   # fill in real paths for your machine
python scripts/run_ap_forecast.py
```

Update `SUPPLIER_CONFIGS` in `scripts/run_ap_forecast.py` with your real
supplier codes — the values there are placeholders matching the
anonymized original script.

## Notes on this refactor

The original script duplicated an entire ~90-line parsing block once
per supplier (copy-pasted, with only the supplier name changed). That's
now one function, `parse_statements_for_supplier`, parameterized by a
`SupplierStatementConfig` (the supplier's filename code and its length,
since that varies per supplier) — adding a new supplier means adding one
config entry, not copying 90 lines.
