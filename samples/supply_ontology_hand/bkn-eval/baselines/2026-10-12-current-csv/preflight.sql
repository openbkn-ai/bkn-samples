-- Read-only verification of the delivered sample data, not a scored Agent run.
-- Expected: three distinct IDs, each with one row, product U00-000080,
-- status 正常, and quantities 3000 / 6000 / 500.
SELECT id, material_number, closestatus_title, qty, bizdate, enddate
FROM erp_mds_forecast
WHERE id IN ('0000023181-FUTURE', '0000023181-SHORT', '0000023181-CONTENTION')
ORDER BY id;

-- Expected: 137 / 115922.
SELECT COUNT(*) AS total_count, SUM(qty) AS total_qty FROM erp_mds_forecast;

-- Expected: 90 / 90 / 56340.
SELECT COUNT(*) AS open_rows, COUNT(DISTINCT id) AS open_ids, SUM(qty) AS open_qty
FROM erp_mds_forecast WHERE closestatus_title != '已关闭';

-- Expected: 12 / 20000.
SELECT COUNT(DISTINCT id) AS open_ids, SUM(qty) AS open_qty
FROM erp_mds_forecast
WHERE closestatus_title != '已关闭' AND material_number = 'U00-000080';

-- Expected: 47 / 59582.
SELECT COUNT(*) AS closed_rows, SUM(qty) AS closed_qty
FROM erp_mds_forecast WHERE closestatus_title = '已关闭';
