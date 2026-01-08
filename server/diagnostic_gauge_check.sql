-- ===============================================
-- Diagnostic SQL Script for Gauge Analysis
-- Purpose: Check why YTD Rev Target and Realized Rev Target show 0%
-- Date: January 8, 2026
-- ===============================================

-- Step 1: Check Company Yearly Target for 2026
-- Expected: Should return a row with positive yearly_target
SELECT
    '1. Company Yearly Target' AS check_name,
    year,
    yearly_target,
    yearly_target / 1000000.0 AS target_millions,
    CASE
        WHEN yearly_target > 0 THEN '✅ Target is set'
        ELSE '❌ No target set - Please configure in Target KPI'
    END AS status
FROM target_kpi_settings
WHERE year = 2026;

-- If no results, target is not set!
-- Fix: Go to PLB > Config > Target KPI and set a yearly target for 2026


-- Step 2: Check Contract Stage Configuration
-- Expected: Should return at least one stage with name containing 'contract'
SELECT
    '2. Contract Stages' AS check_name,
    id AS stage_id,
    name AS stage_name,
    probability,
    CASE
        WHEN probability >= 100 THEN '✅ Won stage'
        WHEN probability = 0 THEN '⚠️ Lost stage'
        ELSE '📊 In progress'
    END AS stage_type
FROM crm_stage
WHERE name ILIKE '%contract%'
ORDER BY probability DESC;

-- If no results, no "contract" stage exists!
-- Check stage names or adjust search criteria


-- Step 3: Check Total Leads in Contract Stage
-- Expected: Should show leads in contract stage
SELECT
    '3. All Contract Leads' AS check_name,
    COUNT(*) AS total_contract_leads,
    COUNT(CASE WHEN date_go_live IS NOT NULL THEN 1 END) AS with_date_go_live,
    COUNT(CASE WHEN date_go_live IS NULL THEN 1 END) AS missing_date_go_live,
    ROUND(SUM(expected_revenue)::numeric, 2) AS total_expected_revenue,
    CASE
        WHEN COUNT(*) = 0 THEN '❌ No contract leads found'
        WHEN COUNT(CASE WHEN date_go_live IS NULL THEN 1 END) > 0
            THEN '⚠️ Some leads missing date_go_live - needs data migration'
        ELSE '✅ All leads have date_go_live'
    END AS status
FROM crm_lead l
JOIN crm_stage s ON l.stage_id = s.id
WHERE s.name ILIKE '%contract%';


-- Step 4: Check Contract Leads with date_go_live in 2026 (KEY CHECK!)
-- Expected: Should return leads with date_go_live in 2026
-- This is CRITICAL - if empty, gauges will show 0%
SELECT
    '4. Contract Leads in 2026' AS check_name,
    l.id,
    l.name AS lead_name,
    s.name AS stage_name,
    l.expected_revenue,
    l.date_go_live,
    l.contract_months,
    l.realized_revenue,
    EXTRACT(YEAR FROM l.date_go_live) AS go_live_year,
    EXTRACT(MONTH FROM l.date_go_live) AS go_live_month,
    -- Calculate MAR
    CASE
        WHEN l.contract_months > 0 THEN l.expected_revenue / l.contract_months
        ELSE 0
    END AS mar,
    -- Calculate months in 2026
    CASE
        WHEN EXTRACT(MONTH FROM l.date_go_live) IS NOT NULL
            THEN 12 - EXTRACT(MONTH FROM l.date_go_live) + 1
        ELSE 0
    END AS months_in_2026
FROM crm_lead l
JOIN crm_stage s ON l.stage_id = s.id
WHERE s.name ILIKE '%contract%'
  AND l.date_go_live IS NOT NULL
  AND EXTRACT(YEAR FROM l.date_go_live) = 2026
ORDER BY l.date_go_live;

-- If this returns ZERO rows, that's why gauges show 0%!
-- Causes:
--   1. No leads in contract stage
--   2. All contract leads have NULL date_go_live
--   3. All contract leads have date_go_live in different years


-- Step 5: Summary Calculation (What the gauge sees)
-- This simulates the exact calculation done by the system
WITH contract_leads AS (
    SELECT
        l.id,
        l.name,
        l.expected_revenue,
        l.date_go_live,
        l.contract_months,
        EXTRACT(YEAR FROM l.date_go_live) AS go_live_year,
        EXTRACT(MONTH FROM l.date_go_live) AS go_live_month,
        CASE
            WHEN l.contract_months > 0 THEN l.expected_revenue / l.contract_months
            ELSE 0
        END AS mar
    FROM crm_lead l
    JOIN crm_stage s ON l.stage_id = s.id
    WHERE s.name ILIKE '%contract%'
      AND l.date_go_live IS NOT NULL
      AND EXTRACT(YEAR FROM l.date_go_live) = 2026
),
realized_calc AS (
    SELECT
        id,
        name,
        expected_revenue,
        date_go_live,
        go_live_month,
        contract_months,
        mar,
        -- Calculate how many months of MAR to count
        LEAST(contract_months, 12 - go_live_month + 1) AS active_months,
        mar * LEAST(contract_months, 12 - go_live_month + 1) AS lead_realized_revenue
    FROM contract_leads
),
targets AS (
    SELECT yearly_target
    FROM target_kpi_settings
    WHERE year = 2026
    LIMIT 1
)
SELECT
    '5. Final Calculation' AS check_name,
    COUNT(rc.id) AS lead_count,
    COALESCE(SUM(rc.expected_revenue), 0) AS total_expected_revenue,
    COALESCE(SUM(rc.lead_realized_revenue), 0) AS total_realized_revenue,
    COALESCE(t.yearly_target, 0) AS yearly_target,
    -- YTD Percentage
    CASE
        WHEN t.yearly_target > 0 THEN
            ROUND((SUM(rc.expected_revenue) / t.yearly_target * 100)::numeric, 2)
        ELSE 0
    END AS ytd_percentage,
    -- Realized Percentage
    CASE
        WHEN t.yearly_target > 0 THEN
            ROUND((SUM(rc.lead_realized_revenue) / t.yearly_target * 100)::numeric, 2)
        ELSE 0
    END AS realized_percentage,
    -- Status
    CASE
        WHEN COUNT(rc.id) = 0 THEN '❌ No leads found - Check Step 4'
        WHEN t.yearly_target IS NULL OR t.yearly_target = 0 THEN '❌ No yearly target - Check Step 1'
        WHEN SUM(rc.expected_revenue) = 0 THEN '⚠️ No expected revenue in leads'
        ELSE '✅ Data looks good - gauges should show percentages'
    END AS status
FROM realized_calc rc
CROSS JOIN targets t
GROUP BY t.yearly_target;


-- Step 6: Breakdown by Lead (Detailed View)
-- This shows exactly what each lead contributes
SELECT
    '6. Lead-by-Lead Breakdown' AS check_name,
    l.id,
    l.name AS lead_name,
    l.expected_revenue,
    l.date_go_live,
    EXTRACT(MONTH FROM l.date_go_live) AS go_live_month,
    l.contract_months,
    -- MAR calculation
    CASE
        WHEN l.contract_months > 0 THEN
            ROUND((l.expected_revenue / l.contract_months)::numeric, 2)
        ELSE 0
    END AS mar,
    -- Months active in 2026
    CASE
        WHEN EXTRACT(MONTH FROM l.date_go_live) IS NOT NULL THEN
            12 - EXTRACT(MONTH FROM l.date_go_live) + 1
        ELSE 0
    END AS months_remaining_in_year,
    -- Active months (capped by contract months)
    CASE
        WHEN l.contract_months > 0 AND EXTRACT(MONTH FROM l.date_go_live) IS NOT NULL THEN
            LEAST(l.contract_months, 12 - EXTRACT(MONTH FROM l.date_go_live) + 1)
        ELSE 0
    END AS active_months,
    -- Realized revenue for this lead
    CASE
        WHEN l.contract_months > 0 AND EXTRACT(MONTH FROM l.date_go_live) IS NOT NULL THEN
            ROUND(((l.expected_revenue / l.contract_months) *
                   LEAST(l.contract_months, 12 - EXTRACT(MONTH FROM l.date_go_live) + 1))::numeric, 2)
        ELSE 0
    END AS lead_realized_revenue
FROM crm_lead l
JOIN crm_stage s ON l.stage_id = s.id
WHERE s.name ILIKE '%contract%'
  AND l.date_go_live IS NOT NULL
  AND EXTRACT(YEAR FROM l.date_go_live) = 2026
ORDER BY l.date_go_live;


-- Step 7: Data Migration Script (if needed)
-- Run this if Step 3 shows missing date_go_live
-- UNCOMMENT and RUN only if you want to populate date_go_live

/*
-- Option A: Copy from expected_start_date
UPDATE crm_lead
SET date_go_live = expected_start_date
WHERE date_go_live IS NULL
  AND expected_start_date IS NOT NULL
  AND stage_id IN (SELECT id FROM crm_stage WHERE name ILIKE '%contract%');

-- Option B: Copy from date_secured for won deals
UPDATE crm_lead
SET date_go_live = date_secured
WHERE date_go_live IS NULL
  AND date_secured IS NOT NULL
  AND stage_id IN (SELECT id FROM crm_stage WHERE probability >= 100);

-- Check results
SELECT
    'After Migration' AS status,
    COUNT(*) AS total_leads,
    COUNT(date_go_live) AS with_go_live,
    COUNT(*) - COUNT(date_go_live) AS still_missing
FROM crm_lead l
JOIN crm_stage s ON l.stage_id = s.id
WHERE s.name ILIKE '%contract%';
*/


-- ===============================================
-- INTERPRETATION GUIDE
-- ===============================================
--
-- If Step 5 shows:
-- - lead_count = 0: No contract leads with date_go_live in 2026
--   → Need to populate date_go_live OR move leads to contract stage
--
-- - yearly_target = 0: No target set for 2026
--   → Go to PLB > Config > Target KPI and set target
--
-- - total_expected_revenue = 0: Leads exist but no revenue
--   → Check expected_revenue field is populated
--
-- - ytd_percentage > 0 and realized_percentage > 0: ✅ Working!
--   → Restart Odoo service to see changes
--
-- ===============================================

