# FahMai Agentic SQL Pipeline

This repository contains the runnable pipeline for answering FahMai benchmark questions over structured FACT/DIM CSV tables.

## Project Context

This work is part of a larger team project: **Enterprise Data Agent**.

The full project goal was to build an agentic AI pipeline for enterprise question answering across structured and unstructured business data. At the system level, the project combines SQL querying, retrieval, and reasoning components so answers can be grounded in enterprise data, traced back to source evidence, and extended across tables, reports, documents, and OCR-based sources.

This repository focuses on **my part of the team project**: the tool-to-SQL agent for structured business tables. My scope was to build the component that selects relevant tables/views, generates and executes SQL queries, validates them against the live schema, and returns structured markdown-table answers. Retrieval over unstructured reports, documents, chat logs, and OCR outputs belongs to the broader Enterprise Data Agent system, but is not the main focus of this cleaned repository.

## What Is Kept In Main

Only files needed to run or understand the pipeline are committed:

- `agentic_ai/fahmai_sql_agent.py`: single-question SQL agent.
- `agentic_ai/run_all_questions.py`: batch runner for `questions.csv`.
- `agentic_ai/format_submission.py`: optional post-processor that converts markdown-table answers into `sample_submission.csv` format.
- `agentic_ai/join_catalog.py`: semantic routing catalog for enriched views.
- `sql/create_joined_views.sql`: approved FACT-to-DIM joined views.
- `fah-mai-the-finale-enterprise-data-agentic-showdown/tables/`: structured source CSV tables.
- `questions.csv`: benchmark questions.
- `sample_submission.csv`: submission format template.
- `scripts/build_enterprise_ai_safe_tables.py`: optional redaction/data-governance utility.
- `tests/`: lightweight regression checks.

Generated files are intentionally ignored by git: SQLite databases, `artifacts/`, final answer CSVs, submission CSVs, report CSVs, and local ground-truth CSVs.

## Pipeline Flow

1. **Load CSV tables into SQLite**
   - The agent builds `fahmai_agentic.db` from the committed CSV tables when the DB does not exist or when `--rebuild-db` is used.
   - Types are inferred conservatively: booleans become `1/0`, numeric measures become `INTEGER` or `REAL`, blanks become `NULL`, and date columns are stored as ISO text with `DATE` declarations.

2. **Create enriched views**
   - `sql/create_joined_views.sql` creates `VW_FACT_*_ENRICHED` views.
   - Views use explicit join paths from FACT tables to DIM tables.
   - Repeated date joins use role-specific aliases to avoid duplicate date columns.

3. **Plan the query**
   - Deterministic intent templates run first for common benchmark-style questions.
   - If no template matches, the local rule planner selects a view, metric, grouping, filters, and limit.
   - With `--planner llm-sql`, ThaiLLM can generate SQL from the live schema. The model must return JSON with one read-only SQLite `SELECT`.

4. **Validate and execute SQL**
   - SQL is checked for read-only behavior.
   - SQLite validates table and column references with the live schema.
   - Common friendly alias mistakes are repaired.
   - Failed LLM SQL can be repaired by another LLM call when enabled, or fall back to rules.

5. **Return markdown table**
   - The core SQL pipeline returns a markdown table.
   - Batch runs write `id,question,answer`, where `answer` is that markdown table.

6. **Optional submission formatting**
   - `agentic_ai/format_submission.py` can convert markdown-table answers to `id,response`.
   - Formatting is based on returned column shapes and question intent, not ground-truth leakage or fixed answers.

## Quick Start

Rebuild the SQLite database and smoke-test an enriched view:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --rebuild-db \
  --sql "SELECT COUNT(*) AS n FROM VW_FACT_SALES_ENRICHED"
```

Run one question without an LLM:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --question-id L3-Q-EASY-001 \
  --fallback-to-rules
```

Run one question with ThaiLLM:

```bash
export THAILLM_API_KEY="your-token"
export THAILLM_MODEL="typhoon-s-thaillm-8b-instruct"
export THAILLM_API_URL="http://thaillm.or.th/api/v1/chat/completions"

python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-EASY-001
```

Run all questions into a local artifact CSV:

```bash
python3 agentic_ai/run_all_questions.py \
  --rules-only \
  --output artifacts/final_answers/final_answers.csv \
  --overwrite
```

Create a submission-style CSV from a batch output:

```bash
python3 agentic_ai/format_submission.py \
  --answers-csv artifacts/final_answers/final_answers.csv \
  --sample-csv sample_submission.csv \
  --output artifacts/submissions/submission.csv
```

Run tests:

```bash
python3 -m pytest tests
```

## Notes

- API keys must be set in the terminal environment. They are not committed.
- Ground-truth CSVs are evaluation-only local files and are not used by the runtime pipeline.
- The SQL agent is strongest for structured FACT/DIM questions. Questions requiring narrative evidence from docs, logs, chat, or reports need an additional retrieval layer.
- See `README_AGENTIC_AI.md` and `SYSTEM_OVERVIEW_AGENTIC_AI.md` for more detailed engineering notes.
