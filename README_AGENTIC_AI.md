# FahMai Agentic SQL AI

This adds a small prompt-to-SQL agent over FahMai's structured FACT/DIM data.

## What Was Added

- `sql/create_joined_views.sql`
  - Creates enriched views for every FACT table.
  - Uses explicit, approved joins to DIM tables.
  - Uses role-playing date aliases instead of `SELECT *` across repeated `DIM_DATE` joins.

- `agentic_ai/join_catalog.py`
  - Semantic catalog of enriched views, metrics, dimensions, and routing keywords.

- `agentic_ai/fahmai_sql_agent.py`
  - CLI agent that accepts Thai or English questions.
  - Builds `fahmai_agentic.db` from CSV files if needed, with typed SQLite columns inferred from names and values.
  - Creates/refreshes enriched views.
  - Routes the prompt to a relevant view using either deterministic rules or ThaiLLM.
  - Generates read-only aggregate SQL.
  - Prints the SQL and query result.

## Run

From the project root:

```bash
python3 agentic_ai/fahmai_sql_agent.py "ยอดขายตามสาขาปี 2025" --limit 5
```

Example:

```bash
python3 agentic_ai/fahmai_sql_agent.py "payroll net pay by department 2024" --limit 10
python3 agentic_ai/fahmai_sql_agent.py "แต้ม loyalty ตาม tier ปี 2568" --limit 10
python3 agentic_ai/fahmai_sql_agent.py "inventory movement by branch and category" --limit 10
```

Use ThaiLLM as the planner:

```bash
export THAILLM_API_KEY="your-token"

python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm \
  "ยอดขายปี 2025 แยกตามสาขา top 5" \
  --limit 5
```

Use the broader LLM-SQL planner for the real benchmark questions in `questions.csv`:

```bash
export THAILLM_API_KEY="your-token"

python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-EASY-001
```

Example table questions:

```bash
python3 agentic_ai/fahmai_sql_agent.py --planner llm-sql --question-id L3-Q-EASY-003
python3 agentic_ai/fahmai_sql_agent.py --planner llm-sql --question-id L3-Q-MED-001
```

Ask for a post-processed final answer instead of only a result table:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-MED-019 \
  --limit 50 \
  --answer-format both
```

For `L3-Q-MED-019`, the SQL result is a month-by-month table and the final answer is formatted as the requested 12-value tuple.

Use fallback if the LLM API is unavailable:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm \
  --fallback-to-rules \
  "ยอดขายปี 2025 แยกตามสาขา top 5" \
  --limit 5
```

The default LLM settings match the provided endpoint:

```text
THAILLM_API_URL=http://thaillm.or.th/api/v1/chat/completions
THAILLM_MODEL=typhoon-s-thaillm-8b-instruct
```

Run direct SQL safely:

```bash
python3 agentic_ai/fahmai_sql_agent.py --sql \
  "SELECT branch_name_en, SUM(CAST(net_total_thb AS REAL)) AS revenue FROM VW_FACT_SALES_ENRICHED GROUP BY branch_name_en ORDER BY revenue DESC LIMIT 10"
```

Rebuild the generated DB from CSV:

```bash
python3 agentic_ai/fahmai_sql_agent.py --rebuild-db "ยอดขายตามสาขาปี 2025"
```

## Enriched Views

| View | Main Join Coverage |
|---|---|
| `VW_FACT_SALES_ENRICHED` | sales + branch + customer + employee + department + promo + settlement bank transaction + dates |
| `VW_FACT_SALES_LINE_ITEM_ENRICHED` | line item + product + product department + vendor + parent sales + branch + customer + dates |
| `VW_FACT_INVENTORY_MOVEMENT_ENRICHED` | inventory movement + product + product department + vendor + branch + dates |
| `VW_FACT_INVENTORY_MONTHLY_SNAPSHOT_ENRICHED` | inventory snapshot + product + product department + vendor + branch + month-end date |
| `VW_FACT_LOYALTY_LEDGER_ENRICHED` | loyalty ledger + customer + account manager employee + dates |
| `VW_FACT_PAYROLL_ENRICHED` | payroll + employee + employee branch + department + position level + bank transaction + pay-period dates |
| `VW_FACT_PROMO_REDEMPTION_ENRICHED` | promo redemption + customer + campaign + promo mechanic + dates |
| `VW_FACT_RETURN_ENRICHED` | return + product + vendor + branch + customer + approver employee + dates |
| `VW_FACT_REFUND_PAID_ENRICHED` | refund + customer + approver + co-signer + return + bank transaction + dates |
| `VW_FACT_BANK_TRANSACTION_ENRICHED` | bank transaction + bank account + associated branch + dates |
| `VW_FACT_VENDOR_PAYMENT_ENRICHED` | vendor payment + vendor + contract version + signing employees + bank transaction + dates |
| `VW_FACT_SHIPPING_ENRICHED` | shipping + vendor + origin branch + parent sale + customer + dates |
| `VW_FACT_WARRANTY_CLAIM_ENRICHED` | warranty claim + customer + product + vendor + latest recall status + original sale + dates |
| `VW_FACT_CS_INTERACTION_ENRICHED` | CS interaction + customer + employee + employee department + branch + related refund/warranty + dates |

## Notes

- The original `fahmai_finale.db` was locked during development, so the agent defaults to a generated `fahmai_agentic.db` built from CSV files.
- The generated DB imports booleans such as `is_partner_brand` as `BOOLEAN` with `1/0` values, numeric measures as `INTEGER` or `REAL`, blank fields as `NULL`, and date columns as `DATE` declarations with ISO text storage, which is SQLite's normal behavior.
- Year filters use the Gregorian year from `business_event_date` or `pay_period_end`, because `DIM_DATE.fiscal_year` is Buddhist Era (`2567`, `2568`).
- The agent intentionally preserves source FACT rows with `LEFT JOIN`.
- Versioned/history dimensions are joined only where the row path is clear. For `dim_product_recall_history`, the warranty view uses the latest recall row per SKU to avoid fan-out.
- In `--planner llm` mode, the LLM does not write raw SQL. It returns structured JSON with `view_name`, `metric`, `group_by`, `year`, `branch_codes`, and `channel`; Python validates those fields and generates the final SQL.
- In `--planner llm-sql` mode, the LLM writes one read-only SQLite `SELECT` from the full schema. Python validates that it is read-only, applies a small alias repair layer for common friendly names, and retries with the LLM if SQLite reports a column/syntax error.
- `--answer-format table` keeps the raw table output. `--answer-format final` returns only the post-processed final answer. `--answer-format both` prints both the table and the final answer. Final-answer synthesis uses the question, SQL, and rows only; some exact benchmark formats such as 12-month tuples are handled deterministically.
- `questions.csv` contains some questions that require narrative files, logs, chat transcripts, or prompt-injection resistance. The SQL agent is best for DIM/FACT table questions; document/log/chat questions need a retrieval layer over `docs/`, `logs/`, and `reports/`.
