# Data Governance Redaction Policy

## Policy Purpose

This policy defines the redaction rules used by the FahMai Enterprise AI-Safe
Analytics Pipeline. The goal is to keep the friend SQLite pipeline compatible
while reducing exposure of personal, contact, bank-account, and shipment
tracking data.

## Redaction Rules

| Table | Column | Action | Reason |
| --- | --- | --- | --- |
| `DIM_BANK_ACCOUNT` | `account_number` | Replace with `REDACTED_ACCOUNT` | Account numbers are not required for analytics answers. |
| `DIM_CUSTOMER` | `first_name_th`, `last_name_th`, `first_name_en`, `last_name_en` | Replace with `REDACTED_CUSTOMER` | Customer names are personal data. |
| `DIM_CUSTOMER` | `email`, `phone` | Blank | Customer contact fields are not needed for benchmark analytics. |
| `DIM_EMPLOYEE` | `email` | Blank | Employee contact details are not needed for analytics answers. |
| `DIM_EMPLOYEE` | `phone` | Blank if present | Employee contact details are not needed for analytics answers. |
| `FACT_SHIPPING` | `tracking_number` | Replace with `REDACTED_TRACKING` | Tracking numbers are operational identifiers. |

## Fields Intentionally Retained

The following identifiers remain available because benchmark questions and
joins require them:

```text
customer_id
employee_id
txn_id
line_item_id
sku_id
branch_code
vendor_id
refund_id
return_id
bank_txn_id
account_id
```

Employee work identity also remains available:

```text
first_name_en
last_name_en
position_title
position_level
dept_code
canon_role_label
```

Employee names are retained because CEO, approver, and organization questions
need human-readable work identity. Employee contact fields are removed.

## Audit Evidence

Each sanitizer run writes:

```text
data_governance/enterprise_ai_safe_redaction_summary.csv
```

The report includes table name, column name, redaction action, redacted cell
count, and governance notes. Review this file before handing the dataset to
another AI agent or analyst.

## Operating Rule

Use the sanitized CSV tables as the default source for SQLite import. Raw values
should not be restored unless a separate, approved local-only investigation
requires them.
