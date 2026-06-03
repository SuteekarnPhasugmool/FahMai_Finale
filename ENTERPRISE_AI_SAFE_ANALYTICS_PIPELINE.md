# FahMai Enterprise AI-Safe Analytics Pipeline

## Executive Overview

The FahMai Enterprise AI-Safe Analytics Pipeline keeps the existing SQLite
agentic analytics workflow intact while replacing sensitive source values with
AI-safe compatible values.

This repository still uses the friend pipeline as the primary execution path:

```text
CSV tables
  -> SQLite import by agentic_ai/fahmai_sql_agent.py
  -> sql/create_joined_views.sql
  -> intent templates / rules / llm / llm-sql planner
  -> SQL execution
  -> markdown table output
```

The enterprise safety layer changes the data values, not the table structure.
All table names, headers, and row counts are preserved so existing SQLite views
and batch workflows continue to run.

## Enterprise Safety Layer

Run the sanitizer before rebuilding the SQLite database:

```bash
python3 scripts/build_enterprise_ai_safe_tables.py \
  --input-dir fah-mai-the-finale-enterprise-data-agentic-showdown/tables \
  --output-dir fah-mai-the-finale-enterprise-data-agentic-showdown/tables \
  --overwrite
```

The sanitizer writes an audit report to:

```text
data_governance/enterprise_ai_safe_redaction_summary.csv
```

Current redaction summary:

```text
Tables processed: 31
Rows processed: 1051694
Redacted cells: 203796
```

## Compatibility Contract

This pipeline intentionally preserves the friend pipeline contract:

- Same `fah-mai-the-finale-enterprise-data-agentic-showdown/tables/` location.
- Same CSV filenames.
- Same CSV headers.
- Same row counts.
- Same `fahmai_sql_agent.py` command shape.
- Same `run_all_questions.py` batch runner.
- Same SQLite view definitions.
- Same markdown-table output contract in the `answer` column.

Sensitive values are redacted in place so queries keep resolving. For example,
`DIM_BANK_ACCOUNT.account_number` still exists because
`VW_FACT_BANK_TRANSACTION_ENRICHED` selects it, but its values are now
`REDACTED_ACCOUNT`.

## Known Join Behavior

The friend pipeline keeps its existing join logic. One known behavior is
preserved intentionally for compatibility:

```text
FACT_PROMO_REDEMPTION row count: 1583
VW_FACT_PROMO_REDEMPTION_ENRICHED row count: 1626
```

The enriched promo view fans out because `dim_promo_mechanic` has two rows for
campaign `SF-LAUNCH-2568`. This branch does not change that join because the
goal is safety-compatible data, not a join refactor.

## Local SQLite Tests

Rebuild the database and run a smoke query:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --rebuild-db \
  --sql "SELECT COUNT(*) AS n FROM VW_FACT_SALES_ENRICHED"
```

Expected result:

```text
117105
```

Verify the enterprise redaction:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --sql "SELECT account_number FROM DIM_BANK_ACCOUNT LIMIT 3"
```

Expected result:

```text
REDACTED_ACCOUNT
```

Run the sanitizer unit test:

```bash
python3 tests/test_enterprise_ai_safe_tables.py -v
```

## Typhoon ThaiLLM Tests

Set ThaiLLM credentials:

```bash
export THAILLM_API_KEY="your-token"
export THAILLM_MODEL="typhoon-s-thaillm-8b-instruct"
```

Run one benchmark question through `llm-sql`:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-EASY-001 \
  --fallback-to-rules
```

Run a small batch through the current main-branch batch runner:

```bash
python3 agentic_ai/run_all_questions.py \
  --max-questions 3 \
  --rebuild-db \
  --overwrite \
  --fallback-to-rules
```

The batch runner should write `final_answers.csv` without SQLite schema errors.
For committed benchmark artifacts, keep generated answer CSVs under
`artifacts/final_answers/`.

## Latest Evaluation Snapshot

The current main-branch flow ends at SQL markdown tables and uses
intent-based deterministic templates before falling back to ThaiLLM. The latest
rerun artifact is:

```text
artifacts/final_answers/final_answers_dynamic_template_check_v2.csv
```

The strict EASY-to-XHARD ground-truth report is:

```text
artifacts/reports/easy_xhard_accuracy_report_dynamic_template_check_v2.csv
```

Latest strict accuracy:

| Level | Correct | Total | Accuracy |
|---|---:|---:|---:|
| EASY | 25 | 25 | 100.00% |
| MED | 20 | 20 | 100.00% |
| HARD | 1 | 20 | 5.00% |
| XHARD | 0 | 20 | 0.00% |
| Total | 46 | 85 | 54.12% |

HARD/XHARD questions often require non-table evidence such as docs, logs,
reports, chat transcripts, rendered files, and multi-step reconciliation. The
structured SQL pipeline should therefore be treated as the table-answering layer
and paired with retrieval/reconciliation for those harder question families.

## Staging Branch Handoff

This work is intended for the existing `staging` branch:

```bash
git fetch origin
git checkout staging
git pull --ff-only origin staging
python3 tests/test_enterprise_ai_safe_tables.py -v
python3 agentic_ai/fahmai_sql_agent.py --rebuild-db --sql "SELECT COUNT(*) AS n FROM VW_FACT_SALES_ENRICHED"
git push origin staging
```
