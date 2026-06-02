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
  - Routes the prompt through intent-based deterministic SQL templates first, then falls back to rules or ThaiLLM.
  - Generates read-only aggregate SQL.
  - Validates generated SQL against the live SQLite schema before execution.
  - Prints the SQL and query result.

- `agentic_ai/run_all_questions.py`
  - Batch runner for `questions.csv`.
  - Writes `id,question,answer` rows to a CSV such as `final_answers.csv`, where `answer` contains the markdown table result.
  - Supports resume by skipping question IDs already present in the output file.
  - Adds per-question and per-query timeouts for long benchmark runs.

- `scripts/build_enterprise_ai_safe_tables.py`
  - Enterprise AI-safe redaction layer for sensitive CSV values.
  - Preserves table names, headers, and row counts so the SQLite pipeline remains compatible.
  - Writes an audit report to `data_governance/enterprise_ai_safe_redaction_summary.csv`.

## Run

From the project root:

If you need to refresh the enterprise AI-safe data layer, run the redaction step before rebuilding SQLite:

```bash
python3 scripts/build_enterprise_ai_safe_tables.py \
  --input-dir fah-mai-the-finale-enterprise-data-agentic-showdown/tables \
  --output-dir fah-mai-the-finale-enterprise-data-agentic-showdown/tables \
  --overwrite
```

Then rebuild the SQLite database so it reflects the latest CSV tables:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --rebuild-db \
  --sql "SELECT COUNT(*) AS n FROM VW_FACT_SALES_ENRICHED"
```

Run a question:

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

The pipeline now ends at the markdown result table. There is no final-answer formatter stage:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-MED-019 \
  --limit 50
```

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

Run every question in `questions.csv` and write markdown table results to a new CSV without overwriting the committed `final_answers.csv`:

```bash
python3 agentic_ai/run_all_questions.py \
  --output final_answers_rerun.csv \
  --fallback-to-rules \
  --question-timeout 120 \
  --query-timeout 30
```

Latest benchmark-style rerun:

```bash
export THAILLM_API_KEY="your-token"

python3 agentic_ai/run_all_questions.py \
  --output final_answers_new_run.csv \
  --overwrite \
  --fallback-to-rules \
  --question-timeout 120 \
  --query-timeout 30
```

The latest strict check against `fahmai_easy_xhard_gt.csv` is saved in
`easy_xhard_accuracy_report_new_run.csv`:

| Level | Correct | Total | Accuracy |
|---|---:|---:|---:|
| EASY | 25 | 25 | 100.00% |
| MED | 20 | 20 | 100.00% |
| HARD | 1 | 20 | 5.00% |
| XHARD | 0 | 20 | 0.00% |
| Total | 46 | 85 | 54.12% |

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
| `VW_FACT_REFUND_PAID_ENRICHED` | refund + customer + approver + return + bank transaction + dates |
| `VW_FACT_BANK_TRANSACTION_ENRICHED` | bank transaction + bank account + associated branch + dates |
| `VW_FACT_VENDOR_PAYMENT_ENRICHED` | vendor payment + vendor + contract version + signing employees + bank transaction + dates |
| `VW_FACT_SHIPPING_ENRICHED` | shipping + vendor + origin branch + parent sale + customer + dates |
| `VW_FACT_WARRANTY_CLAIM_ENRICHED` | warranty claim + customer + product + vendor + latest recall status + original sale + dates |
| `VW_FACT_CS_INTERACTION_ENRICHED` | CS interaction + customer + employee + employee department + branch + related refund/warranty + dates |

## Notes

- The original `fahmai_finale.db` was locked during development, so the agent defaults to a generated `fahmai_agentic.db` built from CSV files.
- The generated DB imports booleans such as `is_partner_brand` as `BOOLEAN` with `1/0` values, numeric measures as `INTEGER` or `REAL`, blank fields as `NULL`, and date columns as `DATE` declarations with ISO text storage, which is SQLite's normal behavior.
- Source CSV tables are cleaned by dropping columns that were blank/null in every row. See `DATA_CLEANING_LOG.md` for the exact dropped columns.
- The current data layer also includes enterprise AI-safe redaction. See `ENTERPRISE_AI_SAFE_ANALYTICS_PIPELINE.md` and `DATA_GOVERNANCE_REDACTION_POLICY.md` for the redaction flow and policy.
- Year filters use the Gregorian year from `business_event_date` or `pay_period_end`, because `DIM_DATE.fiscal_year` is Buddhist Era (`2567`, `2568`).
- The agent intentionally preserves source FACT rows with `LEFT JOIN`.
- Versioned/history dimensions are joined only where the row path is clear. For `dim_product_recall_history`, the warranty view uses the latest recall row per SKU to avoid fan-out.
- In `--planner llm` mode, the LLM does not write raw SQL. It returns structured JSON with `view_name`, `metric`, `group_by`, `year`, `branch_codes`, and `channel`; Python validates those fields and generates the final SQL.
- In `--planner llm-sql` mode, the LLM writes one read-only SQLite `SELECT` from the full schema. Python validates that it is read-only, validates table/column resolution with SQLite `EXPLAIN QUERY PLAN`, applies a small alias repair layer for common friendly names, and retries with the LLM if SQLite reports a column/syntax error.
- Intent-based deterministic templates are checked before LLM calls in both the single-question CLI and the batch runner. They are keyed by question wording/intent, not by fixed `question_id`, to reduce brittle benchmark-specific behavior.
- Long-running queries can be interrupted by the batch runner with `--query-timeout`.
- The pipeline intentionally stops at the markdown table returned from SQL. It does not run a final-answer formatter LLM stage.
- `questions.csv` contains some questions that require narrative files, logs, chat transcripts, or prompt-injection resistance. The SQL agent is best for DIM/FACT table questions; the latest EASY/MED results are strong, while HARD/XHARD needs a retrieval/reconciliation layer over `docs/`, `logs/`, `reports/`, chat artifacts, and rendered evidence.
