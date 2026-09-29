-- ============================================================
-- S7 · 轻 / 中 / 重度用户分层
-- 业务问题：用户能不能按活跃程度分出层？运营资源该押在哪一层？
--
-- ⚠️ 口径说明：
-- 1) 观察窗截止 2017-12-01（12-02/12-03 为数据异常，已剔除），实际 7 天。
--    所以"行为数"是这 7 天内的行为数，不是全生命周期。
-- 2) 分层依据是【行为记录总数】。不用金额——本数据集没有金额字段。
-- 3) 切分用三分位（各层人数尽量均等），不是拍脑袋定阈值。
--    平局问题见结果5：大量用户行为数相同会让"严格等分"做不到，必须交代。
-- ============================================================

-- 结果1：三分位切分点 + 三层的人数与行为数范围
WITH u AS (
    SELECT user_id, COUNT(*) AS n
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY user_id
),
q AS (
    SELECT quantile_cont(n, 1.0 / 3) AS q1,
           quantile_cont(n, 2.0 / 3) AS q2
    FROM u
)
SELECT
    (SELECT ROUND(q1, 1) FROM q)                                    AS 三分之一分位点,
    (SELECT ROUND(q2, 1) FROM q)                                    AS 三分之二分位点,
    CASE WHEN u.n <= (SELECT q1 FROM q) THEN '1 轻度'
         WHEN u.n <= (SELECT q2 FROM q) THEN '2 中度'
         ELSE '3 重度' END                                          AS 分层,
    COUNT(*)                                                        AS 人数,
    MIN(u.n)                                                        AS 行为数下限,
    MAX(u.n)                                                        AS 行为数上限,
    ROUND(AVG(u.n), 1)                                              AS 人均行为数
FROM u
GROUP BY 3
ORDER BY 3;

-- 结果2：三层的行为构成（各层内部，四种行为各占多少）
WITH u AS (
    SELECT user_id, COUNT(*) AS n
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY user_id
),
q AS (SELECT quantile_cont(n, 1.0/3) AS q1, quantile_cont(n, 2.0/3) AS q2 FROM u),
seg AS (
    SELECT u.user_id,
           CASE WHEN u.n <= (SELECT q1 FROM q) THEN '1 轻度'
                WHEN u.n <= (SELECT q2 FROM q) THEN '2 中度'
                ELSE '3 重度' END AS 分层
    FROM u
)
SELECT
    s.分层,
    COUNT(DISTINCT e.user_id)                                       AS 人数,
    ROUND(COUNT(*) FILTER (WHERE e.behavior = 'pv') * 100.0 / COUNT(*), 2)   AS 浏览占比,
    ROUND(COUNT(*) FILTER (WHERE e.behavior = 'cart') * 100.0 / COUNT(*), 2) AS 加购占比,
    ROUND(COUNT(*) FILTER (WHERE e.behavior = 'fav') * 100.0 / COUNT(*), 2)  AS 收藏占比,
    ROUND(COUNT(*) FILTER (WHERE e.behavior = 'buy') * 100.0 / COUNT(*), 2)  AS 购买占比
FROM events e
JOIN seg s ON s.user_id = e.user_id
WHERE e.dt <= DATE '2017-12-01'
GROUP BY 1
ORDER BY 1;

-- 结果3：三层的转化与活跃指标
WITH u AS (
    SELECT user_id, COUNT(*) AS n
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY user_id
),
q AS (SELECT quantile_cont(n, 1.0/3) AS q1, quantile_cont(n, 2.0/3) AS q2 FROM u),
seg AS (
    SELECT u.user_id,
           CASE WHEN u.n <= (SELECT q1 FROM q) THEN '1 轻度'
                WHEN u.n <= (SELECT q2 FROM q) THEN '2 中度'
                ELSE '3 重度' END AS 分层
    FROM u
),
per AS (
    SELECT e.user_id,
           COUNT(DISTINCT e.dt)                                          AS 活跃天数,
           COUNT(DISTINCT e.dt) FILTER (WHERE e.behavior = 'buy')        AS 购买天数,
           MAX(CASE WHEN e.behavior = 'buy'  THEN 1 ELSE 0 END)          AS 买过,
           MAX(CASE WHEN e.behavior = 'cart' THEN 1 ELSE 0 END)          AS 加过购,
           MAX(CASE WHEN e.behavior = 'fav'  THEN 1 ELSE 0 END)          AS 收过藏,
           COUNT(DISTINCT e.item_id)                                     AS 碰过的商品数
    FROM events e
    WHERE e.dt <= DATE '2017-12-01'
    GROUP BY e.user_id
)
SELECT
    s.分层,
    COUNT(*)                                                        AS 人数,
    ROUND(AVG(p.活跃天数), 2)                                       AS 人均活跃天数,
    ROUND(AVG(p.碰过的商品数), 1)                                   AS 人均碰过的商品数,
    ROUND(SUM(p.买过) * 100.0 / COUNT(*), 2)                        AS 购买渗透率,
    ROUND(SUM(p.加过购) * 100.0 / COUNT(*), 2)                      AS 加购渗透率,
    ROUND(SUM(p.收过藏) * 100.0 / COUNT(*), 2)                      AS 收藏渗透率,
    ROUND(AVG(NULLIF(p.购买天数, 0)), 2)                            AS 购买者的人均购买天数
FROM seg s
JOIN per p ON p.user_id = s.user_id
GROUP BY 1
ORDER BY 1;

-- 结果4（本节重点）：三层各自贡献了多少
-- 对照 RFM 项目的"VIP 29% 的人贡献 75% 营收"，看行为数据上是什么结构
WITH u AS (
    SELECT user_id, COUNT(*) AS n
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY user_id
),
q AS (SELECT quantile_cont(n, 1.0/3) AS q1, quantile_cont(n, 2.0/3) AS q2 FROM u),
seg AS (
    SELECT u.user_id,
           CASE WHEN u.n <= (SELECT q1 FROM q) THEN '1 轻度'
                WHEN u.n <= (SELECT q2 FROM q) THEN '2 中度'
                ELSE '3 重度' END AS 分层
    FROM u
),
agg AS (
    SELECT s.分层,
           COUNT(*)                                                       AS 行为总数,
           COUNT(*) FILTER (WHERE e.behavior = 'buy')                     AS 购买事件数,
           COUNT(*) FILTER (WHERE e.behavior = 'cart')                    AS 加购事件数,
           COUNT(DISTINCT CASE WHEN e.behavior = 'buy' THEN e.item_id END) AS 卖出的商品数
    FROM events e
    JOIN seg s ON s.user_id = e.user_id
    WHERE e.dt <= DATE '2017-12-01'
    GROUP BY 1
)
SELECT
    分层,
    ROUND(行为总数 * 100.0 / SUM(行为总数) OVER (), 2)               AS 行为量占比,
    ROUND(购买事件数 * 100.0 / SUM(购买事件数) OVER (), 2)           AS 购买量占比,
    ROUND(加购事件数 * 100.0 / SUM(加购事件数) OVER (), 2)           AS 加购量占比,
    ROUND(卖出的商品数 * 100.0 / SUM(卖出的商品数) OVER (), 2)       AS 卖出商品数占比
FROM agg
ORDER BY 分层;

-- 结果5（稳健性）：换一个分层标准 —— 按【活跃天数】而不是【行为数】
-- 如果两种标准下各层的转化率排序一致，说明"分层"这件事本身是稳的
WITH u AS (
    SELECT user_id, COUNT(DISTINCT dt) AS days
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY user_id
),
per AS (
    SELECT e.user_id,
           MAX(CASE WHEN e.behavior = 'buy' THEN 1 ELSE 0 END) AS 买过,
           MAX(CASE WHEN e.behavior = 'cart' THEN 1 ELSE 0 END) AS 加过购
    FROM events e
    WHERE e.dt <= DATE '2017-12-01'
    GROUP BY e.user_id
)
SELECT
    CASE WHEN u.days <= 2 THEN '1 来 1~2 天'
         WHEN u.days <= 4 THEN '2 来 3~4 天'
         WHEN u.days <= 6 THEN '3 来 5~6 天'
         ELSE '4 来 7 天（天天来）' END                              AS 按活跃天数分层,
    COUNT(*)                                                        AS 人数,
    ROUND(SUM(p.买过) * 100.0 / COUNT(*), 2)                        AS 购买渗透率,
    ROUND(SUM(p.加过购) * 100.0 / COUNT(*), 2)                      AS 加购渗透率
FROM u
JOIN per p ON p.user_id = u.user_id
GROUP BY 1
ORDER BY 1;
