#!/usr/bin/env python3
"""Prompt-to-SQL agent for FahMai's structured fact/dimension tables.

The agent uses a curated semantic layer:

1. Build or open a SQLite database from the CSV bundle.
2. Create enriched FACT views with approved FACT -> DIM joins.
3. Route a natural-language question to a view.
4. Generate a conservative aggregate SQL query.
5. Validate and execute read-only SQL.

This is deliberately metadata-driven rather than free-form SQL guessing.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib import request
from urllib.error import HTTPError, URLError

from join_catalog import VIEW_SPECS, ViewSpec, catalog_prompt


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_DIR = ROOT / "fah-mai-the-finale-enterprise-data-agentic-showdown" / "tables"
DEFAULT_DB = ROOT / "fahmai_agentic.db"
DEFAULT_VIEW_SQL = ROOT / "sql" / "create_joined_views.sql"
DEFAULT_QUESTIONS_CSV = ROOT / "questions.csv"


METRIC_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("net", "net pay", "net_pay", "สุทธิ"), "net_pay_thb"),
    (("gross", "gross pay", "gross_pay", "ก่อนหัก"), "gross_pay_thb"),
    (("tax", "ภาษี"), "tax_deduction_thb"),
    (("social", "ประกันสังคม"), "social_security_thb"),
    (("revenue", "sales", "ยอดขาย", "รายได้", "net_total"), "net_total_thb"),
    (("basket", "ตะกร้า"), "basket_total_thb"),
    (("discount", "ส่วนลด"), "discount_total_thb"),
    (("shipping charge", "ค่าส่ง"), "shipping_charge_thb"),
    (("quantity", "qty", "จำนวนชิ้น", "ชิ้น"), "quantity"),
    (("closing", "คงเหลือ", "closing_units"), "closing_units"),
    (("points", "point", "แต้ม", "คะแนน"), "points_delta"),
    (("refund", "คืนเงิน"), "refund_amount_thb"),
    (("return", "คืนสินค้า"), "return_amount_thb"),
    (("claim", "เคลม"), "claim_amount_thb"),
    (("vendor payment", "paid", "จ่าย"), "paid_amount_thb"),
    (("amount", "จำนวนเงิน", "มูลค่า"), "amount_thb"),
)


GROUP_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("branch", "store", "สาขา"), "branch_name_en"),
    (("origin branch", "สาขาต้นทาง"), "origin_branch_name_en"),
    (("employee branch", "สาขาพนักงาน"), "employee_branch_name_en"),
    (("associated branch", "สาขาบัญชี"), "associated_branch_name_en"),
    (("department", "dept", "แผนก"), "department_name_en"),
    (("product department", "แผนกสินค้า"), "product_department_name_en"),
    (("category", "หมวด", "ประเภทสินค้า"), "product_category"),
    (("subcategory", "หมวดย่อย"), "product_subcategory"),
    (("brand", "แบรนด์"), "product_brand_family"),
    (("vendor", "supplier", "ผู้ขาย", "ซัพพลายเออร์"), "vendor_name_en"),
    (("customer type", "ประเภทลูกค้า"), "customer_type"),
    (("region", "ภูมิภาค"), "customer_region"),
    (("province", "จังหวัด"), "customer_province"),
    (("channel", "ช่องทาง"), "channel"),
    (("campaign", "แคมเปญ"), "campaign_description_en"),
    (("payment status", "สถานะจ่าย"), "payment_status"),
    (("payment method", "วิธีจ่าย"), "payment_method"),
    (("movement type", "ประเภท movement", "ประเภทเคลื่อนไหว"), "movement_type"),
    (("return reason", "เหตุผลคืน"), "return_reason"),
    (("claim reason", "เหตุผลเคลม"), "claim_reason"),
    (("resolution", "resolution", "การแก้ไข"), "resolution_type"),
    (("status", "สถานะ"), "confirmation_status"),
    (("tier", "ระดับสมาชิก"), "customer_loyalty_tier"),
    (("sku", "สินค้า"), "sku_id"),
    (("employee", "พนักงาน"), "employee_id"),
    (("fiscal year", "ปีงบ"), "event_fiscal_year"),
    (("quarter", "ไตรมาส", "q"), "event_fiscal_quarter"),
)


@dataclass(frozen=True)
class QueryPlan:
    view_name: str
    metric: str | None
    aggregate: str
    group_by: tuple[str, ...]
    filters: tuple[str, ...]
    limit: int
    rationale: str


@dataclass(frozen=True)
class StructuredPlannerOutput:
    view_name: str
    metric: str | None
    aggregate: str
    group_by: tuple[str, ...]
    year: int | None
    branch_codes: tuple[str, ...]
    channel: str | None
    limit: int
    rationale: str


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def infer_sqlite_type(column: str, nonblank_values: list[str]) -> str:
    """Infer a practical SQLite type from a column name and sampled values.

    SQLite is dynamically typed, but declaring useful affinities helps the LLM
    and avoids obvious issues such as booleans being stored as text.
    """
    col = column.lower()
    values = [value.strip() for value in nonblank_values if value.strip()]
    lowered = {value.lower() for value in values}
    int_re = re.compile(r"^[-+]?\d+$")
    real_re = re.compile(r"^[-+]?(?:\d+\.\d*|\d*\.\d+)$")

    if values and lowered <= {"true", "false"}:
        return "BOOLEAN"

    if col in {"phone", "account_number"}:
        return "TEXT"
    if col.endswith(("_type", "_status", "_method", "_reason", "_role", "_category", "_subcategory", "_subtype")):
        return "TEXT"
    if col.endswith("_tier") or col == "resulting_tier":
        return "TEXT"

    if col.endswith("_date") or col in {"date_iso", "issue_date", "business_event_date", "posting_date", "as_of_date"}:
        return "DATE"
    if col.endswith("_timestamp"):
        return "TEXT"

    numeric_real_markers = (
        "_thb",
        "_pct",
        "amount",
        "balance",
        "price",
        "cost",
        "revenue",
        "discount",
        "rate",
        "multiplier",
        "coefficient",
        "ceiling",
        "msrp",
    )
    numeric_integer_names = {
        "quantity",
        "closing_units",
        "points_delta",
        "resulting_balance_points",
        "warranty_months",
        "coverage_months",
        "days_since_purchase",
        "rank",
        "schema_version",
        "version_number",
        "fiscal_year",
        "fiscal_quarter",
        "day_of_week",
        "min_co_signers",
        "age",
    }

    if col in numeric_integer_names:
        return "INTEGER"
    if any(marker in col for marker in numeric_real_markers):
        return "REAL"
    if col == "value_numeric":
        return "REAL"

    if values and all(int_re.match(value) for value in values):
        return "INTEGER"
    if values and all(int_re.match(value) or real_re.match(value) for value in values):
        return "REAL"

    return "TEXT"


def convert_for_sqlite(value: str, sqlite_type: str):
    value = (value or "").strip()
    if value == "":
        return None
    if sqlite_type == "BOOLEAN":
        return 1 if value.lower() == "true" else 0
    if sqlite_type == "INTEGER":
        return int(value)
    if sqlite_type == "REAL":
        return float(value)
    return value


def infer_csv_schema(csv_path: Path) -> dict[str, str]:
    samples: dict[str, list[str]] = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return {}
        samples = {column: [] for column in reader.fieldnames}
        for row in reader:
            for column, value in row.items():
                if value and value.strip() and len(samples[column]) < 1000:
                    samples[column].append(value)
            if all(len(values) >= 1000 for values in samples.values()):
                break
    return {column: infer_sqlite_type(column, values) for column, values in samples.items()}


def bootstrap_database(db_path: Path, csv_dir: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        return

    print(f"Building SQLite database from CSVs: {db_path}", file=sys.stderr)
    conn = connect(db_path)
    try:
        for csv_path in sorted(csv_dir.glob("*.csv")):
            table_name = csv_path.stem
            schema = infer_csv_schema(csv_path)
            with csv_path.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.reader(handle)
                headers = next(reader)
                columns_sql = ", ".join(f"{quote_ident(col)} {schema.get(col, 'TEXT')}" for col in headers)
                conn.execute(f"DROP TABLE IF EXISTS {quote_ident(table_name)}")
                conn.execute(f"CREATE TABLE {quote_ident(table_name)} ({columns_sql})")

                placeholders = ", ".join("?" for _ in headers)
                insert_sql = f"INSERT INTO {quote_ident(table_name)} VALUES ({placeholders})"
                batch: list[list[str]] = []
                for row in reader:
                    converted = [convert_for_sqlite(value, schema.get(column, "TEXT")) for column, value in zip(headers, row)]
                    batch.append(converted)
                    if len(batch) >= 10_000:
                        conn.executemany(insert_sql, batch)
                        batch.clear()
                if batch:
                    conn.executemany(insert_sql, batch)
                conn.commit()
                print(f"  imported {table_name}", file=sys.stderr)
    finally:
        conn.close()


def ensure_views(conn: sqlite3.Connection, view_sql_path: Path) -> None:
    sql = view_sql_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def normalize(text: str) -> str:
    return text.strip().lower()


def score_spec(question: str, spec: ViewSpec) -> int:
    q = normalize(question)
    score = 0
    for keyword in spec.keywords:
        if normalize(keyword) in q:
            score += 5
    for dim in spec.dimensions:
        if normalize(dim).replace("_", " ") in q:
            score += 2
    for metric in spec.metrics:
        if normalize(metric).replace("_", " ") in q:
            score += 3
    return score


def choose_view(question: str) -> ViewSpec:
    q = normalize(question)
    strong_routes = (
        (("warranty", "เคลม", "ประกัน"), "VW_FACT_WARRANTY_CLAIM_ENRICHED"),
        (("payroll", "salary", "เงินเดือน", "ค่าจ้าง"), "VW_FACT_PAYROLL_ENRICHED"),
        (("loyalty", "ledger", "แต้ม", "คะแนนสมาชิก"), "VW_FACT_LOYALTY_LEDGER_ENRICHED"),
        (("inventory movement", "stock movement"), "VW_FACT_INVENTORY_MOVEMENT_ENRICHED"),
        (("snapshot", "closing stock", "สินค้าคงเหลือ"), "VW_FACT_INVENTORY_MONTHLY_SNAPSHOT_ENRICHED"),
        (("refund", "คืนเงิน"), "VW_FACT_REFUND_PAID_ENRICHED"),
        (("return", "คืนสินค้า"), "VW_FACT_RETURN_ENRICHED"),
        (("vendor payment", "จ่าย vendor"), "VW_FACT_VENDOR_PAYMENT_ENRICHED"),
        (("shipping", "delivery", "ขนส่ง"), "VW_FACT_SHIPPING_ENRICHED"),
        (("customer service", "cs ", "บริการลูกค้า"), "VW_FACT_CS_INTERACTION_ENRICHED"),
        (("bank", "ธนาคาร", "บัญชี"), "VW_FACT_BANK_TRANSACTION_ENRICHED"),
    )
    for hints, view_name in strong_routes:
        if any(hint in q for hint in hints):
            return VIEW_SPECS[view_name]

    scored = sorted(
        ((score_spec(question, spec), spec) for spec in VIEW_SPECS.values()),
        key=lambda item: item[0],
        reverse=True,
    )
    best_score, best = scored[0]
    if best_score == 0:
        return VIEW_SPECS["VW_FACT_SALES_ENRICHED"]
    return best


def extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        candidate = cleaned[match.start() :]
        try:
            parsed, _ = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError(f"LLM did not return a valid JSON object: {text[:500]}")


def call_chat_completion(
    *,
    api_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int = 2048,
    temperature: float = 0.1,
    timeout: int = 60,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        api_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "curl/8.0.0",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API HTTP {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"LLM API connection failed: {exc}") from exc

    parsed = json.loads(body)
    return parsed["choices"][0]["message"]["content"]


def load_question_by_id(path: Path, question_id: str) -> str:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("id") == question_id:
                return row["question"]
    raise ValueError(f"Question id not found: {question_id}")


def schema_prompt(conn: sqlite3.Connection) -> str:
    names = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    lines = ["SQLite schema:"]
    for name in names:
        columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({quote_ident(name)})")]
        lines.append(f"- {name}({', '.join(columns)})")

    lines.append(
        """
Important join paths:
- FACT_SALES.branch_code -> DIM_BRANCH.branch_code
- FACT_SALES.customer_id -> DIM_CUSTOMER.customer_id
- FACT_SALES.employee_id -> DIM_EMPLOYEE.employee_id
- FACT_SALES.promo_campaign_id -> DIM_PROMO_CAMPAIGN.campaign_id
- FACT_SALES_LINE_ITEM.txn_id -> FACT_SALES.txn_id
- FACT_SALES_LINE_ITEM.sku_id -> DIM_PRODUCT.sku_id
- FACT_RETURN.sku_id -> DIM_PRODUCT.sku_id
- FACT_RETURN.branch_code -> DIM_BRANCH.branch_code
- FACT_RETURN.customer_id -> DIM_CUSTOMER.customer_id
- FACT_RETURN.approved_by_employee_id -> DIM_EMPLOYEE.employee_id
- FACT_REFUND_PAID.return_id -> FACT_RETURN.return_id
- FACT_REFUND_PAID.customer_id -> DIM_CUSTOMER.customer_id
- FACT_REFUND_PAID.approver_employee_id -> DIM_EMPLOYEE.employee_id
- FACT_REFUND_PAID.cosig_employee_id -> DIM_EMPLOYEE.employee_id
- FACT_REFUND_PAID.bank_txn_id -> FACT_BANK_TRANSACTION.bank_txn_id
- FACT_PAYROLL.employee_id -> DIM_EMPLOYEE.employee_id -> DIM_DEPARTMENT.dept_code
- FACT_SHIPPING.vendor_id -> DIM_VENDOR.vendor_id
- FACT_SHIPPING.origin_branch_code -> DIM_BRANCH.branch_code
- FACT_VENDOR_PAYMENT.vendor_id -> DIM_VENDOR.vendor_id
- FACT_VENDOR_PAYMENT.vendor_contract_version_id -> DIM_VENDOR_CONTRACT_VERSION.contract_version_id
- FACT_BANK_TRANSACTION.account_id -> DIM_BANK_ACCOUNT.account_id
- FACT_INVENTORY_MOVEMENT.sku_id -> DIM_PRODUCT.sku_id
- FACT_INVENTORY_MOVEMENT.branch_code -> DIM_BRANCH.branch_code
- FACT_INVENTORY_MONTHLY_SNAPSHOT.sku_id -> DIM_PRODUCT.sku_id
- FACT_INVENTORY_MONTHLY_SNAPSHOT.branch_code -> DIM_BRANCH.branch_code
- FACT_LOYALTY_LEDGER.customer_id -> DIM_CUSTOMER.customer_id
- FACT_WARRANTY_CLAIM.customer_id -> DIM_CUSTOMER.customer_id
- FACT_WARRANTY_CLAIM.sku_id -> DIM_PRODUCT.sku_id
- dim_product_recall_history.sku_id -> DIM_PRODUCT.sku_id
- dim_promo_mechanic.campaign_id -> DIM_PROMO_CAMPAIGN.campaign_id
- dim_signing_authority_ladder.policy_version_id -> DIM_POLICY_VERSION.policy_version_id
- dim_signing_authority_ladder.position_level_code -> DIM_POSITION_LEVEL.position_level_code
- dim_signing_authority_ladder.dept_code -> DIM_DEPARTMENT.dept_code

Date notes:
- Dates are stored as text YYYY-MM-DD. Use substr(date_col,1,4) for calendar year and substr(date_col,1,7) for month.
- Thai Buddhist years in questions map to Gregorian years: 2567=2024, 2568=2025.
- DIM_DATE.fiscal_year is Buddhist Era in this dataset.
- Empty CSV fields are stored as empty strings, not SQL NULL, in generated fahmai_agentic.db. Check both '' and NULL when needed.

Safety and correctness:
- Use only SELECT queries.
- Prefer enriched VW_FACT_*_ENRICHED views for FACT questions when they already contain the joined dimension attributes.
- Prefer source tables for exact question wording. Enriched views are allowed when helpful.
- Always qualify columns with table aliases when more than one table is used.
- Do not invent columns. Use aliases for computed outputs.
- DIM_VENDOR company names are in name_en/name_th, not vendor_name_en unless using an enriched view.
- DIM_PRODUCT has sku_id. FACT_SALES_LINE_ITEM has sku_id. FACT_SALES does not have sku_id; join through FACT_SALES_LINE_ITEM.
- For percentages, multiply by 100.0.
- For policy effective date questions, filter effective_date <= target date AND (end_date > target date OR end_date IS NULL OR end_date = '') then ORDER BY effective_date DESC LIMIT 1.
- In DIM_POLICY_VERSION, policy_class is broad (return, membership, signing_authority, warranty, shipping, refund). The specific named policy is usually policy_variable, e.g. refund_signing_authority_ladder, point_earning_rate_per_thb, refund_threshold_thb, return_window_days.
- "current version" for DIM_POLICY_VERSION usually means end_date IS NULL OR end_date = ''. Then choose the latest effective_date.
""".strip()
    )
    return "\n".join(lines)


def llm_generate_sql(
    question: str,
    conn: sqlite3.Connection,
    *,
    api_url: str,
    api_key: str,
    model: str,
) -> tuple[str, str]:
    system_prompt = f"""
You are a careful SQLite analyst for the FahMai public data bundle.
Generate exactly one read-only SQLite SELECT query that answers the user's question.
Return JSON only:
{{"sql":"SELECT ...","rationale":"short Thai explanation"}}

{schema_prompt(conn)}
""".strip()
    content = call_chat_completion(
        api_url=api_url,
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.05,
    )
    raw = extract_json_object(content)
    sql = str(raw.get("sql") or "").strip().rstrip(";")
    rationale = str(raw.get("rationale") or "LLM generated SQL from schema.").strip()
    return sql, rationale


def repair_sql_with_llm(
    *,
    question: str,
    bad_sql: str,
    error: str,
    conn: sqlite3.Connection,
    api_url: str,
    api_key: str,
    model: str,
) -> tuple[str, str]:
    system_prompt = f"""
You repair SQLite SELECT queries. Return JSON only:
{{"sql":"SELECT ...","rationale":"short Thai explanation"}}

Fix the query using the schema. Do not invent columns.
Always qualify columns with aliases. If a requested friendly name does not exist on a base DIM table, use the real column and alias it.

{schema_prompt(conn)}
""".strip()
    user_prompt = f"Question:\n{question}\n\nBad SQL:\n{bad_sql}\n\nSQLite error:\n{error}"
    content = call_chat_completion(
        api_url=api_url,
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.05,
    )
    raw = extract_json_object(content)
    sql = str(raw.get("sql") or "").strip().rstrip(";")
    rationale = str(raw.get("rationale") or "LLM repaired SQL from SQLite error.").strip()
    return sql, rationale


def allowed_group_values(columns: set[str]) -> list[str]:
    values = ["event_year", "event_month"]
    values.extend(sorted(columns))
    return values


def llm_plan_query(
    question: str,
    conn: sqlite3.Connection,
    *,
    limit: int,
    api_url: str,
    api_key: str,
    model: str,
) -> tuple[QueryPlan, str]:
    schema_summary = catalog_prompt()
    system_prompt = f"""
You are a strict planner for a SQLite analytics agent.
Return JSON only. Do not write SQL.

You must choose only from the approved enriched views, metrics, and dimensions below.
The Python program will validate your choices and generate SQL.

JSON schema:
{{
  "view_name": "one approved view name",
  "metric": "one metric from that view, or null for row count",
  "aggregate": "SUM or COUNT",
  "group_by": ["zero or more dimension columns, event_year, or event_month"],
  "year": 2024 or 2025 or null,
  "branch_codes": ["optional branch codes such as BKK-SIAM"],
  "channel": "online, web, retail, or null",
  "limit": integer,
  "rationale": "short reason in Thai"
}}

Rules:
- If the user asks for "ปี 2567", use year 2024. If "ปี 2568", use year 2025.
- Use event_year/event_month for calendar grouping, not fiscal_year, unless the user explicitly asks fiscal year.
- Do not invent tables, joins, columns, filters, or metrics.
- Prefer COUNT only when the user asks count/how many/จำนวน.
- Keep group_by small, usually 1-3 fields.

{schema_summary}
""".strip()
    content = call_chat_completion(
        api_url=api_url,
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.1,
    )
    raw = extract_json_object(content)
    structured = normalize_llm_output(raw, conn, fallback_question=question, fallback_limit=limit)
    return structured_to_query_plan(structured, conn)


def normalize_llm_output(
    raw: dict,
    conn: sqlite3.Connection,
    *,
    fallback_question: str,
    fallback_limit: int,
) -> StructuredPlannerOutput:
    view_name = str(raw.get("view_name") or "").strip()
    if view_name not in VIEW_SPECS:
        view_name = choose_view(fallback_question).name

    spec = VIEW_SPECS[view_name]
    columns = available_columns(conn, view_name)

    aggregate = str(raw.get("aggregate") or "SUM").strip().upper()
    if aggregate not in {"SUM", "COUNT"}:
        aggregate = "SUM"

    metric = raw.get("metric")
    if metric in ("", "null"):
        metric = None
    if metric is not None:
        metric = str(metric).strip()
    if aggregate == "COUNT":
        metric = None
    elif metric not in spec.metrics or metric not in columns:
        metric = spec.metrics[0] if spec.metrics else None
        if metric is None:
            aggregate = "COUNT"

    valid_groups = set(allowed_group_values(columns))
    group_by = tuple(
        group
        for group in (str(item).strip() for item in raw.get("group_by") or [])
        if group in valid_groups
    )

    year = raw.get("year")
    try:
        year = int(year) if year is not None else None
    except (TypeError, ValueError):
        year = None
    if year is not None and year >= 2500:
        year -= 543
    if year not in (2024, 2025):
        year = None

    branch_codes = tuple(
        code
        for code in (str(item).strip().upper() for item in raw.get("branch_codes") or [])
        if re.fullmatch(r"[A-Z]{3}-[A-Z0-9]{2,5}", code)
    )

    channel = raw.get("channel")
    channel = str(channel).strip().lower() if channel is not None else None
    if channel not in {"online", "web", "retail"}:
        channel = None

    try:
        llm_limit = int(raw.get("limit") or fallback_limit)
    except (TypeError, ValueError):
        llm_limit = fallback_limit
    llm_limit = max(1, min(llm_limit, fallback_limit, 100))

    rationale = str(raw.get("rationale") or spec.description).strip()
    return StructuredPlannerOutput(
        view_name=view_name,
        metric=metric,
        aggregate=aggregate,
        group_by=group_by[:4],
        year=year,
        branch_codes=branch_codes,
        channel=channel,
        limit=llm_limit,
        rationale=rationale,
    )


def structured_to_query_plan(
    structured: StructuredPlannerOutput,
    conn: sqlite3.Connection,
) -> tuple[QueryPlan, str]:
    columns = available_columns(conn, structured.view_name)
    filters: list[str] = []
    if structured.year is not None:
        if "business_event_date" in columns:
            filters.append(f"substr(business_event_date, 1, 4) = '{structured.year}'")
        elif "pay_period_end" in columns:
            filters.append(f"substr(pay_period_end, 1, 4) = '{structured.year}'")

    if structured.branch_codes:
        branch_col = next(
            (col for col in ("branch_code", "employee_branch_code", "origin_branch_code", "associated_branch_code") if col in columns),
            None,
        )
        if branch_col:
            quoted = ", ".join("'" + code.replace("'", "''") + "'" for code in structured.branch_codes)
            filters.append(f"{quote_ident(branch_col)} IN ({quoted})")

    if structured.channel and "channel" in columns:
        filters.append(f"LOWER(channel) = '{structured.channel}'")

    plan = QueryPlan(
        view_name=structured.view_name,
        metric=structured.metric,
        aggregate=structured.aggregate,
        group_by=structured.group_by,
        filters=tuple(filters),
        limit=structured.limit,
        rationale=structured.rationale,
    )
    return plan, build_sql(plan, columns)


def choose_metric(question: str, spec: ViewSpec) -> tuple[str | None, str]:
    q = normalize(question)
    if any(word in q for word in ("count", "how many", "จำนวนรายการ", "กี่รายการ", "นับ")):
        return None, "COUNT"

    for hints, metric in METRIC_HINTS:
        if metric in spec.metrics and any(hint in q for hint in hints):
            return metric, "SUM"

    if spec.metrics:
        return spec.metrics[0], "SUM"
    return None, "COUNT"


def available_columns(conn: sqlite3.Connection, view_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({quote_ident(view_name)})")}


def choose_groups(question: str, columns: set[str]) -> tuple[str, ...]:
    q = normalize(question)
    groups: list[str] = []

    if any(word in q for word in ("year", "ปี", "รายปี")):
        groups.append("event_year")

    if any(word in q for word in ("month", "เดือน", "รายเดือน")):
        groups.append("event_month")

    for hints, column in GROUP_HINTS:
        if column in columns and any(hint in q for hint in hints):
            groups.append(column)

    if "pay period" in q or "งวดเงินเดือน" in q:
        if "period_end_fiscal_year" in columns:
            groups.append("period_end_fiscal_year")
        if "period_end_fiscal_quarter" in columns and ("quarter" in q or "ไตรมาส" in q):
            groups.append("period_end_fiscal_quarter")

    deduped: list[str] = []
    for group in groups:
        if group not in deduped:
            deduped.append(group)
    return tuple(deduped[:4])


def extract_filters(question: str, columns: set[str]) -> tuple[str, ...]:
    q = normalize(question)
    filters: list[str] = []

    years = set(re.findall(r"\b(2024|2025|2567|2568)\b", question))
    for year_text in sorted(years):
        year = int(year_text)
        if year >= 2500:
            year -= 543
        if "business_event_date" in columns:
            filters.append(f"substr(business_event_date, 1, 4) = '{year}'")
        elif "pay_period_end" in columns:
            filters.append(f"substr(pay_period_end, 1, 4) = '{year}'")

    code_match = re.findall(r"\b[A-Z]{3}-[A-Z0-9]{2,5}\b", question)
    if code_match:
        branch_col = next(
            (col for col in ("branch_code", "employee_branch_code", "origin_branch_code", "associated_branch_code") if col in columns),
            None,
        )
        if branch_col:
            quoted = ", ".join("'" + code.replace("'", "''") + "'" for code in code_match)
            filters.append(f"{quote_ident(branch_col)} IN ({quoted})")

    if any(word in q for word in ("b2b", "องค์กร")) and "is_b2b" in columns:
        filters.append("is_b2b = 'true'")
    if any(word in q for word in ("online", "web", "ออนไลน์")) and "channel" in columns:
        filters.append("LOWER(channel) IN ('online', 'web')")
    if any(word in q for word in ("retail", "หน้าร้าน")) and "channel" in columns:
        filters.append("LOWER(channel) = 'retail'")

    return tuple(filters)


def build_sql(plan: QueryPlan, columns: set[str]) -> str:
    select_parts: list[str] = []
    group_exprs: list[str] = []

    for group in plan.group_by:
        if group == "event_year":
            select_parts.append("substr(business_event_date, 1, 4) AS event_year")
            group_exprs.append("event_year")
        elif group == "event_month":
            select_parts.append("substr(business_event_date, 1, 7) AS event_month")
            group_exprs.append("event_month")
        elif group in columns:
            select_parts.append(quote_ident(group))
            group_exprs.append(quote_ident(group))

    if plan.aggregate == "COUNT":
        metric_expr = "COUNT(*) AS row_count"
        order_col = "row_count"
    else:
        if plan.metric is None:
            metric_expr = "COUNT(*) AS row_count"
            order_col = "row_count"
        else:
            metric_expr = f"SUM(CAST({quote_ident(plan.metric)} AS REAL)) AS total_{plan.metric}"
            order_col = f"total_{plan.metric}"

    select_parts.append(metric_expr)

    sql = f"SELECT {', '.join(select_parts)}\nFROM {quote_ident(plan.view_name)}"
    if plan.filters:
        sql += "\nWHERE " + " AND ".join(plan.filters)
    if group_exprs:
        sql += "\nGROUP BY " + ", ".join(group_exprs)
    sql += f"\nORDER BY {quote_ident(order_col)} DESC"
    sql += f"\nLIMIT {int(plan.limit)}"
    return sql


def plan_query(question: str, conn: sqlite3.Connection, limit: int) -> tuple[QueryPlan, str]:
    spec = choose_view(question)
    columns = available_columns(conn, spec.name)
    metric, aggregate = choose_metric(question, spec)
    groups = choose_groups(question, columns)
    filters = extract_filters(question, columns)
    plan = QueryPlan(
        view_name=spec.name,
        metric=metric,
        aggregate=aggregate,
        group_by=groups,
        filters=filters,
        limit=limit,
        rationale=spec.description,
    )
    return plan, build_sql(plan, columns)


def validate_readonly_sql(sql: str) -> None:
    stripped = sql.strip().lower()
    if not stripped.startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")
    forbidden = (" insert ", " update ", " delete ", " drop ", " alter ", " create ", " attach ", " detach ", " pragma ")
    padded = " " + re.sub(r"\s+", " ", stripped) + " "
    if any(token in padded for token in forbidden):
        raise ValueError("Query contains a forbidden SQL operation.")


def repair_known_sql_aliases(sql: str) -> str:
    """Fix common friendly-column aliases when the LLM uses base DIM tables."""
    replacements: list[tuple[str, str]] = []
    if re.search(r"\bDIM_VENDOR\b", sql, flags=re.IGNORECASE):
        replacements.extend(
            [
                (r"\bvendor_name_en\b", "DIM_VENDOR.name_en"),
                (r"\bvendor_name_th\b", "DIM_VENDOR.name_th"),
                (r"\bvendor_category\b", "DIM_VENDOR.category"),
            ]
        )
    if re.search(r"\bDIM_PROMO_CAMPAIGN\b", sql, flags=re.IGNORECASE):
        replacements.extend(
            [
                (r"\bcampaign_description_en\b", "DIM_PROMO_CAMPAIGN.description_en"),
                (r"\bcampaign_description_th\b", "DIM_PROMO_CAMPAIGN.description_th"),
            ]
        )
    if re.search(r"\bDIM_BRANCH\b", sql, flags=re.IGNORECASE):
        replacements.extend(
            [
                (r"\bbranch_name_en\b", "DIM_BRANCH.name_en"),
                (r"\bbranch_name_th\b", "DIM_BRANCH.name_th"),
            ]
        )
    repaired = sql
    for pattern, replacement in replacements:
        repaired = re.sub(pattern, replacement, repaired)
    return repaired


def repair_known_empty_result_sql(sql: str) -> str | None:
    """Try conservative rewrites for valid SQL that returns no rows."""
    if not re.search(r"\bDIM_POLICY_VERSION\b", sql, flags=re.IGNORECASE):
        return None
    if not re.search(r"\bpolicy_variable\s*=", sql, flags=re.IGNORECASE):
        return None
    repaired = re.sub(
        r"\s+AND\s+policy_class\s*=\s*'[^']*'",
        "",
        sql,
        flags=re.IGNORECASE,
    )
    repaired = re.sub(
        r"\s+WHERE\s+policy_class\s*=\s*'[^']*'\s+AND\s+",
        " WHERE ",
        repaired,
        flags=re.IGNORECASE,
    )
    return repaired if repaired != sql else None


def execute_sql(conn: sqlite3.Connection, sql: str) -> list[sqlite3.Row]:
    sql = repair_known_sql_aliases(sql)
    validate_readonly_sql(sql)
    return conn.execute(sql).fetchall()


def markdown_table(rows: Iterable[sqlite3.Row]) -> str:
    rows = list(rows)
    if not rows:
        return "(no rows)"
    headers = rows[0].keys()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = []
        for header in headers:
            value = row[header]
            if isinstance(value, float):
                value = f"{value:,.2f}"
            values.append("" if value is None else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def rows_to_jsonable(rows: Iterable[sqlite3.Row], max_rows: int = 200) -> list[dict]:
    json_rows: list[dict] = []
    for idx, row in enumerate(rows):
        if idx >= max_rows:
            break
        json_rows.append({key: row[key] for key in row.keys()})
    return json_rows


def deterministic_final_answer(question: str, rows: list[sqlite3.Row]) -> str | None:
    """Handle a few exact benchmark formats without spending an LLM call."""
    q = normalize(question)
    if "tuple 12" in q and "distinct" in q and "sku" in q and "แต่ละเดือน" in q:
        month_count: dict[int, int] = {}
        for row in rows:
            data = {key: row[key] for key in row.keys()}
            month_value = data.get("month") or data.get("event_month") or data.get("sales_month")
            count_value = (
                data.get("distinct_sku_count")
                or data.get("sku_count")
                or data.get("count_distinct_sku_id")
                or data.get("COUNT(DISTINCT sku_id)")
            )
            if month_value is None or count_value is None:
                continue
            month_text = str(month_value)
            month_num = int(month_text[-2:]) if "-" in month_text else int(month_text)
            month_count[month_num] = int(count_value)
        if len(month_count) == 12:
            values = tuple(month_count[month] for month in range(1, 13))
            return str(values)
    return None


def synthesize_final_answer(
    *,
    question: str,
    sql: str,
    rows: list[sqlite3.Row],
    api_url: str,
    api_key: str,
    model: str,
) -> str:
    deterministic = deterministic_final_answer(question, rows)
    if deterministic is not None:
        return deterministic

    rows_json = json.dumps(rows_to_jsonable(rows), ensure_ascii=False, default=str)
    system_prompt = """
You are the final-answer formatter for a data QA pipeline.
Use only the SQL result rows provided. Do not invent numbers.
Answer in Thai unless the user explicitly asks otherwise.
Match the requested output shape exactly: tuple, list, top-N rows, short paragraph, or specific fields.
If the question asks for a tuple, output the tuple clearly and in the requested order.
If rows are empty, say that no matching rows were found.
Do not include markdown tables unless the user asks for a table.
""".strip()
    user_prompt = f"""
Question:
{question}

SQL:
{sql}

Rows as JSON:
{rows_json}

Final answer:
""".strip()
    return call_chat_completion(
        api_url=api_url,
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=1024,
    ).strip()


def print_agent_output(
    *,
    planner: str,
    question: str,
    sql: str,
    rows: list[sqlite3.Row],
    rationale: str | None,
    question_id: str | None,
    answer_format: str,
    api_url: str,
    api_key: str | None,
    model: str,
    view_name: str | None = None,
) -> None:
    print(f"Planner: {planner}")
    if question_id:
        print(f"Question ID: {question_id}")
    print(f"Question: {question}")
    if view_name:
        print(f"View: {view_name}")
    if rationale:
        print(f"Reason: {rationale}")
    print()
    print("SQL:")
    print(sql)

    if answer_format in {"table", "both"}:
        print()
        print(markdown_table(rows))

    if answer_format in {"final", "both"}:
        if not api_key:
            raise ValueError("--answer-format final/both requires --llm-api-key or THAILLM_API_KEY.")
        final_answer = synthesize_final_answer(
            question=question,
            sql=sql,
            rows=rows,
            api_url=api_url,
            api_key=api_key,
            model=model,
        )
        print()
        print("Final Answer:")
        print(final_answer)


def main() -> int:
    parser = argparse.ArgumentParser(description="FahMai prompt-to-SQL agent over enriched FACT/DIM views.")
    parser.add_argument("question", nargs="*", help="Natural-language question, Thai or English.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"SQLite DB path. Default: {DEFAULT_DB}")
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR, help="CSV table directory for first-time DB build.")
    parser.add_argument("--view-sql", type=Path, default=DEFAULT_VIEW_SQL, help="SQL file that creates enriched views.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum output rows.")
    parser.add_argument("--sql", help="Run a read-only SQL query directly instead of planning from a prompt.")
    parser.add_argument("--planner", choices=("rules", "llm", "llm-sql"), default="rules", help="Planning mode. Default: rules.")
    parser.add_argument("--llm-api-url", default=os.getenv("THAILLM_API_URL", "http://thaillm.or.th/api/v1/chat/completions"))
    parser.add_argument("--llm-model", default=os.getenv("THAILLM_MODEL", "typhoon-s-thaillm-8b-instruct"))
    parser.add_argument("--llm-api-key", default=os.getenv("THAILLM_API_KEY"), help="ThaiLLM bearer token. Prefer THAILLM_API_KEY.")
    parser.add_argument("--fallback-to-rules", action="store_true", help="If LLM planning fails, use deterministic rule planning.")
    parser.add_argument("--question-id", help="Load a question from questions.csv by id, e.g. L3-Q-EASY-001.")
    parser.add_argument("--questions-csv", type=Path, default=DEFAULT_QUESTIONS_CSV, help="questions.csv path for --question-id.")
    parser.add_argument(
        "--answer-format",
        choices=("table", "final", "both"),
        default="table",
        help="Output raw result table, synthesized final answer, or both. Default: table.",
    )
    parser.add_argument("--rebuild-db", action="store_true", help="Delete and rebuild the generated SQLite DB from CSV files.")
    args = parser.parse_args()

    if args.rebuild_db and args.db.exists():
        args.db.unlink()
    bootstrap_database(args.db, args.csv_dir)

    conn = connect(args.db)
    try:
        ensure_views(conn, args.view_sql)
        if args.sql:
            sql = repair_known_sql_aliases(args.sql)
            rows = execute_sql(conn, sql)
            print_agent_output(
                planner="direct-sql",
                question=args.sql,
                sql=sql,
                rows=rows,
                rationale=None,
                question_id=None,
                answer_format=args.answer_format,
                api_url=args.llm_api_url,
                api_key=args.llm_api_key,
                model=args.llm_model,
            )
            return 0

        question = load_question_by_id(args.questions_csv, args.question_id) if args.question_id else " ".join(args.question).strip()
        if not question:
            parser.error("Please provide a question or --sql.")

        if args.planner == "llm-sql":
            if not args.llm_api_key:
                parser.error("LLM SQL planner requires --llm-api-key or THAILLM_API_KEY.")
            try:
                sql, rationale = llm_generate_sql(
                    question,
                    conn,
                    api_url=args.llm_api_url,
                    api_key=args.llm_api_key,
                    model=args.llm_model,
                )
                rows = None
                last_error = None
                for attempt in range(3):
                    try:
                        sql = repair_known_sql_aliases(sql)
                        rows = execute_sql(conn, sql)
                        if not rows:
                            repaired_empty = repair_known_empty_result_sql(sql)
                            if repaired_empty:
                                retry_rows = execute_sql(conn, repaired_empty)
                                if retry_rows:
                                    print("Applied empty-result repair for DIM_POLICY_VERSION policy lookup.", file=sys.stderr)
                                    sql = repaired_empty
                                    rows = retry_rows
                        break
                    except sqlite3.Error as exc:
                        last_error = exc
                        print(f"LLM SQL attempt {attempt + 1} failed: {exc}", file=sys.stderr)
                        print(f"Failed SQL:\n{sql}", file=sys.stderr)
                        if attempt == 2:
                            raise
                        sql, rationale = repair_sql_with_llm(
                            question=question,
                            bad_sql=sql,
                            error=str(exc),
                            conn=conn,
                            api_url=args.llm_api_url,
                            api_key=args.llm_api_key,
                            model=args.llm_model,
                        )
                if rows is None:
                    raise sqlite3.Error(last_error or "SQL execution failed")
            except RuntimeError as exc:
                if not args.fallback_to_rules:
                    raise
                print(f"LLM SQL planner failed, falling back to rules: {exc}", file=sys.stderr)
                plan, sql = plan_query(question, conn, args.limit)
                rows = execute_sql(conn, sql)
                rationale = plan.rationale
            except sqlite3.Error as exc:
                if not args.fallback_to_rules:
                    raise
                print(f"LLM SQL execution failed, falling back to rules: {exc}", file=sys.stderr)
                plan, sql = plan_query(question, conn, args.limit)
                rows = execute_sql(conn, sql)
                rationale = plan.rationale
            print_agent_output(
                planner=args.planner,
                question=question,
                sql=sql,
                rows=rows,
                rationale=rationale,
                question_id=args.question_id,
                answer_format=args.answer_format,
                api_url=args.llm_api_url,
                api_key=args.llm_api_key,
                model=args.llm_model,
            )
            return 0

        if args.planner == "llm":
            if not args.llm_api_key:
                parser.error("LLM planner requires --llm-api-key or THAILLM_API_KEY.")
            try:
                plan, sql = llm_plan_query(
                    question,
                    conn,
                    limit=args.limit,
                    api_url=args.llm_api_url,
                    api_key=args.llm_api_key,
                    model=args.llm_model,
                )
            except RuntimeError as exc:
                if not args.fallback_to_rules:
                    raise
                print(f"LLM planner failed, falling back to rules: {exc}", file=sys.stderr)
                plan, sql = plan_query(question, conn, args.limit)
        else:
            plan, sql = plan_query(question, conn, args.limit)
        sql = repair_known_sql_aliases(sql)
        rows = execute_sql(conn, sql)

        print_agent_output(
            planner=args.planner,
            question=question,
            sql=sql,
            rows=rows,
            rationale=plan.rationale,
            question_id=args.question_id,
            answer_format=args.answer_format,
            api_url=args.llm_api_url,
            api_key=args.llm_api_key,
            model=args.llm_model,
            view_name=plan.view_name,
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
