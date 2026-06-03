#!/usr/bin/env python3
"""Run every benchmark question through the FahMai SQL agent and save markdown tables."""

from __future__ import annotations

import argparse
import csv
import os
import signal
import sqlite3
import sys
from pathlib import Path
from contextlib import contextmanager

from fahmai_sql_agent import (
    DEFAULT_CSV_DIR,
    DEFAULT_DB,
    DEFAULT_QUESTIONS_CSV,
    DEFAULT_VIEW_SQL,
    bootstrap_database,
    connect,
    deterministic_sql_for_question,
    ensure_views,
    execute_sql,
    llm_generate_sql,
    markdown_table,
    plan_query,
    repair_known_empty_result_sql,
    repair_known_sql_aliases,
    repair_sql_with_llm,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "final_answers.csv"
DEFAULT_API_URL = "http://thaillm.or.th/api/v1/chat/completions"
DEFAULT_MODEL = "typhoon-s-thaillm-8b-instruct"


@contextmanager
def question_timeout(seconds: int):
    def raise_timeout(_signum, _frame):
        raise TimeoutError(f"Question exceeded {seconds} seconds")

    previous_handler = signal.signal(signal.SIGALRM, raise_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


def read_questions(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_completed_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row["id"] for row in csv.DictReader(handle) if row.get("id")}


def append_answer(path: Path, question_id: str, question: str, answer: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    should_write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "question", "answer"])
        if should_write_header:
            writer.writeheader()
        writer.writerow({"id": question_id, "question": question, "answer": answer})


def generate_rows(
    *,
    conn: sqlite3.Connection,
    question: str,
    api_url: str,
    api_key: str,
    model: str,
    fallback_to_rules: bool,
    rules_only: bool,
    limit: int,
    query_timeout: int,
) -> tuple[str, list[sqlite3.Row]]:
    deterministic = deterministic_sql_for_question(question)
    if deterministic:
        sql, _ = deterministic
        return sql, execute_sql(conn, sql, query_timeout=query_timeout)

    if rules_only:
        _, sql = plan_query(question, conn, limit)
        return sql, execute_sql(conn, sql, query_timeout=query_timeout)

    try:
        sql, _ = llm_generate_sql(question, conn, api_url=api_url, api_key=api_key, model=model)
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                sql = repair_known_sql_aliases(sql)
                rows = execute_sql(conn, sql, query_timeout=query_timeout)
                if not rows:
                    repaired_empty = repair_known_empty_result_sql(sql)
                    if repaired_empty:
                        retry_rows = execute_sql(conn, repaired_empty, query_timeout=query_timeout)
                        if retry_rows:
                            sql = repaired_empty
                            rows = retry_rows
                return sql, rows
            except sqlite3.Error as exc:
                last_error = exc
                if attempt == 2:
                    raise
                sql, _ = repair_sql_with_llm(
                    question=question,
                    bad_sql=sql,
                    error=str(exc),
                    conn=conn,
                    api_url=api_url,
                    api_key=api_key,
                    model=model,
                )
        raise sqlite3.Error(last_error or "SQL execution failed")
    except Exception:
        if not fallback_to_rules:
            raise
        _, sql = plan_query(question, conn, limit)
        return sql, execute_sql(conn, sql, query_timeout=query_timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-run FahMai questions and write id,question,answer CSV.")
    parser.add_argument("--questions-csv", type=Path, default=DEFAULT_QUESTIONS_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    parser.add_argument("--view-sql", type=Path, default=DEFAULT_VIEW_SQL)
    parser.add_argument("--llm-api-url", default=os.environ.get("THAILLM_API_URL", DEFAULT_API_URL))
    parser.add_argument("--llm-api-key", default=os.environ.get("THAILLM_API_KEY"))
    parser.add_argument("--llm-model", default=os.environ.get("THAILLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--question-timeout", type=int, default=180)
    parser.add_argument("--query-timeout", type=int, default=30)
    parser.add_argument("--max-questions", type=int, help="Optional cap for smoke testing.")
    parser.add_argument("--fallback-to-rules", action="store_true")
    parser.add_argument("--rules-only", action="store_true", help="Skip LLM calls and use deterministic templates plus local rule planner.")
    parser.add_argument("--rebuild-db", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.llm_api_key and not args.rules_only:
        parser.error("Please set THAILLM_API_KEY or pass --llm-api-key.")

    if args.overwrite and args.output.exists():
        args.output.unlink()
    if args.rebuild_db and args.db.exists():
        args.db.unlink()

    bootstrap_database(args.db, args.csv_dir)
    questions = read_questions(args.questions_csv)
    if args.max_questions:
        questions = questions[: args.max_questions]

    completed = read_completed_ids(args.output)
    conn = connect(args.db)
    try:
        ensure_views(conn, args.view_sql)
        for index, row in enumerate(questions, start=1):
            question_id = row["id"]
            question = row["question"]
            if question_id in completed:
                print(f"[{index}/{len(questions)}] skip {question_id}", file=sys.stderr, flush=True)
                continue
            print(f"[{index}/{len(questions)}] run {question_id}", file=sys.stderr, flush=True)
            try:
                with question_timeout(args.question_timeout):
                    _, rows = generate_rows(
                        conn=conn,
                        question=question,
                        api_url=args.llm_api_url,
                        api_key=args.llm_api_key,
                        model=args.llm_model,
                        fallback_to_rules=args.fallback_to_rules,
                        rules_only=args.rules_only,
                        limit=args.limit,
                        query_timeout=args.query_timeout,
                    )
                    answer = markdown_table(rows)
            except Exception as exc:
                answer = f"ERROR: {type(exc).__name__}: {exc}"
                print(f"[{index}/{len(questions)}] error {question_id}: {exc}", file=sys.stderr, flush=True)
            append_answer(args.output, question_id, question, answer)
    finally:
        conn.close()
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
