import pandas as pd

from ap_forecast_automation.ap_forecast import (
    SupplierStatementConfig,
    add_bank_details_row,
    pivot_statement_df,
    process_statement_df,
)


def test_process_statement_df_normalizes_due_date_labels_and_types():
    df = pd.DataFrame(
        {
            "Item": ["Balance Overdue", "Due on/after:"],
            "Date": ["01/06/2025", "15/06/2025"],
            "Amt": ["1,234.50", "99.00"],
            "Store": ["TEST STORE 1", "TEST STORE 1"],
            "Supplier": ["SUP", "SUP"],
        }
    )

    result = process_statement_df(df)

    assert result["Amt"].tolist() == [1234.50, 99.00]
    assert result["Item"].tolist() == ["Balance Overdue", "Due by:"]
    assert result["Date"].iloc[0] == pd.Timestamp("2025-06-01").date()


def test_pivot_statement_df_sums_stores_into_total_column():
    df = pd.DataFrame(
        {
            "Item": ["Balance Overdue", "Balance Overdue"],
            "Date": [pd.Timestamp("2025-06-01").date()] * 2,
            "Amt": [100.0, 50.0],
            "Store": ["TEST STORE 1", "TEST STORE 2"],
            "Supplier": ["SUP", "SUP"],
        }
    )

    result = pivot_statement_df(df)

    assert result["Total"].iloc[0] == 150.0


def test_add_bank_details_row_prepends_row_matching_column_count():
    df_pivot = pd.DataFrame(
        {
            "Item": ["Balance Overdue"],
            "Date": [pd.Timestamp("2025-06-01").date()],
            "Supplier": ["SUP"],
            "TEST STORE 1": [100.0],
            "Total": [100.0],
        }
    )
    config = SupplierStatementConfig(key="SUP", code_length=3, sheet_name="TestSupplier", bank_name="TestBank")

    result = add_bank_details_row(df_pivot, config)

    assert len(result) == 2
    assert result.iloc[0]["Item"] == "Bank"
    assert result.iloc[0]["Supplier"] == "TestSupplier"
    assert result.iloc[0]["TEST STORE 1"] == "BankName"
