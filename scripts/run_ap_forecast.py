"""CLI entry point: build the accounts-payable forecast workbook from
today's supplier statement PDFs.

Update SUPPLIER_CONFIGS below with your real supplier codes - the
values here are placeholders matching the anonymized original script.
"""

from ap_forecast_automation.config import FinanceSettings
from ap_forecast_automation.ap_forecast import SupplierStatementConfig, run

SUPPLIER_CONFIGS = [
    SupplierStatementConfig(key="Supplier1", code_length=3, sheet_name="Supplier1", bank_name="BankName"),
    SupplierStatementConfig(key="Supplier2", code_length=7, sheet_name="Supplier2", bank_name="BankName"),
]

if __name__ == "__main__":
    output_path = run(FinanceSettings(), SUPPLIER_CONFIGS)
    print(f"AP forecast written to: {output_path}")
