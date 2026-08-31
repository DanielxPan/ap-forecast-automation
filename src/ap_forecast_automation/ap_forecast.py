"""Extract outstanding-balance statements from supplier PDFs into an
accounts-payable forecast workbook.

Refactored from ``ReadStatements_ForecastAPOutstanding.py`` (recovered
from a PDF export). The original duplicated an entire ~90-line block
per supplier (Supplier1, Metcash/Supplier2); that block is now one
function, ``parse_statements_for_supplier``, parameterized per supplier
by how many characters of the filename its code occupies.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import pandas as pd
import pdfplumber

from ap_forecast_automation.config import FinanceSettings

START_WORDS = [
    "Balance Overdue Due by: Due by: Due by: Due on/after:",
    "Balance Overdue Due by: Due by: Due by:",
    "Balance Overdue",
]
STOP_WORDS = "Date Reference Description Due Debit Credit Balance"

# Filenames look like "{today}_{supplier_code}_{store}.pdf" - the supplier
# code length varies per supplier, so it's supplied per config below.
FILENAME_PREFIX_LEN = 11  # len("YYYY-MM-DD_")


@dataclass(frozen=True)
class SupplierStatementConfig:
    key: str  # matches the supplier code embedded in the filename
    code_length: int
    sheet_name: str
    bank_name: str


def _parse_statement_page(file_path: str) -> dict:
    """Extract the item/date/amount rows from the first page of one statement."""
    with pdfplumber.open(file_path) as pdf:
        text = pdf.pages[0].extract_text()

    lines = text.split("\n")
    start_index = next((i for i, line in enumerate(lines) if any(w in line for w in START_WORDS)), None)
    end_index = next((i for i, line in enumerate(lines) if STOP_WORDS in line), None)
    lines_filtered = lines[start_index:end_index]

    headers = re.findall(r"Due by:|Due on/after:|[^\s]+", lines_filtered[0])
    dates = lines_filtered[1].split()
    dates.insert(1, dates[0])
    values = re.split(r"\s+", lines_filtered[2])

    return {"Item": headers, "Date": dates, "Amt": values}


def parse_statements_for_supplier(
    statements_dir: str, today_str: str, config: SupplierStatementConfig
) -> pd.DataFrame:
    """Parse every statement PDF for one supplier, received today, into a dataframe."""
    file_keyword = f"{today_str}_{config.key}"
    supplier_start = FILENAME_PREFIX_LEN
    supplier_end = supplier_start + config.code_length
    store_start = supplier_end + 1

    frames = []
    for file_name in os.listdir(statements_dir):
        if file_keyword not in file_name or not file_name.endswith(".pdf"):
            continue

        store = file_name[store_start:-4]
        data = _parse_statement_page(os.path.join(statements_dir, file_name))
        df = pd.DataFrame(data)
        df["Store"] = store
        df["Supplier"] = file_name[supplier_start:supplier_end]
        frames.append(df)

    if not frames:
        return pd.DataFrame(columns=["Item", "Date", "Amt", "Store", "Supplier"])
    return pd.concat(frames, ignore_index=True)


def process_statement_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize date/amount types and collapse due-date variants into one label."""
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y").dt.date
    df["Amt"] = df["Amt"].str.replace(",", "").astype(float)
    df.loc[df["Item"] == "Due on/after:", "Item"] = "Due by:"
    return df


def pivot_statement_df(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot to one row per (item, date) and one column per store, with a total."""
    pvt = df.pivot_table(index=["Item", "Date", "Supplier"], values="Amt", columns="Store")
    pvt = pvt.reset_index().sort_values(by="Date").fillna(0)

    store_columns = pvt.columns.tolist()[3:]
    pvt["Total"] = pvt[store_columns].sum(axis=1)
    return pvt


def add_bank_details_row(df_pivot: pd.DataFrame, config: SupplierStatementConfig) -> pd.DataFrame:
    """Prepend a row labeling which bank each store pays this supplier through.

    This is a label only (e.g. "ANZ", "Westpac") for whoever processes the
    payment run to route it correctly - it never contains an account
    number or any other transfer detail.
    """
    num_store_columns = df_pivot.shape[1] - 4
    bank_row = ["Bank", "", config.sheet_name] + [config.bank_name] * num_store_columns + [""]
    df_bank_row = pd.DataFrame([bank_row], columns=df_pivot.columns.tolist())
    return pd.concat([df_bank_row, df_pivot], ignore_index=True)


def build_supplier_forecast(
    statements_dir: str, today_str: str, config: SupplierStatementConfig
) -> pd.DataFrame:
    """Run the full per-supplier pipeline: parse -> process -> pivot -> bank row."""
    df_raw = parse_statements_for_supplier(statements_dir, today_str, config)
    df_processed = process_statement_df(df_raw)
    df_pivot = pivot_statement_df(df_processed)
    return add_bank_details_row(df_pivot, config)


def write_forecast_workbook(sheets: dict[str, pd.DataFrame], output_path: str) -> None:
    """Write one sheet per supplier with column widths and integer formatting."""
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        workbook = writer.book
        integer_format = workbook.add_format({"num_format": "#,##0"})
        border_format = workbook.add_format({"border": 1})

        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False, header=True)
            sheet = writer.sheets[sheet_name]
            rows, cols = df.shape

            for col_num, value in enumerate(df.columns):
                sheet.set_column(col_num, col_num, len(str(value)) + 2)

            sheet.conditional_format(0, 0, rows, cols - 1, {"type": "no_errors", "format": border_format})

            numeric_columns = df.select_dtypes(include=["int", "float"]).columns
            for col_num, column_name in enumerate(df.columns):
                if column_name in numeric_columns:
                    sheet.set_column(col_num, col_num, None, integer_format)


def run(settings: FinanceSettings, supplier_configs: list[SupplierStatementConfig]) -> str:
    """Build the AP forecast workbook for all configured suppliers."""
    today_str = str(pd.Timestamp.today().date())

    sheets = {
        config.sheet_name: build_supplier_forecast(settings.statements_dir, today_str, config)
        for config in supplier_configs
    }

    output_path = os.path.join(settings.ap_forecast_output_dir, f"{today_str}_AP_Forecast.xlsx")
    write_forecast_workbook(sheets, output_path)
    return output_path
