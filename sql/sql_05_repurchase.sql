-- ============================================================
-- S5 · 复购与"一次即走"
-- 业务问题：买过东西的人，还会不会再来买第二次？
--
-- ⚠️ 三条必须先读的口径警告：
--
-- 1) 数据没有订单号。一条 buy 记录 = 一次"购买动作"（一个商品一次），
--    不是一张订单。同一天买 3 件商品 = 3 条 buy 记录。
--    所以【购买事件数 > 1】不等于复购，可能只是同一天买了好几件。
--    本节的"真复购"一律用【购买天数 > 1】（跨天回购）来定义。
--
-- 2) 观察窗只有 9 天，且 12-02 / 12-03 是数据异常（覆盖率断崖 98%），
--    已剔除。所以所有复购窗口一律截止到 2017-12-01，实际只有 7 天。
--    任何"回购率"都被右端截断压低，必须配合窗口截断检验（结果4）一起读。
--
-- 3) 9 天窗口测不了真正的复购周期（快消品通常以周/月计）。本节测的是
--    "短窗口内的回购倾向"，不能拿去说"用户忠诚度"。
-- ============================================================

-- 结果1：购买者按【购买事件数】分层 —— 这个口径会被"一天买多件"污染
WITH buyn AS (
    SELECT user_id, COUNT(*) AS n
    FROM events
    WHERE behavior = 'buy' AND dt <= DATE '2017-12-01'
    GROUP BY user_id
)
SELECT
    n                                                               AS 购买事件数,
    COUNT(*)                                                        AS 人数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS 占购买者比例
FROM buyn
GROUP BY n
ORDER BY n
LIMIT 12;

-- 结果2（主口径）：购买者按【购买天数】分层 —— 跨天才算真复购
WITH buyd AS (
    SELECT user_id, COUNT(DISTINCT dt) AS days
    FROM events
    WHERE behavior = 'buy' AND dt <= DATE '2017-12-01'
    GROUP BY user_id
)
SELECT
    CASE WHEN days = 1 THEN '1 天（一次即走）'
         WHEN days = 2 THEN '2 天'
         WHEN days = 3 THEN '3 天'
         ELSE '4 天及以上' END                                      AS 购买天数分层,
    COUNT(*)                                                        AS 人数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS 占购买者比例
FROM buyd
GROUP BY 1
ORDER BY MIN(days);

-- 结果3：相邻两次购买之间隔了几天（只看跨天回购的人）
WITH buyd AS (
    SELECT DISTINCT user_id, dt FROM events
    WHERE behavior = 'buy' AND dt <= DATE '2017-12-01'
),
seq AS (
    SELECT user_id, dt,
           LAG(dt) OVER (PARTITION BY user_id ORDER BY dt) AS prev_dt
    FROM buyd
)
SELECT
    date_diff('day', prev_dt, dt)                                   AS 间隔天数,
    COUNT(*)                                                        AS 次数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS 占比
FROM seq
WHERE prev_dt IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- 结果4（窗口截断检验）：按首次购买日看"次日会不会再买"
-- 剩余可观察天数越少，回购率被压得越低 —— 不看这一列就会把截断当成规律
WITH firstbuy AS (
    SELECT user_id, MIN(dt) AS d0
    FROM events
    WHERE behavior = 'buy'
    GROUP BY user_id
),
buyd AS (
    SELECT DISTINCT user_id, dt FROM events
    WHERE behavior = 'buy' AND dt <= DATE '2017-12-01'
)
SELECT
    f.d0                                                            AS 首次购买日,
    COUNT(DISTINCT f.user_id)                                       AS 首购人数,
    date_diff('day', f.d0, DATE '2017-12-01')                       AS 此后还剩几天可观察,
    COUNT(DISTINCT CASE WHEN b.dt > f.d0 THEN f.user_id END)        AS 之后又买过的人,
    ROUND(COUNT(DISTINCT CASE WHEN b.dt > f.d0 THEN f.user_id END)
          * 100.0 / COUNT(DISTINCT f.user_id), 2)                   AS 回购率
FROM firstbuy f
LEFT JOIN buyd b ON b.user_id = f.user_id
GROUP BY f.d0
ORDER BY f.d0;

-- 结果5：跨天回购的人 vs 只在一天买过的人，差在哪
WITH buyd AS (
    SELECT user_id, COUNT(DISTINCT dt) AS days
    FROM events
    WHERE behavior = 'buy' AND dt <= DATE '2017-12-01'
    GROUP BY user_id
),
grp AS (
    SELECT user_id,
           CASE WHEN days >= 2 THEN '跨天回购' ELSE '只在一天买过' END AS 分组
    FROM buyd
),
buyev AS (
    SELECT user_id,
           COUNT(*)                     AS 购买事件数,
           COUNT(DISTINCT item_id)      AS 买过的商品数,
           COUNT(DISTINCT category_id)  AS 买过的类目数
    FROM events
    WHERE behavior = 'buy' AND dt <= DATE '2017-12-01'
    GROUP BY user_id
)
SELECT
    g.分组,
    COUNT(DISTINCT g.user_id)                                       AS 人数,
    ROUND(AVG(e.购买事件数), 2)                                     AS 人均购买事件,
    ROUND(AVG(e.买过的商品数), 2)                                   AS 人均买过的商品数,
    ROUND(AVG(e.买过的类目数), 2)                                   AS 人均买过的类目数
FROM grp g
JOIN buyev e ON e.user_id = g.user_id
GROUP BY 1
ORDER BY 1;

-- 结果6：有没有人重复买同一个商品（真·单品复购）
WITH same_item AS (
    SELECT user_id, item_id, COUNT(DISTINCT dt) AS d
    FROM events
    WHERE behavior = 'buy' AND dt <= DATE '2017-12-01'
    GROUP BY user_id, item_id
)
SELECT
    (SELECT COUNT(*) FROM same_item)                                AS 人去重后的购买商品对数,
    COUNT(*) FILTER (WHERE d >= 2)                                  AS 跨天重复买过同一商品的,
    ROUND(COUNT(*) FILTER (WHERE d >= 2) * 100.0
          / (SELECT COUNT(*) FROM same_item), 2)                    AS 占比
FROM same_item;
