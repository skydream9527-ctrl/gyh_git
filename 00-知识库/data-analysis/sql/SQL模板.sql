-- =====================================================
-- SQL名称: {SQL名称}
-- 功能描述: {描述这个SQL是做什么的}
-- 业务线: {浏览器/信息流/内容中心/搜索/小说}
-- 指标说明: {说明核心指标逻辑}
-- 创建日期: {YYYY-MM-DD}
-- 更新记录:
--   YYYY-MM-DD  {更新内容} by {更新人}
-- =====================================================

-- 参数设置
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;

-- 主查询
WITH base_data AS (
    -- 基础数据逻辑
    SELECT
        dt,
        user_id,
        item_type,
        event,
        duration
    FROM
        {表名}
    WHERE
        dt BETWEEN '{start_date}' AND '{end_date}'
),

aggregated AS (
    -- 聚合逻辑
    SELECT
        dt,
        item_type,
        COUNT(DISTINCT user_id) AS uv,
        COUNT(1) AS pv,
        SUM(duration) AS total_duration
    FROM
        base_data
    GROUP BY
        dt,
        item_type
)

-- 最终结果
SELECT
    *
FROM
    aggregated
ORDER BY
    dt DESC,
    uv DESC
;
