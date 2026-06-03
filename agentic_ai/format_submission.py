#!/usr/bin/env python3
"""Format markdown-table agent answers into sample_submission-compatible responses."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def split_markdown_row(line: str) -> list[str]:
    placeholder = "\u241f"
    protected = line.strip().replace("\\|", placeholder)
    parts = [part.strip().replace(placeholder, "|") for part in protected.strip("|").split("|")]
    return parts


def parse_markdown_table(text: str) -> tuple[list[str], list[dict[str, str]]]:
    if not text or text.strip() == "(no rows)" or text.startswith("ERROR:"):
        return [], []
    lines = [line for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return [], []
    headers = split_markdown_row(lines[0])
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        values = split_markdown_row(line)
        if len(values) != len(headers):
            continue
        rows.append(dict(zip(headers, values)))
    return headers, rows


def one_decimal(value: str) -> str:
    try:
        return f"{float(value.replace(',', '')):.1f}"
    except Exception:
        return value


def join_nonempty(parts: list[str], sep: str = ", ") -> str:
    return sep.join(part for part in parts if part and part != "None")


def format_rows(question: str, answer: str) -> str:
    q = question.lower()
    headers, rows = parse_markdown_table(answer)
    if not rows:
        if any(term in q for term in ("ceo", "cfo", "nps", "line works", "line oa", "อีเมล", "บันทึกการประชุม")):
            return "ไม่พบข้อมูลที่ยืนยันได้จากตาราง SQL ที่โหลดอยู่"
        return "0"

    r = rows[0]
    h = set(headers)

    if {"vendor_invoice_id", "payment_id", "duplicate_count"} <= h:
        payments = "; ".join(
            f"{x['payment_id']} ({x.get('business_event_date','')}/{x.get('posting_date','')}, {x.get('paid_amount_thb','')} THB)"
            for x in rows
        )
        return (
            f"(1) invoice_id={r['vendor_invoice_id']} "
            f"(2) payment records={r['duplicate_count']} "
            f"(3) records: {payments}"
        )

    if {"phantom_duplicate_rows", "discount_after_dedup_thb", "inflation_pct_vs_dedup"} <= h:
        line_note = "LINE WORKS evidence ไม่อยู่ใน SQL tables ที่โหลดอยู่" if "line works" in q else ""
        return join_nonempty(
            [
                f"campaign_id={r.get('campaign_id','')}",
                f"phantom/log duplicate rows={r['phantom_duplicate_rows']}",
                f"real rows after dedup={r.get('real_redemption_rows_after_dedup') or r.get('unique_redemption_rows_after_dedup','')}",
                f"phantom discount={r.get('phantom_discount_thb','')} THB",
                f"dedup discount={r.get('discount_after_dedup_thb') or r.get('net_discount_cost_after_dedup_thb','')} THB",
                f"inflation={r['inflation_pct_vs_dedup']}%",
                line_note,
            ]
        )

    if {"phantom_duplicate_rows", "unique_redemption_rows_after_dedup", "roi_ratio", "paywise_payment_rows"} <= h:
        return (
            f"campaign {r['campaign_id']}: raw redemption rows={r['total_redemption_rows']}, "
            f"phantom duplicate rows={r['phantom_duplicate_rows']}, unique rows after dedup={r['unique_redemption_rows_after_dedup']}, "
            f"net discount cost={r['net_discount_cost_after_dedup_thb']} THB, dedup net revenue={r['dedup_net_revenue_thb']} THB, "
            f"ROI={r['roi_ratio']}x, PayWise payment={r['paywise_payment_rows']} rows/{r['paywise_paid_amount_thb']} THB"
        )

    if {"payment_record_count", "active_contract_versions", "inferred_true_overpayment_thb"} <= h:
        return (
            f"(1) invoice_id={r['vendor_invoice_id']} (2) payment records={r['payment_record_count']} "
            f"(3) payment_ids={r['payment_ids']} (4) amounts/dates={r['row_amount_and_dates']} "
            f"(5) active contracts={r['active_contract_versions']} "
            f"(6) contract-aware instances={r['distinct_payment_instances_after_contract_aware_dedupe']} "
            f"(7) cash outflow={r['total_cash_outflow_thb']} THB; bank matches={r['bank_amount_match_rows']}/{r['bank_crosscheck_rows']}; "
            f"inferred overpayment={r['inferred_true_overpayment_thb']} THB"
        )

    if {"spike_date", "remote_transaction_count", "dominant_sku_id"} <= h:
        return f"({r['spike_date']}, {r['dominant_sku_id']}, {r['remote_transaction_count']} transactions)"

    if {"sku_id", "branch_code", "return_count", "total_return_amount_thb"} <= h:
        return (
            f"SKU {r['sku_id']} ที่สาขา {r['branch_code']} ({r.get('affected_branch_name','')}) "
            f"ถูก return {r['return_count']} rows รวม {r['total_return_amount_thb']} THB"
        )

    if {"mismatch_count", "min_business_event_date", "max_posting_date", "max_lag_days"} <= h:
        return (
            f"มี {r['mismatch_count']} shipments; business_event_date {r['min_business_event_date']} ถึง "
            f"{r['max_business_event_date']}; posting_date {r.get('min_posting_date','')} ถึง {r['max_posting_date']}; "
            f"max lag {r['max_lag_days']} วัน"
        )

    if {"cross_month_posting_count", "total_vendor_payment_rows", "max_lag_days"} <= h:
        return f"({r['cross_month_posting_count']}, {r['total_vendor_payment_rows']}, {r['max_lag_days']} days)"

    if {"sales_year", "sales_quarter", "quarter_revenue_thb", "ratio_vs_baseline"} <= h:
        return (
            f"{r['sales_year']} Q{r['sales_quarter']}: revenue {r['quarter_revenue_thb']} THB, "
            f"baseline {r.get('baseline_avg_revenue_thb','')} THB, ratio {r['ratio_vs_baseline']}x"
        )

    if {"amount_thb", "business_event_date", "account_id", "primary_sku_id"} <= h:
        return (
            f"largest deposit คือ {r.get('bank_txn_id','')} วันที่ {r['business_event_date']} บัญชี {r['account_id']} "
            f"ยอด {r['amount_thb']} THB; driver หลักคือ campaign {r.get('primary_promo_campaign_id','')} "
            f"และ SKU {r['primary_sku_id']} ({r.get('primary_sku_units','')} units)"
        )

    if {"all_zero_sku_count", "snapshot_branch_count", "dim_branch_count"} <= h:
        coverage = "ตรงกับ DIM_BRANCH" if r["snapshot_branch_count"] == r["dim_branch_count"] else f"ไม่ตรง, missing={r.get('missing_branch_codes','')}"
        return (
            f"(1) all-zero SKU={r['all_zero_sku_count']} "
            f"(2) EOL-count={r.get('all_zero_sku_with_eol_count','0')} ({r.get('eol_schema_note','')}) "
            f"(3) snapshot branches={r['snapshot_branch_count']}/{r['dim_branch_count']} {coverage}"
        )

    if {"campaign_id", "roi_ratio", "discount_total_thb"} <= h:
        return f"({r['campaign_id']}, {one_decimal(r['roi_ratio'])}x)"

    if {"account_id", "month_deposit_thb", "year_deposit_thb", "month_share_pct"} <= h:
        return (
            f"{r['account_id']} deposit July 2025 = {r['month_deposit_thb']} THB "
            f"({r['month_deposit_count']} deposits), FY2025 deposit = {r['year_deposit_thb']} THB, "
            f"share = {r['month_share_pct']}%"
        )

    if {"vendor_id", "total_paid_thb", "vendor_spend_share_pct"} <= h:
        ranking = "; ".join(f"{x['vendor_id']} {x['total_paid_thb']} THB ({x['vendor_spend_share_pct']}%)" for x in rows)
        duplicate = next((x for x in rows if x.get("duplicate_invoice_id_count") not in ("", "0")), None)
        dup_text = f"; duplicate invoice พบที่ {duplicate['vendor_id']} จำนวน {duplicate['duplicate_invoice_id_count']}" if duplicate else ""
        return ranking + dup_text

    if {"total_opening_balance_quantity", "top_opening_branch_code", "same_day_transfer_in_quantity"} <= h:
        return (
            f"opening_balance รวม {r['total_opening_balance_quantity']} units จาก {r['opening_balance_rows']} rows/"
            f"{r['opening_balance_branches']} branches; top branch={r['top_opening_branch_code']} "
            f"{r['branch_opening_quantity']} units; same-day transfer_in={r['same_day_transfer_in_rows']} rows "
            f"{r['same_day_transfer_in_quantity']} units"
        )

    if {"current_ceo_employee_id", "top_refund_approver_employee_id"} <= h:
        return (
            f"current CEO={r['current_ceo_first_name_en']} {r['current_ceo_last_name_en']} "
            f"({r['current_ceo_employee_id']}, {r.get('current_ceo_role_label','')}); "
            f"top refund approver={r['top_refund_approver_first_name_en']} {r['top_refund_approver_last_name_en']} "
            f"({r['top_refund_approver_employee_id']}) {r['approved_refund_rows']} rows/{r['approved_refund_amount_thb']} THB; "
            f"is_current_ceo={r.get('top_approver_is_current_ceo','')}"
        )

    if {"carrier_vendor_id", "carrier_name_en", "carrier_shipment_rows_in_window"} <= h:
        return (
            f"(1) สาเหตุ delay จาก LINE WORKS ไม่สามารถยืนยันจาก SQL tables ที่โหลดอยู่ "
            f"(2) carrier={r['carrier_vendor_id']} {r['carrier_name_en']} "
            f"(3) shipments ในช่วง {r['window_start_date']} ถึง {r['window_end_date']} = "
            f"{r['carrier_shipment_rows_in_window']} rows"
        )

    if {"ic_approver_refund_rows", "approver_employee_id"} <= h:
        return (
            f"IC approver refunds={r['ic_approver_refund_rows']} rows รวม {r['ic_approver_refund_amount_thb']} THB; "
            f"top approver={r['first_name_en']} {r['last_name_en']} ({r['approver_employee_id']}, {r['position_title']}); "
            f"{r.get('evidence_note','')}"
        )

    if {"pre_pm1_violation_count", "post_pm1_violation_count", "employee_id"} <= h:
        return (
            f"CS-tier IC agent={r['first_name_en']} {r['last_name_en']} ({r['employee_id']}, {r['dept_code']}/{r['position_level']}); "
            f"pre-PM1 violations={r['pre_pm1_violation_count']} rows/{r['pre_pm1_violation_amount_thb']} THB; "
            f"post-PM1 violations={r['post_pm1_violation_count']} rows/{r['post_pm1_violation_amount_thb']} THB; "
            f"total violation amount={r['total_violation_amount_thb']} THB"
        )

    if {"non_fin_manager_refund_rows", "approver_employee_id"} <= h:
        return (
            f"non-FIN manager refunds={r['non_fin_manager_refund_rows']} rows รวม {r['non_fin_manager_refund_amount_thb']} THB; "
            f"top approver={r['first_name_en']} {r['last_name_en']} ({r['approver_employee_id']}, {r['dept_code']}); "
            f"{r.get('evidence_note','')}"
        )

    if {"status_record_count", "status", "transition_date"} <= h:
        states = "; ".join(f"{x['status']}:{x['transition_date']}" for x in rows)
        return f"recall state machine มี {r['status_record_count']} states/transitions: {states}"

    if {"as_of_date", "handover_date", "canon_role_label"} <= h:
        return (
            f"as_of={r['as_of_date']}; handover_date={r['handover_date']}; "
            f"{r['canon_role_label']}={r['first_name_en']} {r['last_name_en']} "
            f"({r['employee_id']}, {r['position_title']})"
        )

    if {"recall_state_machine", "vendor_recall_return_rows", "lost_revenue_thb"} <= h:
        return (
            f"{r['sku_id']} state={r['recall_state_machine']}; return rows={r['vendor_recall_return_rows']} "
            f"amount={r['return_amount_total_thb']} THB; refund={r['refund_paid_thb']} THB; "
            f"lost revenue={r['lost_revenue_thb']} THB; early-warning claims={r['early_warning_claims']}"
        )

    if {"unique_cohort_customers_after_dedup", "corrected_roi_ratio"} <= h:
        return (
            f"campaign {r['campaign_id']}: cohort customers={r['unique_cohort_customers_after_dedup']}, "
            f"discount cost={r['discount_cost_after_dedup_thb']} THB, gross sales={r['gross_sales_thb']} THB, "
            f"refund={r['in_window_refund_amount_thb']} THB, 12mo net revenue={r['ltv_12mo_net_revenue_thb']} THB, "
            f"corrected ROI={r['corrected_roi_ratio']}x"
        )

    if {"recall_return_rows", "top_approver_employee_id", "recall_branch_codes"} <= h:
        return (
            f"recall returns={r['recall_return_rows']} rows รวม {r['total_return_amount_thb']} THB; "
            f"top approver={r['top_approver_first_name_en']} {r['top_approver_last_name_en']} "
            f"({r['top_approver_employee_id']}) {r['top_approver_rows']} rows/{r['top_approver_pct']}%; "
            f"branches={r['recall_branch_count']} ({r['recall_branch_codes']}); days_since_purchase="
            f"{r['min_days_since_purchase']}-{r['max_days_since_purchase']} avg {r['avg_days_since_purchase']}"
        )

    if {"customer_id", "total_spent_thb", "top_sku_id"} <= h:
        return (
            f"top B2B account={r['customer_id']} total_spent={r['total_spent_thb']} THB "
            f"({r['transaction_count']} txns); anchor SKU={r['top_sku_id']} {r.get('brand_family','')}/"
            f"{r.get('category','')} {r.get('sku_units','')} units; active_months={r.get('distinct_active_months','')}"
        )

    if {"sku_id", "campaign_id", "preorder_units", "launch_day_units", "corrected_roi_ratio"} <= h or {"sku_id", "campaign_id", "preorder_units", "launch_day_units", "campaign_window_units"} <= h:
        return (
            f"SKU {r['sku_id']} / campaign {r['campaign_id']}: preorder={r.get('preorder_units','')} units "
            f"(avg {r.get('avg_preorder_daily_units','')}/day, pattern={r.get('preorder_daily_pattern','')}), "
            f"launch_day={r.get('launch_day_units','')} units, launch spike={r.get('launch_spike_vs_preorder_avg','')}x, "
            f"post_launch={r.get('post_launch_units','')} units, campaign_window={r.get('campaign_window_units','')} units, "
            f"full_july={r.get('full_july_units','')} units, campaign share={r.get('campaign_units_pct_of_july','')}%, "
            f"line discount={r.get('sku_line_discount_total_thb','')} THB"
        )

    if {"policy_version_id", "policy_variable", "value_numeric"} <= h:
        return (
            f"policy_version_id={r['policy_version_id']}, {r['policy_variable']}={r['value_numeric']}, "
            f"effective_date={r['effective_date']}, end_date={r.get('end_date','')}"
        )

    if {"sku_id", "event_fiscal_quarter", "row_count"} <= h and "top-selling sku" in q:
        top = rows[0]
        return f"top-selling SKU by rows in returned table={top['sku_id']}, count={top['row_count']}"

    if "row_count" in h and len(headers) <= 3:
        if any(term in q for term in ("line works", "line oa", "chat", "note ภายใน", "อีเมล", "บันทึกการประชุม")):
            return f"ไม่พบหลักฐานข้อความภายในจากตาราง SQL ที่โหลดอยู่; query คืนค่า row_count={r.get('row_count','')}"
        return "; ".join(", ".join(f"{k}={v}" for k, v in x.items()) for x in rows[:5])

    if any(term in q for term in ("nps", "อีเมล", "บันทึกการประชุม", "line oa")):
        return "ไม่พบข้อมูลเอกสาร/ข้อความที่ยืนยันคำตอบนี้ในตาราง SQL ที่โหลดอยู่"

    return "; ".join(", ".join(f"{k}={v}" for k, v in x.items()) for x in rows[:3])


def main() -> int:
    parser = argparse.ArgumentParser(description="Create sample_submission-style CSV from agent markdown answers.")
    parser.add_argument("--answers-csv", type=Path, required=True)
    parser.add_argument("--sample-csv", type=Path, default=ROOT / "sample_submission.csv")
    parser.add_argument("--easy-med-formatted-csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    answers = {row["id"]: row for row in read_csv(args.answers_csv)}
    easy_med: dict[str, str] = {}
    if args.easy_med_formatted_csv and args.easy_med_formatted_csv.exists():
        easy_med = {row["id"]: row["answer"] for row in read_csv(args.easy_med_formatted_csv)}

    output_rows: list[dict[str, str]] = []
    for sample_row in read_csv(args.sample_csv):
        question_id = sample_row["id"]
        if question_id in easy_med:
            response = easy_med[question_id]
        else:
            row = answers.get(question_id, {})
            response = format_rows(row.get("question", ""), row.get("answer", ""))
        output_rows.append({"id": question_id, "response": response})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "response"])
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
