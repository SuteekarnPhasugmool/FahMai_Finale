DROP VIEW IF EXISTS VW_FACT_SALES_ENRICHED;
CREATE VIEW VW_FACT_SALES_ENRICHED AS
SELECT
  f.*,
  db.name_en AS branch_name_en,
  db.name_th AS branch_name_th,
  db.branch_type,
  db.is_service_center AS branch_is_service_center,
  dc.customer_type,
  dc.b2b_subtype,
  dc.region AS customer_region,
  dc.province AS customer_province,
  dc.loyalty_tier AS customer_loyalty_tier,
  de.first_name_en AS employee_first_name_en,
  de.last_name_en AS employee_last_name_en,
  de.position_title AS employee_position_title,
  de.position_level AS employee_position_level,
  dept.dept_name_en AS department_name_en,
  dept.dept_type AS department_type,
  pc.description_en AS promo_campaign_description_en,
  pc.start_timestamp AS promo_start_timestamp,
  pc.end_timestamp AS promo_end_timestamp,
  bt.account_id AS settlement_account_id,
  bt.amount_thb AS settlement_amount_thb,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  event_date.day_of_week AS event_day_of_week,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter,
  due_date.fiscal_year AS due_fiscal_year,
  received_date.fiscal_year AS received_fiscal_year
FROM FACT_SALES f
LEFT JOIN DIM_BRANCH db ON f.branch_code = db.branch_code
LEFT JOIN DIM_CUSTOMER dc ON f.customer_id = dc.customer_id
LEFT JOIN DIM_EMPLOYEE de ON f.employee_id = de.employee_id
LEFT JOIN DIM_DEPARTMENT dept ON de.dept_code = dept.dept_code
LEFT JOIN DIM_PROMO_CAMPAIGN pc ON f.promo_campaign_id = pc.campaign_id
LEFT JOIN FACT_BANK_TRANSACTION bt ON f.settlement_bank_txn_id = bt.bank_txn_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso
LEFT JOIN DIM_DATE due_date ON f.payment_due_date = due_date.date_iso
LEFT JOIN DIM_DATE received_date ON f.payment_received_date = received_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_SALES_LINE_ITEM_ENRICHED;
CREATE VIEW VW_FACT_SALES_LINE_ITEM_ENRICHED AS
SELECT
  f.*,
  dp.brand_family AS product_brand_family,
  dp.category AS product_category,
  dp.subcategory AS product_subcategory,
  dp.msrp_thb AS product_msrp_thb,
  dp.msrp_tier AS product_msrp_tier,
  dp.is_third_party AS product_is_third_party,
  dp.warranty_months AS product_warranty_months,
  dept.dept_name_en AS product_department_name_en,
  dv.name_en AS vendor_name_en,
  dv.category AS vendor_category,
  sales.branch_code,
  sales.customer_id,
  sales.employee_id,
  sales.channel,
  sales.payment_method,
  sales.payment_status,
  db.name_en AS branch_name_en,
  dc.customer_type,
  dc.region AS customer_region,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_SALES_LINE_ITEM f
LEFT JOIN DIM_PRODUCT dp ON f.sku_id = dp.sku_id
LEFT JOIN DIM_DEPARTMENT dept ON dp.dept_code = dept.dept_code
LEFT JOIN DIM_VENDOR dv ON dp.vendor_id = dv.vendor_id
LEFT JOIN FACT_SALES sales ON f.txn_id = sales.txn_id
LEFT JOIN DIM_BRANCH db ON sales.branch_code = db.branch_code
LEFT JOIN DIM_CUSTOMER dc ON sales.customer_id = dc.customer_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_INVENTORY_MOVEMENT_ENRICHED;
CREATE VIEW VW_FACT_INVENTORY_MOVEMENT_ENRICHED AS
SELECT
  f.*,
  dp.brand_family AS product_brand_family,
  dp.category AS product_category,
  dp.subcategory AS product_subcategory,
  dp.msrp_tier AS product_msrp_tier,
  dept.dept_name_en AS product_department_name_en,
  dv.name_en AS vendor_name_en,
  dv.category AS vendor_category,
  db.name_en AS branch_name_en,
  db.name_th AS branch_name_th,
  db.branch_type,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  event_date.day_of_week AS event_day_of_week,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_INVENTORY_MOVEMENT f
LEFT JOIN DIM_PRODUCT dp ON f.sku_id = dp.sku_id
LEFT JOIN DIM_DEPARTMENT dept ON dp.dept_code = dept.dept_code
LEFT JOIN DIM_VENDOR dv ON dp.vendor_id = dv.vendor_id
LEFT JOIN DIM_BRANCH db ON f.branch_code = db.branch_code
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_INVENTORY_MONTHLY_SNAPSHOT_ENRICHED;
CREATE VIEW VW_FACT_INVENTORY_MONTHLY_SNAPSHOT_ENRICHED AS
SELECT
  f.*,
  dp.brand_family AS product_brand_family,
  dp.category AS product_category,
  dp.subcategory AS product_subcategory,
  dp.msrp_tier AS product_msrp_tier,
  dept.dept_name_en AS product_department_name_en,
  dv.name_en AS vendor_name_en,
  db.name_en AS branch_name_en,
  db.branch_type,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  month_end_date.fiscal_year AS month_end_fiscal_year,
  month_end_date.fiscal_quarter AS month_end_fiscal_quarter
FROM FACT_INVENTORY_MONTHLY_SNAPSHOT f
LEFT JOIN DIM_PRODUCT dp ON f.sku_id = dp.sku_id
LEFT JOIN DIM_DEPARTMENT dept ON dp.dept_code = dept.dept_code
LEFT JOIN DIM_VENDOR dv ON dp.vendor_id = dv.vendor_id
LEFT JOIN DIM_BRANCH db ON f.branch_code = db.branch_code
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE month_end_date ON f.month_end_date = month_end_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_LOYALTY_LEDGER_ENRICHED;
CREATE VIEW VW_FACT_LOYALTY_LEDGER_ENRICHED AS
SELECT
  f.*,
  dc.customer_type,
  dc.b2b_subtype,
  dc.region AS customer_region,
  dc.province AS customer_province,
  dc.loyalty_tier AS customer_loyalty_tier,
  dc.account_manager_id AS account_manager_employee_id,
  mgr.first_name_en AS account_manager_first_name_en,
  mgr.last_name_en AS account_manager_last_name_en,
  mgr.position_level AS account_manager_position_level,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  event_date.day_of_week AS event_day_of_week,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_LOYALTY_LEDGER f
LEFT JOIN DIM_CUSTOMER dc ON f.customer_id = dc.customer_id
LEFT JOIN DIM_EMPLOYEE mgr ON dc.account_manager_id = mgr.employee_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_PAYROLL_ENRICHED;
CREATE VIEW VW_FACT_PAYROLL_ENRICHED AS
SELECT
  f.*,
  de.first_name_en AS employee_first_name_en,
  de.last_name_en AS employee_last_name_en,
  de.branch_code AS employee_branch_code,
  de.dept_code AS employee_dept_code,
  de.position_title AS employee_position_title,
  de.position_level AS employee_position_level,
  de.employment_type,
  de.is_canon_leader,
  db.name_en AS employee_branch_name_en,
  dept.dept_name_en AS department_name_en,
  dept.dept_type AS department_type,
  pl.rank AS position_level_rank,
  pl.default_signing_authority_thb,
  bt.account_id AS payroll_bank_account_id,
  bt.amount_thb AS payroll_bank_amount_thb,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter,
  period_start.fiscal_year AS period_start_fiscal_year,
  period_start.fiscal_quarter AS period_start_fiscal_quarter,
  period_end.fiscal_year AS period_end_fiscal_year,
  period_end.fiscal_quarter AS period_end_fiscal_quarter
FROM FACT_PAYROLL f
LEFT JOIN DIM_EMPLOYEE de ON f.employee_id = de.employee_id
LEFT JOIN DIM_BRANCH db ON de.branch_code = db.branch_code
LEFT JOIN DIM_DEPARTMENT dept ON de.dept_code = dept.dept_code
LEFT JOIN DIM_POSITION_LEVEL pl ON de.position_level = pl.position_level_code
LEFT JOIN FACT_BANK_TRANSACTION bt ON f.bank_txn_id = bt.bank_txn_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso
LEFT JOIN DIM_DATE period_start ON f.pay_period_start = period_start.date_iso
LEFT JOIN DIM_DATE period_end ON f.pay_period_end = period_end.date_iso;

DROP VIEW IF EXISTS VW_FACT_PROMO_REDEMPTION_ENRICHED;
CREATE VIEW VW_FACT_PROMO_REDEMPTION_ENRICHED AS
SELECT
  f.*,
  dc.customer_type,
  dc.b2b_subtype,
  dc.region AS customer_region,
  dc.loyalty_tier AS customer_loyalty_tier,
  pc.description_en AS campaign_description_en,
  pc.description_th AS campaign_description_th,
  pc.start_timestamp AS campaign_start_timestamp,
  pc.end_timestamp AS campaign_end_timestamp,
  pm.discount_type,
  pm.discount_value,
  pm.point_multiplier,
  pm.min_basket_thb,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_PROMO_REDEMPTION f
LEFT JOIN DIM_CUSTOMER dc ON f.customer_id = dc.customer_id
LEFT JOIN DIM_PROMO_CAMPAIGN pc ON f.campaign_id = pc.campaign_id
LEFT JOIN dim_promo_mechanic pm ON f.campaign_id = pm.campaign_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_RETURN_ENRICHED;
CREATE VIEW VW_FACT_RETURN_ENRICHED AS
SELECT
  f.*,
  dp.brand_family AS product_brand_family,
  dp.category AS product_category,
  dp.subcategory AS product_subcategory,
  dept.dept_name_en AS product_department_name_en,
  dv.name_en AS vendor_name_en,
  db.name_en AS branch_name_en,
  dc.customer_type,
  dc.region AS customer_region,
  approver.first_name_en AS approver_first_name_en,
  approver.last_name_en AS approver_last_name_en,
  approver.position_level AS approver_position_level,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_RETURN f
LEFT JOIN DIM_PRODUCT dp ON f.sku_id = dp.sku_id
LEFT JOIN DIM_DEPARTMENT dept ON dp.dept_code = dept.dept_code
LEFT JOIN DIM_VENDOR dv ON dp.vendor_id = dv.vendor_id
LEFT JOIN DIM_BRANCH db ON f.branch_code = db.branch_code
LEFT JOIN DIM_CUSTOMER dc ON f.customer_id = dc.customer_id
LEFT JOIN DIM_EMPLOYEE approver ON f.approved_by_employee_id = approver.employee_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_REFUND_PAID_ENRICHED;
CREATE VIEW VW_FACT_REFUND_PAID_ENRICHED AS
SELECT
  f.*,
  dc.customer_type,
  dc.region AS customer_region,
  approver.first_name_en AS approver_first_name_en,
  approver.last_name_en AS approver_last_name_en,
  approver.position_level AS approver_position_level,
  cosig.first_name_en AS cosig_first_name_en,
  cosig.last_name_en AS cosig_last_name_en,
  cosig.position_level AS cosig_position_level,
  ret.return_reason,
  ret.return_amount_thb,
  bt.account_id AS refund_bank_account_id,
  bt.amount_thb AS refund_bank_amount_thb,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  request_date.fiscal_year AS request_fiscal_year,
  request_date.fiscal_quarter AS request_fiscal_quarter
FROM FACT_REFUND_PAID f
LEFT JOIN DIM_CUSTOMER dc ON f.customer_id = dc.customer_id
LEFT JOIN DIM_EMPLOYEE approver ON f.approver_employee_id = approver.employee_id
LEFT JOIN DIM_EMPLOYEE cosig ON f.cosig_employee_id = cosig.employee_id
LEFT JOIN FACT_RETURN ret ON f.return_id = ret.return_id
LEFT JOIN FACT_BANK_TRANSACTION bt ON f.bank_txn_id = bt.bank_txn_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE request_date ON f.request_date = request_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_BANK_TRANSACTION_ENRICHED;
CREATE VIEW VW_FACT_BANK_TRANSACTION_ENRICHED AS
SELECT
  f.*,
  ba.bank,
  ba.account_number,
  ba.account_role,
  ba.associated_branch_code,
  ba.currency,
  db.name_en AS associated_branch_name_en,
  db.branch_type AS associated_branch_type,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_BANK_TRANSACTION f
LEFT JOIN DIM_BANK_ACCOUNT ba ON f.account_id = ba.account_id
LEFT JOIN DIM_BRANCH db ON ba.associated_branch_code = db.branch_code
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_VENDOR_PAYMENT_ENRICHED;
CREATE VIEW VW_FACT_VENDOR_PAYMENT_ENRICHED AS
SELECT
  f.*,
  dv.name_en AS vendor_name_en,
  dv.category AS vendor_category,
  dv.role AS vendor_role,
  dv.payment_terms AS vendor_payment_terms,
  contract.version_number AS vendor_contract_version_number,
  contract.effective_date AS vendor_contract_effective_date,
  contract.end_date AS vendor_contract_end_date,
  signer.first_name_en AS signing_employee_first_name_en,
  signer.last_name_en AS signing_employee_last_name_en,
  signer.position_level AS signing_employee_position_level,
  cosig.first_name_en AS cosig_employee_first_name_en,
  cosig.last_name_en AS cosig_employee_last_name_en,
  cosig.position_level AS cosig_employee_position_level,
  bt.account_id AS vendor_payment_bank_account_id,
  bt.amount_thb AS vendor_payment_bank_amount_thb,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  request_date.fiscal_year AS request_fiscal_year,
  request_date.fiscal_quarter AS request_fiscal_quarter,
  invoice_start.fiscal_year AS invoice_start_fiscal_year,
  invoice_end.fiscal_year AS invoice_end_fiscal_year
FROM FACT_VENDOR_PAYMENT f
LEFT JOIN DIM_VENDOR dv ON f.vendor_id = dv.vendor_id
LEFT JOIN DIM_VENDOR_CONTRACT_VERSION contract ON f.vendor_contract_version_id = contract.contract_version_id
LEFT JOIN DIM_EMPLOYEE signer ON f.signing_employee_id = signer.employee_id
LEFT JOIN DIM_EMPLOYEE cosig ON f.cosig_employee_id = cosig.employee_id
LEFT JOIN FACT_BANK_TRANSACTION bt ON f.bank_txn_id = bt.bank_txn_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE request_date ON f.request_date = request_date.date_iso
LEFT JOIN DIM_DATE invoice_start ON f.invoice_period_start = invoice_start.date_iso
LEFT JOIN DIM_DATE invoice_end ON f.invoice_period_end = invoice_end.date_iso;

DROP VIEW IF EXISTS VW_FACT_SHIPPING_ENRICHED;
CREATE VIEW VW_FACT_SHIPPING_ENRICHED AS
SELECT
  f.*,
  dv.name_en AS vendor_name_en,
  dv.category AS vendor_category,
  db.name_en AS origin_branch_name_en,
  db.branch_type AS origin_branch_type,
  sales.customer_id,
  sales.channel,
  sales.net_total_thb AS sales_net_total_thb,
  dc.customer_type,
  dc.region AS customer_region,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_SHIPPING f
LEFT JOIN DIM_VENDOR dv ON f.vendor_id = dv.vendor_id
LEFT JOIN DIM_BRANCH db ON f.origin_branch_code = db.branch_code
LEFT JOIN FACT_SALES sales ON f.txn_id = sales.txn_id
LEFT JOIN DIM_CUSTOMER dc ON sales.customer_id = dc.customer_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_WARRANTY_CLAIM_ENRICHED;
CREATE VIEW VW_FACT_WARRANTY_CLAIM_ENRICHED AS
WITH latest_recall AS (
  SELECT sku_id, status, transition_date
  FROM (
    SELECT
      sku_id,
      status,
      transition_date,
      ROW_NUMBER() OVER (PARTITION BY sku_id ORDER BY transition_date DESC, history_id DESC) AS rn
    FROM dim_product_recall_history
  )
  WHERE rn = 1
)
SELECT
  f.*,
  dc.customer_type,
  dc.region AS customer_region,
  dp.brand_family AS product_brand_family,
  dp.category AS product_category,
  dp.subcategory AS product_subcategory,
  dp.warranty_months AS product_warranty_months,
  dept.dept_name_en AS product_department_name_en,
  dv.name_en AS vendor_name_en,
  latest_recall.status AS latest_recall_status,
  latest_recall.transition_date AS latest_recall_transition_date,
  sales.branch_code AS original_sale_branch_code,
  sales.channel AS original_sale_channel,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_WARRANTY_CLAIM f
LEFT JOIN DIM_CUSTOMER dc ON f.customer_id = dc.customer_id
LEFT JOIN DIM_PRODUCT dp ON f.sku_id = dp.sku_id
LEFT JOIN DIM_DEPARTMENT dept ON dp.dept_code = dept.dept_code
LEFT JOIN DIM_VENDOR dv ON dp.vendor_id = dv.vendor_id
LEFT JOIN latest_recall ON f.sku_id = latest_recall.sku_id
LEFT JOIN FACT_SALES sales ON f.original_txn_id = sales.txn_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;

DROP VIEW IF EXISTS VW_FACT_CS_INTERACTION_ENRICHED;
CREATE VIEW VW_FACT_CS_INTERACTION_ENRICHED AS
SELECT
  f.*,
  dc.customer_type,
  dc.region AS customer_region,
  dc.loyalty_tier AS customer_loyalty_tier,
  de.first_name_en AS employee_first_name_en,
  de.last_name_en AS employee_last_name_en,
  de.position_title AS employee_position_title,
  dept.dept_name_en AS department_name_en,
  db.name_en AS branch_name_en,
  refund.refund_amount_thb AS related_refund_amount_thb,
  warranty.claim_amount_thb AS related_warranty_claim_amount_thb,
  event_date.fiscal_year AS event_fiscal_year,
  event_date.fiscal_quarter AS event_fiscal_quarter,
  posting_date.fiscal_year AS posting_fiscal_year,
  posting_date.fiscal_quarter AS posting_fiscal_quarter
FROM FACT_CS_INTERACTION f
LEFT JOIN DIM_CUSTOMER dc ON f.customer_id = dc.customer_id
LEFT JOIN DIM_EMPLOYEE de ON f.employee_id = de.employee_id
LEFT JOIN DIM_DEPARTMENT dept ON de.dept_code = dept.dept_code
LEFT JOIN DIM_BRANCH db ON f.branch_code = db.branch_code
LEFT JOIN FACT_REFUND_PAID refund ON f.related_refund_id = refund.refund_id
LEFT JOIN FACT_WARRANTY_CLAIM warranty ON f.related_warranty_claim_id = warranty.claim_id
LEFT JOIN DIM_DATE event_date ON f.business_event_date = event_date.date_iso
LEFT JOIN DIM_DATE posting_date ON f.posting_date = posting_date.date_iso;
