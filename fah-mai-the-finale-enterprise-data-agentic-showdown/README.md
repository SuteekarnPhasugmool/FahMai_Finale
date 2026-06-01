# FahMai Public Data Bundle

This bundle contains the Day-1 analyst view of FahMai's operations data — a multi-channel electronics retailer in Thailand.

The data covers the 2024-01-01 → 2025-12-31 fiscal window. Release as-of date: 2026-01-15.

## Contents

| Folder | Count | Description |
|---|---:|---|
| `tables/` | 31 | DIM_* (dimension) and FACT_* (fact) CSVs |
| `docs/memo/` | 16 | Internal policy memos |
| `docs/minutes/` | 26 | Meeting minutes |
| `docs/email/` | 25 | All-staff emails |
| `docs/chat_line_oa/` | 37,441 | Customer LINE OA chat transcripts (markdown) |
| `docs/chat_line_works/` | 15,802 | Internal LINE Works thread transcripts (markdown) |
| `docs/l1_kb/` | 0 | L1 KB documents (product specs, policies) |
| `renders/*` | 6,128 | Bank statements, receipts, invoices, warranty forms, lease + training PDFs, promo banners |
| `logs/` | 7,935 | POS line-item + web order + WMS + helpdesk + PayWise fee logs |
| `reports/` | 32 | Monthly OPS + quarterly FIN cadence reports |

## Notes on the data

- Most narrative is in **Thai**; some is in English; a small fraction is mixed. Plan for both.
- The fiscal window crosses a mid-2025 **schema-version cutover** in `FACT_SALES`. Date-aware joins should respect it.
- The corpus contains **real-world data-quality artifacts** — duplicate invoices, phantom redemptions, retry markers, manual corrections. These are not bugs in the data; they reflect how the underlying business actually runs.
- The corpus includes both **structured tables and unstructured narrative** that sometimes disagree (e.g. a memo vs. a database table). When sources conflict, the database table is the authoritative source unless a more recent memo / policy version supersedes it.
- Renders are organized as `renders/<type>/YYYY-MM/<file>.png|pdf`. The structured tables reference render filenames via standard ID columns where applicable.

Good luck.
