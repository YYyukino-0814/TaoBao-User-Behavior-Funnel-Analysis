-- ============================================================
-- S6 · 类目转化差异 + 卡方检验
-- 业务问题：不同类目的转化率差得多吗？差得"显著"吗？这个"显著"有意义吗？
--
-- ⚠️ 口径说明：
-- 1) 粒度是【人 × 类目】配对，不是行为记录。同一个人浏览 A、B 两个类目，
--    在两个类目里各算一次。这样"浏览→购买"才是分子分母可比的漏斗，
--    而不是被记录条数污染（同 S1、S5 的口径纪律）。
-- 2) 12-02 / 12-03 已剔除（数据异常），窗口截止 2017-12-01。
-- 3) 类目共 8,044 个，长尾极长。本节只取 Top N，长尾见结果4。
-- ============================================================

-- 结果1：Top 20 类目（按浏览人数）的四层人数与转化率
WITH cu AS (
    SELECT
        category_id,
        user_id,
        MAX(CASE WHEN behavior = 'pv'   THEN 1 ELSE 0 END) AS 有浏览,
        MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS 有加购,
        MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS 有购买
    FROM events
    WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
)
SELECT
    category_id                                                     AS 类目,
    COUNT(*) FILTER (WHERE 有浏览 = 1)                              AS 浏览人数,
    COUNT(*) FILTER (WHERE 有浏览 = 1 AND 有加购 = 1)               AS 浏览且加购人数,
    COUNT(*) FILTER (WHERE 有浏览 = 1 AND 有购买 = 1)               AS 浏览且购买人数,
    ROUND(COUNT(*) FILTER (WHERE 有浏览 = 1 AND 有购买 = 1) * 100.0
          / NULLIF(COUNT(*) FILTER (WHERE 有浏览 = 1), 0), 2)       AS 浏览到购买率,
    -- 加购者中的购买率：这个类目的加购"含金量"有多高（同 S3 的思路）
    ROUND(COUNT(*) FILTER (WHERE 有加购 = 1 AND 有购买 = 1) * 100.0
          / NULLIF(COUNT(*) FILTER (WHERE 有加购 = 1), 0), 2)       AS 加购者中的购买率
FROM cu
GROUP BY 1
HAVING COUNT(*) FILTER (WHERE 有浏览 = 1) >= 3000
ORDER BY 浏览人数 DESC
LIMIT 20;

-- 结果2：卡方检验用的列联表（Top 40 类目 × 购买/未购买）
-- 导出给 Python 跑 scipy。两列 = 浏览过该类目且买过 / 浏览过但没买
WITH cu AS (
    SELECT
        category_id,
        user_id,
        MAX(CASE WHEN behavior = 'pv'  THEN 1 ELSE 0 END) AS 有浏览,
        MAX(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS 有购买
    FROM events
    WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
),
agg AS (
    SELECT
        category_id,
        COUNT(*) FILTER (WHERE 有浏览 = 1)                          AS 浏览人数,
        COUNT(*) FILTER (WHERE 有浏览 = 1 AND 有购买 = 1)           AS 购买人数
    FROM cu
    GROUP BY 1
    HAVING COUNT(*) FILTER (WHERE 有浏览 = 1) >= 3000
)
SELECT
    category_id                                                     AS 类目,
    购买人数                                                        AS 购买,
    浏览人数 - 购买人数                                             AS 未购买,
    浏览人数                                                        AS 合计,
    ROUND(购买人数 * 100.0 / 浏览人数, 2)                           AS 转化率
FROM agg
ORDER BY 浏览人数 DESC
LIMIT 40;

-- 结果3：长尾检查 —— 多少类目承担了多少流量
-- 如果 Top 20 就吃掉绝大部分，"类目转化差异"这件事的适用面就有限
WITH cu AS (
    SELECT category_id, user_id,
           MAX(CASE WHEN behavior = 'pv' THEN 1 ELSE 0 END) AS 有浏览
    FROM events
    WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
),
cat AS (
    SELECT category_id, COUNT(*) FILTER (WHERE 有浏览 = 1) AS 浏览人数
    FROM cu GROUP BY 1
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (ORDER BY 浏览人数 DESC) AS rk,
           SUM(浏览人数) OVER () AS 总浏览人次
    FROM cat
    WHERE 浏览人数 > 0
)
SELECT
    'Top 20'  AS 范围, ROUND(SUM(浏览人数) * 100.0 / MAX(总浏览人次), 2) AS 占全部浏览人次比例 FROM ranked WHERE rk <= 20
UNION ALL
SELECT 'Top 100', ROUND(SUM(浏览人数) * 100.0 / MAX(总浏览人次), 2) FROM ranked WHERE rk <= 100
UNION ALL
SELECT 'Top 500', ROUND(SUM(浏览人数) * 100.0 / MAX(总浏览人次), 2) FROM ranked WHERE rk <= 500;

-- 结果4：类目数的规模（给结果3配套读，单位不同所以单独一个结果集）
SELECT
    COUNT(DISTINCT category_id)                                     AS 数据里出现的类目总数,
    COUNT(DISTINCT CASE WHEN behavior = 'pv'  THEN category_id END) AS 有浏览的类目数,
    COUNT(DISTINCT CASE WHEN behavior = 'buy' THEN category_id END) AS 有购买的类目数
FROM events
WHERE dt <= DATE '2017-12-01';

-- 结果5（稳健性）：把窗口切成前后两半，同一个类目的转化率是否稳定复现
-- 显著性会被大样本"买"出来，复现性不会 —— 这一列比 p 值有用
WITH cu AS (
    SELECT
        category_id, user_id,
        MAX(CASE WHEN behavior = 'pv'  THEN 1 ELSE 0 END) AS 有浏览,
        MAX(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS 有购买,
        MAX(CASE WHEN dt <= DATE '2017-11-28' THEN 1 ELSE 0 END) AS 属前半段,
        MAX(CASE WHEN dt >= DATE '2017-11-29' THEN 1 ELSE 0 END) AS 属后半段
    FROM events
    WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
)
SELECT
    category_id                                                     AS 类目,
    ROUND(COUNT(*) FILTER (WHERE 有浏览 = 1 AND 属前半段 = 1 AND 有购买 = 1) * 100.0
          / NULLIF(COUNT(*) FILTER (WHERE 有浏览 = 1 AND 属前半段 = 1), 0), 2) AS 前半段转化率,
    COUNT(*) FILTER (WHERE 有浏览 = 1 AND 属前半段 = 1)              AS 前半段浏览人数,
    ROUND(COUNT(*) FILTER (WHERE 有浏览 = 1 AND 属后半段 = 1 AND 有购买 = 1) * 100.0
          / NULLIF(COUNT(*) FILTER (WHERE 有浏览 = 1 AND 属后半段 = 1), 0), 2) AS 后半段转化率,
    COUNT(*) FILTER (WHERE 有浏览 = 1 AND 属后半段 = 1)              AS 后半段浏览人数
FROM cu
GROUP BY 1
HAVING COUNT(*) FILTER (WHERE 有浏览 = 1 AND 属前半段 = 1) >= 1500
   AND COUNT(*) FILTER (WHERE 有浏览 = 1 AND 属后半段 = 1) >= 1500
ORDER BY 前半段浏览人数 DESC
LIMIT 40;
