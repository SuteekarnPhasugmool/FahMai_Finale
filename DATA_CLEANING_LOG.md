# Data Cleaning Log

- Generated at: 2026-06-02T10:04:30
- Scope: `fah-mai-the-finale-enterprise-data-agentic-showdown/tables/*.csv`
- Rule: drop columns where every row is blank/null after trimming whitespace.
- Notes: CSV blank fields are treated as null-equivalent for this cleanup.

## Summary

- Tables changed: 20
- Columns dropped: 27

## Dropped Columns

| Table | Rows | Columns Before | Columns After | Dropped Columns |
|---|---:|---:|---:|---|
| `DIM_DATE` | 731 | 7 | 6 | `holiday_name` |
| `DIM_EMPLOYEE` | 600 | 21 | 16 | `phone`, `section`, `unit`, `termination_date`, `termination_reason` |
| `DIM_POLICY_VERSION` | 12 | 10 | 9 | `policy_doc_filename` |
| `DIM_PRODUCT` | 110 | 13 | 12 | `end_of_life_date` |
| `FACT_BANK_TRANSACTION` | 65334 | 13 | 12 | `effective_date` |
| `FACT_CS_INTERACTION` | 14368 | 14 | 13 | `effective_date` |
| `FACT_INVENTORY_MONTHLY_SNAPSHOT` | 26220 | 9 | 8 | `effective_date` |
| `FACT_INVENTORY_MOVEMENT` | 310827 | 10 | 9 | `effective_date` |
| `FACT_LOYALTY_LEDGER` | 118857 | 11 | 10 | `effective_date` |
| `FACT_PAYROLL` | 14400 | 14 | 13 | `effective_date` |
| `FACT_PROMO_REDEMPTION` | 1583 | 10 | 9 | `effective_date` |
| `FACT_REFUND_PAID` | 7134 | 13 | 10 | `effective_date`, `cs_interaction_id`, `cosig_employee_id` |
| `FACT_RETURN` | 7144 | 14 | 13 | `effective_date` |
| `FACT_SALES` | 117105 | 24 | 22 | `effective_date`, `retry_idempotency_marker` |
| `FACT_SALES_LINE_ITEM` | 309129 | 13 | 12 | `effective_date` |
| `FACT_SHIPPING` | 23182 | 11 | 10 | `effective_date` |
| `FACT_VENDOR_PAYMENT` | 809 | 15 | 14 | `effective_date` |
| `FACT_WARRANTY_CLAIM` | 3973 | 12 | 11 | `effective_date` |
| `dim_care_plus_sku_tier` | 2 | 7 | 6 | `sku_category` |
| `dim_promo_mechanic` | 8 | 7 | 6 | `min_basket_thb` |

## Unchanged Tables

- `DIM_BANK_ACCOUNT`
- `DIM_BRANCH`
- `DIM_CUSTOMER`
- `DIM_DEPARTMENT`
- `DIM_POSITION_LEVEL`
- `DIM_PROMO_CAMPAIGN`
- `DIM_VENDOR`
- `DIM_VENDOR_CONTRACT_VERSION`
- `T2_DOC_INVENTORY`
- `dim_product_recall_history`
- `dim_signing_authority_ladder`
