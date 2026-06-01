"""Semantic join catalog for the FahMai structured data bundle.

This file is intentionally explicit. The agent should plan from approved join
paths instead of guessing from similarly named columns.
"""

from __future__ import annotations

from dataclasses import dataclass


COMMON_DATE_ROLES = {
    "business_event_date": "event",
    "posting_date": "posting",
}


@dataclass(frozen=True)
class ViewSpec:
    name: str
    fact_table: str
    description: str
    metrics: tuple[str, ...]
    dimensions: tuple[str, ...]
    keywords: tuple[str, ...]


VIEW_SPECS: dict[str, ViewSpec] = {
    "VW_FACT_SALES_ENRICHED": ViewSpec(
        name="VW_FACT_SALES_ENRICHED",
        fact_table="FACT_SALES",
        description="Sales orders enriched with branch, customer, employee, promo, settlement bank transaction and role-playing dates.",
        metrics=("basket_total_thb", "discount_total_thb", "net_total_thb", "shipping_charge_thb"),
        dimensions=(
            "branch_code",
            "branch_name_en",
            "customer_id",
            "customer_type",
            "customer_region",
            "employee_id",
            "employee_position_level",
            "department_name_en",
            "channel",
            "promo_campaign_id",
            "payment_method",
            "payment_status",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("sales", "sale", "revenue", "ยอดขาย", "ขาย", "รายได้", "basket", "order", "txn"),
    ),
    "VW_FACT_SALES_LINE_ITEM_ENRICHED": ViewSpec(
        name="VW_FACT_SALES_LINE_ITEM_ENRICHED",
        fact_table="FACT_SALES_LINE_ITEM",
        description="Sales line items enriched with product, vendor, product department, parent sale, customer, branch and dates.",
        metrics=("quantity", "unit_price_thb", "line_discount_thb", "line_total_thb"),
        dimensions=(
            "txn_id",
            "sku_id",
            "product_category",
            "product_subcategory",
            "product_brand_family",
            "vendor_name_en",
            "branch_code",
            "customer_type",
            "channel",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("line item", "sku", "product", "สินค้า", "ยอดขายสินค้า", "quantity", "ชิ้น", "category"),
    ),
    "VW_FACT_INVENTORY_MOVEMENT_ENRICHED": ViewSpec(
        name="VW_FACT_INVENTORY_MOVEMENT_ENRICHED",
        fact_table="FACT_INVENTORY_MOVEMENT",
        description="Inventory movements enriched with product, vendor, product department, branch and dates.",
        metrics=("quantity",),
        dimensions=(
            "sku_id",
            "product_category",
            "product_brand_family",
            "vendor_name_en",
            "branch_code",
            "branch_name_en",
            "movement_type",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("inventory movement", "movement", "stock movement", "inventory", "สต๊อก", "stock", "movement_type"),
    ),
    "VW_FACT_INVENTORY_MONTHLY_SNAPSHOT_ENRICHED": ViewSpec(
        name="VW_FACT_INVENTORY_MONTHLY_SNAPSHOT_ENRICHED",
        fact_table="FACT_INVENTORY_MONTHLY_SNAPSHOT",
        description="Monthly inventory snapshots enriched with product, vendor, branch, event date and month-end date.",
        metrics=("closing_units",),
        dimensions=(
            "month_end_date",
            "sku_id",
            "product_category",
            "product_brand_family",
            "branch_code",
            "branch_name_en",
            "month_end_fiscal_year",
            "month_end_fiscal_quarter",
        ),
        keywords=("snapshot", "closing stock", "closing_units", "สินค้าคงเหลือ", "คงเหลือ", "month end"),
    ),
    "VW_FACT_LOYALTY_LEDGER_ENRICHED": ViewSpec(
        name="VW_FACT_LOYALTY_LEDGER_ENRICHED",
        fact_table="FACT_LOYALTY_LEDGER",
        description="Loyalty point ledger enriched with customer, account manager employee and dates.",
        metrics=("points_delta", "resulting_balance_points"),
        dimensions=(
            "customer_id",
            "customer_type",
            "customer_region",
            "customer_loyalty_tier",
            "account_manager_employee_id",
            "event_type",
            "resulting_tier",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("loyalty", "ledger", "points", "point", "แต้ม", "คะแนน", "member", "สมาชิก"),
    ),
    "VW_FACT_PAYROLL_ENRICHED": ViewSpec(
        name="VW_FACT_PAYROLL_ENRICHED",
        fact_table="FACT_PAYROLL",
        description="Payroll enriched with employee, employee branch, department, position level, bank transaction and pay period dates.",
        metrics=("gross_pay_thb", "tax_deduction_thb", "social_security_thb", "net_pay_thb"),
        dimensions=(
            "employee_id",
            "employee_branch_code",
            "employee_branch_name_en",
            "employee_dept_code",
            "department_name_en",
            "employee_position_level",
            "pay_period_start",
            "pay_period_end",
            "period_end_fiscal_year",
            "period_end_fiscal_quarter",
        ),
        keywords=("payroll", "salary", "net pay", "gross pay", "เงินเดือน", "ค่าจ้าง", "พนักงาน"),
    ),
    "VW_FACT_PROMO_REDEMPTION_ENRICHED": ViewSpec(
        name="VW_FACT_PROMO_REDEMPTION_ENRICHED",
        fact_table="FACT_PROMO_REDEMPTION",
        description="Promo redemptions enriched with customer, campaign, promo mechanic and dates.",
        metrics=("discount_applied_thb",),
        dimensions=(
            "campaign_id",
            "campaign_description_en",
            "discount_type",
            "customer_type",
            "customer_region",
            "channel",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("promo", "promotion", "campaign", "redemption", "ส่วนลด", "โปร", "แคมเปญ"),
    ),
    "VW_FACT_RETURN_ENRICHED": ViewSpec(
        name="VW_FACT_RETURN_ENRICHED",
        fact_table="FACT_RETURN",
        description="Returns enriched with product, branch, customer, approver employee and dates.",
        metrics=("return_amount_thb", "days_since_purchase"),
        dimensions=(
            "sku_id",
            "product_category",
            "branch_code",
            "branch_name_en",
            "customer_type",
            "return_reason",
            "approved_by_employee_id",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("return", "refund return", "คืนสินค้า", "returns", "return_reason"),
    ),
    "VW_FACT_REFUND_PAID_ENRICHED": ViewSpec(
        name="VW_FACT_REFUND_PAID_ENRICHED",
        fact_table="FACT_REFUND_PAID",
        description="Paid refunds enriched with customer, approver, co-signer, bank transaction, return and dates.",
        metrics=("refund_amount_thb",),
        dimensions=(
            "customer_id",
            "customer_type",
            "customer_region",
            "approver_employee_id",
            "cosig_employee_id",
            "bank_txn_id",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("refund", "refund paid", "คืนเงิน", "จ่ายคืน"),
    ),
    "VW_FACT_BANK_TRANSACTION_ENRICHED": ViewSpec(
        name="VW_FACT_BANK_TRANSACTION_ENRICHED",
        fact_table="FACT_BANK_TRANSACTION",
        description="Bank transactions enriched with bank account, associated branch and dates. Polymorphic related_entity fields are left as raw columns.",
        metrics=("amount_thb", "balance_after_thb"),
        dimensions=(
            "account_id",
            "bank",
            "account_role",
            "associated_branch_code",
            "associated_branch_name_en",
            "transaction_type",
            "related_entity_table",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("bank", "transaction", "cash", "payment", "บัญชี", "ธนาคาร", "เงินเข้า", "เงินออก"),
    ),
    "VW_FACT_VENDOR_PAYMENT_ENRICHED": ViewSpec(
        name="VW_FACT_VENDOR_PAYMENT_ENRICHED",
        fact_table="FACT_VENDOR_PAYMENT",
        description="Vendor payments enriched with vendor, vendor contract version, signing employees, bank transaction and dates.",
        metrics=("paid_amount_thb",),
        dimensions=(
            "vendor_id",
            "vendor_name_en",
            "vendor_category",
            "vendor_contract_version_id",
            "signing_employee_id",
            "cosig_employee_id",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("vendor payment", "vendor", "supplier", "paid_amount", "จ่าย vendor", "ผู้ขาย", "ซัพพลายเออร์"),
    ),
    "VW_FACT_SHIPPING_ENRICHED": ViewSpec(
        name="VW_FACT_SHIPPING_ENRICHED",
        fact_table="FACT_SHIPPING",
        description="Shipping records enriched with vendor, origin branch, parent sale customer and dates.",
        metrics=(),
        dimensions=(
            "vendor_id",
            "vendor_name_en",
            "origin_branch_code",
            "origin_branch_name_en",
            "destination_province",
            "confirmation_status",
            "channel",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("shipping", "delivery", "ship", "ส่งของ", "ขนส่ง", "tracking"),
    ),
    "VW_FACT_WARRANTY_CLAIM_ENRICHED": ViewSpec(
        name="VW_FACT_WARRANTY_CLAIM_ENRICHED",
        fact_table="FACT_WARRANTY_CLAIM",
        description="Warranty claims enriched with customer, product, vendor, recall status from latest recall history and dates.",
        metrics=("claim_amount_thb",),
        dimensions=(
            "customer_id",
            "customer_type",
            "sku_id",
            "product_category",
            "vendor_name_en",
            "claim_reason",
            "routing_destination",
            "resolution_type",
            "latest_recall_status",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("warranty", "claim", "เคลม", "ประกัน", "claim_amount", "recall"),
    ),
    "VW_FACT_CS_INTERACTION_ENRICHED": ViewSpec(
        name="VW_FACT_CS_INTERACTION_ENRICHED",
        fact_table="FACT_CS_INTERACTION",
        description="Customer-service interactions enriched with customer, employee, employee department, branch and dates.",
        metrics=(),
        dimensions=(
            "customer_id",
            "customer_type",
            "customer_region",
            "employee_id",
            "department_name_en",
            "branch_code",
            "branch_name_en",
            "channel",
            "interaction_type",
            "resolution_type",
            "event_fiscal_year",
            "event_fiscal_quarter",
        ),
        keywords=("cs", "customer service", "interaction", "ticket", "support", "บริการลูกค้า", "แชท"),
    ),
}


def catalog_prompt() -> str:
    lines = ["Approved enriched views and usable metrics/dimensions:"]
    for spec in VIEW_SPECS.values():
        lines.append(f"- {spec.name}: {spec.description}")
        lines.append(f"  metrics: {', '.join(spec.metrics) or '(count rows only)'}")
        lines.append(f"  dimensions: {', '.join(spec.dimensions)}")
    return "\n".join(lines)

