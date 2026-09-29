-- ============================================================
-- S1 · 数据认识：整体规模 + 四种行为结构 + 每日概览
-- 主表 events：1000 万行样本，2017-11-25 ~ 12-03（北京时间），已清洗异常时间戳
-- 业务问题：这片数据里，用户在干什么？全站是不是天然的"逛多买少"？
-- ============================================================

-- 结果1：整体规模（先把"有多大"钉死）
SELECT
    COUNT(*)                    AS 总行为记录数,
    COUNT(DISTINCT user_id)     AS 用户数,
    COUNT(DISTINCT item_id)     AS 商品数,
    COUNT(DISTINCT category_id) AS 类目数,
    COUNT(DISTINCT dt)          AS 覆盖天数
FROM events;

-- 结果2：四种行为结构（行数口径 vs 人数口径，两个都要看）
-- 口径提示：行数看"动作总量"，人数看"有多少人做过这件事"，两者含义完全不同
SELECT
    behavior AS 行为,
    CASE behavior
        WHEN 'pv'   THEN '浏览'
        WHEN 'fav'  THEN '收藏'
        WHEN 'cart' THEN '加购'
        WHEN 'buy'  THEN '购买'
    END AS 中文,
    COUNT(*)                                           AS 行数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 3) AS 行数占比,
    COUNT(DISTINCT user_id)                            AS 人数,
    ROUND(COUNT(DISTINCT user_id) * 100.0
          / (SELECT COUNT(DISTINCT user_id) FROM events), 2) AS 人数占比
FROM events
GROUP BY behavior
ORDER BY 行数 DESC;

-- 结果3：每日概览（先看有没有明显的日子差异）
SELECT
    dt                                                 AS 日期,
    COUNT(*)                                           AS 行为行数,
    COUNT(DISTINCT user_id)                            AS 活跃用户数,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_id), 2) AS 人均行为数
FROM events
GROUP BY dt
ORDER BY dt;
