#!/usr/bin/env python3
"""Build FahMai Enterprise AI-safe CSV tables without changing SQLite shape.

The friend pipeline imports CSV files directly into SQLite and creates views
from fixed table/column names. This script preserves that shape while replacing
sensitive values with enterprise-safe placeholders.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


CUSTOMER_NAME_REDACTION = "REDACTED_CUSTOMER"
ACCOUNT_REDACTION = "REDACTED_ACCOUNT"
TRACKING_REDACTION = "REDACTED_TRACKING"


@dataclass(frozen=True)
class RedactionRule:
    table_name: str
    column_name: str
    replacement: str
    action: str
    notes: str


@dataclass(frozen=True)
class BuildSummary:
    tables_processed: int
    rows_processed: int
    redacted_cells: int
    report_path: Path


REDACTION_RULES: tuple[RedactionRule, ...] = (
    RedactionRule(
        "DIM_BANK_ACCOUNT",
        "account_number",
        ACCOUNT_REDACTION,
        "replace_with_token",
        "Bank account numbers are not required for analytics answers; account_id remains available for joins.",
    ),
    RedactionRule(
        "DIM_CUSTOMER",
        "first_name_th",
        CUSTOMER_NAME_REDACTION,
        "replace_with_token",
        "Customer names are personal data; customer_id and segmentation fields remain available.",
    ),
    RedactionRule(
        "DIM_CUSTOMER",
        "last_name_th",
        CUSTOMER_NAME_REDACTION,
        "replace_with_token",
        "Customer names are personal data; customer_id and segmentation fields remain available.",
    ),
    RedactionRule(
        "DIM_CUSTOMER",
        "first_name_en",
        CUSTOMER_NAME_REDACTION,
        "replace_with_token",
        "Customer names are personal data; customer_id and segmentation fields remain available.",
    ),
    RedactionRule(
        "DIM_CUSTOMER",
        "last_name_en",
        CUSTOMER_NAME_REDACTION,
        "replace_with_token",
        "Customer names are personal data; customer_id and segmentation fields remain available.",
    ),
    RedactionRule(
        "DIM_CUSTOMER",
        "email",
        "",
        "blank",
        "Customer contact data is not required for benchmark analytics.",
    ),
    RedactionRule(
        "DIM_CUSTOMER",
        "phone",
        "",
        "blank",
        "Customer contact data is not required for benchmark analytics.",
    ),
    RedactionRule(
        "DIM_EMPLOYEE",
        "email",
        "",
        "blank",
        "Employee contact data is removed; work names and roles remain for CEO/approver questions.",
    ),
    RedactionRule(
        "DIM_EMPLOYEE",
        "phone",
        "",
        "blank",
        "Employee contact data is removed when present; work names and roles remain available.",
    ),
    RedactionRule(
        "FACT_SHIPPING",
        "tracking_number",
        TRACKING_REDACTION,
        "replace_with_token",
        "Shipment tracking numbers are operational identifiers, not needed for analytics joins.",
    ),
)


RULES_BY_TABLE_COLUMN = {(rule.table_name, rule.column_name): rule for rule in REDACTION_RULES}
REPORT_COLUMNS = ["table_name", "column_name", "redaction_action", "redacted_cells", "notes"]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return headers, rows


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sanitize_rows(table_name: str, headers: list[str], rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    sanitized = [dict(row) for row in rows]
    report_rows: list[dict[str, str]] = []

    for column_name in headers:
        rule = RULES_BY_TABLE_COLUMN.get((table_name, column_name))
        if rule is None:
            continue

        for row in sanitized:
            row[column_name] = rule.replacement
        redacted_cells = len(sanitized)

        report_rows.append(
            {
                "table_name": table_name,
                "column_name": column_name,
                "redaction_action": rule.action,
                "redacted_cells": str(redacted_cells),
                "notes": rule.notes,
            }
        )

    return sanitized, report_rows


def build_enterprise_ai_safe_tables(input_dir: Path, output_dir: Path, report_path: Path) -> BuildSummary:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    report_path = report_path.resolve()

    csv_paths = sorted(input_dir.glob("*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")

    all_report_rows: list[dict[str, str]] = []
    rows_processed = 0

    for input_path in csv_paths:
        table_name = input_path.stem
        headers, rows = read_csv(input_path)
        sanitized, report_rows = sanitize_rows(table_name, headers, rows)
        output_path = output_dir / input_path.name
        if output_path.resolve() != input_path.resolve() or report_rows or sanitized != rows:
            write_csv(output_path, headers, sanitized)
        all_report_rows.extend(report_rows)
        rows_processed += len(rows)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_report_rows)

    redacted_cells = sum(int(row["redacted_cells"]) for row in all_report_rows)
    return BuildSummary(
        tables_processed=len(csv_paths),
        rows_processed=rows_processed,
        redacted_cells=redacted_cells,
        report_path=report_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FahMai Enterprise AI-safe tables while preserving SQLite compatibility.")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing source CSV tables.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to write AI-safe compatible CSV tables.")
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("data_governance/enterprise_ai_safe_redaction_summary.csv"),
        help="CSV report path for redacted columns and cell counts.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Allow writing into an existing non-empty output directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    input_dir = args.input_dir.resolve()
    if output_dir.exists() and output_dir != input_dir and any(output_dir.iterdir()) and not args.overwrite:
        raise SystemExit(f"Output directory is not empty: {output_dir}. Pass --overwrite to replace files.")

    summary = build_enterprise_ai_safe_tables(input_dir, output_dir, args.report_path)
    print("FahMai Enterprise AI-Safe Analytics Pipeline")
    print(f"Tables processed: {summary.tables_processed}")
    print(f"Rows processed: {summary.rows_processed}")
    print(f"Redacted cells: {summary.redacted_cells}")
    print(f"Redaction report: {summary.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
