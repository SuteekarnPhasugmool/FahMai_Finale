# FahMai Agentic SQL AI - System Overview

เอกสารนี้สรุปการทำงานของระบบ Agentic SQL AI ที่สร้างไว้สำหรับ dataset ของ FahMai

## เป้าหมายของระบบ

ระบบนี้ทำให้ผู้ใช้สามารถถามคำถามภาษาไทยหรืออังกฤษ แล้วให้ agent ไปดึงข้อมูลจากตาราง `FACT_*` และ `DIM_*` ที่เกี่ยวข้องได้ โดยมีการควบคุม join path, schema, data type และ SQL safety เพื่อลดปัญหา LLM เดา table/column/join ผิด

## ไฟล์หลัก

| ไฟล์ | หน้าที่ |
|---|---|
| `agentic_ai/fahmai_sql_agent.py` | CLI agent หลัก รับ prompt, เรียก LLM, generate/validate/execute SQL |
| `agentic_ai/run_all_questions.py` | batch runner สำหรับรันทุกคำถามใน `questions.csv` แล้วเขียน `id,question,answer` เป็น CSV |
| `agentic_ai/join_catalog.py` | semantic catalog ของ enriched views, metrics, dimensions และ routing keywords |
| `sql/create_joined_views.sql` | SQL สำหรับสร้าง enriched views ที่ join FACT กับ DIM ที่เหมาะสมไว้แล้ว |
| `scripts/build_enterprise_ai_safe_tables.py` | redaction layer สำหรับทำ CSV ให้ enterprise AI-safe โดย preserve schema และ row count |
| `DATA_GOVERNANCE_REDACTION_POLICY.md` | นโยบายและรายการ field ที่ถูก redact |
| `ENTERPRISE_AI_SAFE_ANALYTICS_PIPELINE.md` | เอกสาร flow ของ enterprise AI-safe layer |
| `README_AGENTIC_AI.md` | quick start และตัวอย่างคำสั่งใช้งาน |
| `questions.csv` | ชุดคำถามจริงสำหรับทดสอบ agent |
| `final_answers.csv` | output batch run ล่าสุดในรูปแบบ `id,question,answer` |
| `fahmai_agentic.db` | SQLite database ที่ agent สร้างจาก CSV และใช้ query |

## Data Flow

```text
CSV tables
  -> enterprise AI-safe redaction layer
  -> cleaned/redacted CSV tables
  -> typed SQLite import
  -> create enriched views
  -> receive user prompt / question-id
  -> planner mode
  -> generate SQL
  -> validate SELECT-only SQL + live schema
  -> repair SQL or fallback to rules
  -> execute on SQLite
  -> print SQL + result table
  -> optionally write batch markdown tables to CSV
```

## Enterprise AI-Safe Redaction Layer

branch ที่ merge ล่าสุดเพิ่ม layer สำหรับลด exposure ของ sensitive fields ก่อนนำข้อมูลเข้า AI/SQLite pipeline

รันได้ด้วย:

```bash
python3 scripts/build_enterprise_ai_safe_tables.py \
  --input-dir fah-mai-the-finale-enterprise-data-agentic-showdown/tables \
  --output-dir fah-mai-the-finale-enterprise-data-agentic-showdown/tables \
  --overwrite
```

script นี้ preserve สิ่งสำคัญสำหรับ pipeline เดิม:

```text
table names
CSV filenames
headers
row counts
join keys
```

ตัวอย่าง redaction:

| Table | Column | Result |
|---|---|---|
| `DIM_BANK_ACCOUNT` | `account_number` | `REDACTED_ACCOUNT` |
| `DIM_CUSTOMER` | customer name fields | `REDACTED_CUSTOMER` |
| `DIM_CUSTOMER` | `email`, `phone` | blank |
| `DIM_EMPLOYEE` | `email` | blank |
| `FACT_SHIPPING` | `tracking_number` | `REDACTED_TRACKING` |

audit report อยู่ที่:

```text
data_governance/enterprise_ai_safe_redaction_summary.csv
```

หลัง redaction ต้อง rebuild SQLite database เพื่อให้ `fahmai_agentic.db` sync กับ CSV ล่าสุด:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --rebuild-db \
  --sql "SELECT COUNT(*) AS n FROM VW_FACT_SALES_ENRICHED"
```

## Database Import

ข้อมูลต้นทางอยู่ใน:

```text
fah-mai-the-finale-enterprise-data-agentic-showdown/tables/*.csv
```

เมื่อรันครั้งแรก หรือใช้ `--rebuild-db` ระบบจะสร้าง database:

```text
fahmai_agentic.db
```

importer ตอนนี้ไม่ได้สร้างทุก column เป็น `TEXT` แล้ว แต่ infer type จากชื่อ column และค่าจริงใน CSV

| Data Pattern | SQLite Declaration | Storage |
|---|---|---|
| `true` / `false` | `BOOLEAN` | `1` / `0` |
| จำนวนเต็ม เช่น `quantity`, `rank`, `schema_version` | `INTEGER` | integer |
| เงิน/ราคา/ยอดรวม เช่น `net_total_thb`, `msrp_thb` | `REAL` | real |
| วันที่ format `YYYY-MM-DD` | `DATE` | text ISO date ตาม behavior ปกติของ SQLite |
| ค่าว่างใน CSV | type ตาม column | `NULL` |
| field ที่ควร preserve เป็น text เช่น `phone`, `account_number` | `TEXT` | text |

ตัวอย่าง:

```sql
PRAGMA table_info(DIM_VENDOR);
```

จะเห็น:

```text
is_partner_brand       BOOLEAN
is_component_supplier  BOOLEAN
start_date             DATE
end_date               DATE
```

และค่า boolean ถูกแปลงเป็น:

```text
true  -> 1
false -> 0
```

## Date Handling ใน SQLite

SQLite ไม่มี native date storage แบบ PostgreSQL/MySQL แต่ถ้าเก็บวันที่เป็น text format:

```text
YYYY-MM-DD
```

จะสามารถ compare แบบ string ได้ถูกต้อง เช่น:

```sql
WHERE business_event_date BETWEEN '2025-01-01' AND '2025-12-31'
```

หรือใช้ function:

```sql
WHERE date(business_event_date) <= date('2025-06-01')
```

หลัง cleanup แล้ว column ที่ว่างทั้งคอลัมน์จะถูกลบออกจาก CSV ต้นทาง เช่น `DIM_EMPLOYEE.termination_date` และ `FACT_* .effective_date` หลายตาราง ดังนั้นควรดู schema ปัจจุบันจาก `PRAGMA table_info(...)` หรือ schema prompt ก่อนเขียน SQL

## Enriched Views

ระบบสร้าง view ที่ join FACT กับ DIM ที่เหมาะสมไว้แล้ว เพื่อลดการให้ LLM เดา join เอง

| View | Main Join Coverage |
|---|---|
| `VW_FACT_SALES_ENRICHED` | sales + branch + customer + employee + department + promo + settlement bank transaction + dates |
| `VW_FACT_SALES_LINE_ITEM_ENRICHED` | line item + product + product department + vendor + parent sales + branch + customer + dates |
| `VW_FACT_INVENTORY_MOVEMENT_ENRICHED` | inventory movement + product + product department + vendor + branch + dates |
| `VW_FACT_INVENTORY_MONTHLY_SNAPSHOT_ENRICHED` | inventory snapshot + product + vendor + branch + month-end date |
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

## Planner Modes

Agent รองรับ 3 modes

### 1. `rules`

เป็น deterministic planner ไม่เรียก LLM

```text
prompt
  -> keyword matching
  -> choose enriched view
  -> choose metric / group_by / year filter
  -> generate SQL
```

เหมาะกับคำถาม aggregate ทั่วไป เช่น:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner rules \
  "ยอดขายตามสาขาปี 2025" \
  --limit 5
```

### 2. `llm`

ใช้ ThaiLLM เป็น structured planner แต่ไม่ให้ LLM เขียน SQL เอง

```text
prompt
  -> ThaiLLM returns JSON
  -> Python validates view_name / metric / group_by / filters
  -> Python generates SQL
```

เหมาะกับคำถาม business aggregate ที่ยังอยู่ในกรอบ enriched views

ตัวอย่าง:

```bash
export THAILLM_API_KEY="your-token"

python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm \
  "ยอดขายปี 2025 แยกตามสาขา top 5" \
  --limit 5
```

### 3. `llm-sql`

ใช้ ThaiLLM generate SQL โดยตรงจาก full schema แต่ระบบยัง validate ว่าเป็น read-only `SELECT`

```text
prompt / question-id
  -> ThaiLLM sees full schema
  -> ThaiLLM returns JSON with SQL
  -> Python validates SELECT-only
  -> Python repairs common alias mistakes
  -> execute SQL
```

เหมาะกับคำถามจริงจาก `questions.csv` ที่หลากหลายกว่า เช่น lookup, policy table, percentage, join หลาย table

ตัวอย่าง:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-EASY-001
```

หรือถามเอง:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  "ในปี 2025 สาขาไหนมียอดขาย net_total_thb สูงสุด 5 อันดับแรก"
```

## LLM Integration

ระบบเรียก ThaiLLM ผ่าน endpoint:

```text
http://thaillm.or.th/api/v1/chat/completions
```

default model:

```text
typhoon-s-thaillm-8b-instruct
```

ตั้งค่า key:

```bash
export THAILLM_API_KEY="your-token"
```

Python client ต้องส่ง header ที่ gateway ยอมรับ:

```text
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>
User-Agent: curl/8.0.0
```

เหตุผลที่ใส่ `User-Agent: curl/8.0.0` เพราะตอนแรก Python `urllib` โดน gateway block ด้วย `403 error code: 1010` แต่ `curl` ใช้งานได้

## SQL Safety

ระบบ validate SQL ก่อน execute

อนุญาตเฉพาะ:

```sql
SELECT ...
```

block operation เสี่ยง เช่น:

```text
INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
ATTACH
DETACH
PRAGMA
```

นอกจากนี้ระบบใช้ SQLite schema preflight:

```text
EXPLAIN QUERY PLAN <generated SQL>
```

เพื่อให้ SQLite resolve table/column ก่อน execute จริง ถ้า LLM สร้าง column ที่ไม่มีอยู่ เช่น `employment_status_at_period_end` ระบบจะจับ error ก่อน แล้วใน `llm-sql` mode จะส่ง error กลับไปให้ LLM repair query ใหม่

สำหรับ batch runner มี query timeout เพื่อกัน query หนักค้าง:

```bash
--query-timeout 30
```

## SQL Repair Layer

ใน `llm-sql` mode บางครั้ง LLM ใช้ชื่อ friendly alias ที่ไม่มีจริงบน base table เช่น:

```text
vendor_name_en
```

แต่ใน `DIM_VENDOR` ชื่อ column จริงคือ:

```text
name_en
```

ระบบมี repair layer สำหรับเคสพบบ่อย เช่น:

| LLM ใช้ | แก้เป็น |
|---|---|
| `vendor_name_en` | `DIM_VENDOR.name_en` |
| `vendor_name_th` | `DIM_VENDOR.name_th` |
| `campaign_description_en` | `DIM_PROMO_CAMPAIGN.description_en` |
| `branch_name_en` | `DIM_BRANCH.name_en` |

อีกเคสที่ repair คือ query `DIM_POLICY_VERSION` แล้วได้ no rows เพราะ LLM filter `policy_class` แคบเกินไป ทั้งที่ตัว specific policy อยู่ใน `policy_variable`

## Markdown Table Output

pipeline ตอนนี้จบที่ markdown result table จาก SQL เท่านั้น ไม่มี final-answer formatter stage และไม่มี LLM รอบสองสำหรับจัดรูปคำตอบ

ตัวอย่าง:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-MED-019 \
  --limit 50
```

## ใช้งานกับ questions.csv

ดูคำถามจาก `questions.csv` ด้วย id:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-EASY-001
```

ตัวอย่างที่ทดสอบแล้ว:

```bash
python3 agentic_ai/fahmai_sql_agent.py --planner llm-sql --question-id L3-Q-EASY-001
python3 agentic_ai/fahmai_sql_agent.py --planner llm-sql --question-id L3-Q-EASY-003
python3 agentic_ai/fahmai_sql_agent.py --planner llm-sql --question-id L3-Q-EASY-011
python3 agentic_ai/fahmai_sql_agent.py --planner llm-sql --question-id L3-Q-MED-001
```

รันทุกคำถามแล้วเก็บ markdown table result เป็น CSV:

```bash
python3 agentic_ai/run_all_questions.py \
  --output final_answers_rerun.csv \
  --fallback-to-rules \
  --question-timeout 120 \
  --query-timeout 30
```

output มี 3 columns:

```text
id,question,answer
```

ใน batch output นี้ column `answer` คือ markdown table จาก SQL result ไม่ใช่คำตอบที่ผ่าน final-answer formatter

ถ้าไม่ต้องการทับไฟล์เดิม ให้ใช้ชื่อไฟล์ใหม่ใน `--output` และไม่ใส่ `--overwrite`

## Example Output

คำสั่ง:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --planner llm-sql \
  --question-id L3-Q-EASY-001
```

ผลลัพธ์:

```text
Planner: llm-sql
Question ID: L3-Q-EASY-001
Question: MSRP ของสินค้ารหัส NT-LT-001 ...
Reason: ...

SQL:
SELECT msrp_thb FROM DIM_PRODUCT WHERE sku_id = 'NT-LT-001'

| msrp_thb |
| --- |
| 42900.00 |
```

## Rebuild Database

ถ้าแก้ CSV, เพิ่งรัน redaction, แก้ importer/schema หรืออยากสร้าง DB ใหม่:

```bash
python3 agentic_ai/fahmai_sql_agent.py \
  --rebuild-db \
  --planner rules \
  "ยอดขายตามสาขาปี 2025" \
  --limit 5
```

## ข้อจำกัดปัจจุบัน

ระบบตอนนี้ตอบคำถามจาก `DIM/FACT` ได้ดีที่สุด

แต่ `questions.csv` มีบางกลุ่มที่ต้องอ่านข้อมูลนอก table เช่น:

```text
docs/
logs/
reports/
chat_line_oa/
chat_line_works/
renders/
```

คำถามกลุ่ม `HARD`, `XHARD`, `REF` บางข้อจึงควรเพิ่ม retrieval layer สำหรับ unstructured data ต่อ เช่น:

```text
question
  -> detect needed corpus
  -> search docs/logs/chats
  -> provide retrieved context to LLM
  -> combine with SQL result
  -> answer with citations/context
```

## สรุป

ระบบตอนนี้มี 4 ความสามารถหลัก:

1. สร้าง typed SQLite database จาก CSV
2. สร้าง enriched FACT/DIM views
3. ใช้ rule planner หรือ ThaiLLM planner เพื่อสร้าง SQL
4. validate SQL และ execute อย่างปลอดภัย

เหมาะสำหรับใช้ตอบคำถาม data analytics จาก structured tables และเป็นฐานพร้อมต่อยอดไปสู่ RAG สำหรับเอกสาร/log/chat ใน public data lake
