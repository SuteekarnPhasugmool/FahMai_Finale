import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_enterprise_ai_safe_tables import build_enterprise_ai_safe_tables


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


class EnterpriseAiSafeTablesTest(unittest.TestCase):
    def test_build_preserves_headers_rows_and_redacts_sensitive_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            report_path = root / "reports" / "redaction_summary.csv"

            write_csv(
                input_dir / "DIM_BANK_ACCOUNT.csv",
                ["account_id", "bank", "account_number", "account_role"],
                [["ACC-1", "KBank", "001-1-00001-1", "operating"]],
            )
            write_csv(
                input_dir / "DIM_CUSTOMER.csv",
                ["customer_id", "first_name_en", "last_name_en", "email", "phone", "customer_type"],
                [["CUST-1", "Mali", "Jaidee", "mali@example.test", "0800000000", "B2C"]],
            )
            write_csv(
                input_dir / "DIM_EMPLOYEE.csv",
                ["employee_id", "first_name_en", "last_name_en", "email", "position_title"],
                [["E1", "Naret", "Vision", "naret@example.test", "CEO"]],
            )
            write_csv(
                input_dir / "FACT_SHIPPING.csv",
                ["shipping_id", "tracking_number", "vendor_id"],
                [["SHIP-1", "TRACK-123", "V-001"]],
            )

            summary = build_enterprise_ai_safe_tables(input_dir, output_dir, report_path)

            account_headers, account_rows = read_csv(output_dir / "DIM_BANK_ACCOUNT.csv")
            self.assertEqual(account_headers, ["account_id", "bank", "account_number", "account_role"])
            self.assertEqual(len(account_rows), 1)
            self.assertEqual(account_rows[0]["account_number"], "REDACTED_ACCOUNT")

            customer_headers, customer_rows = read_csv(output_dir / "DIM_CUSTOMER.csv")
            self.assertEqual(customer_headers, ["customer_id", "first_name_en", "last_name_en", "email", "phone", "customer_type"])
            self.assertEqual(customer_rows[0]["first_name_en"], "REDACTED_CUSTOMER")
            self.assertEqual(customer_rows[0]["last_name_en"], "REDACTED_CUSTOMER")
            self.assertEqual(customer_rows[0]["email"], "")
            self.assertEqual(customer_rows[0]["phone"], "")

            employee_headers, employee_rows = read_csv(output_dir / "DIM_EMPLOYEE.csv")
            self.assertEqual(employee_headers, ["employee_id", "first_name_en", "last_name_en", "email", "position_title"])
            self.assertEqual(employee_rows[0]["first_name_en"], "Naret")
            self.assertEqual(employee_rows[0]["last_name_en"], "Vision")
            self.assertEqual(employee_rows[0]["email"], "")

            shipping_headers, shipping_rows = read_csv(output_dir / "FACT_SHIPPING.csv")
            self.assertEqual(shipping_headers, ["shipping_id", "tracking_number", "vendor_id"])
            self.assertEqual(shipping_rows[0]["tracking_number"], "REDACTED_TRACKING")

            self.assertEqual(summary.redacted_cells, 7)
            report_headers, report_rows = read_csv(report_path)
            self.assertEqual(report_headers, ["table_name", "column_name", "redaction_action", "redacted_cells", "notes"])
            self.assertEqual(len(report_rows), 7)


if __name__ == "__main__":
    unittest.main()
