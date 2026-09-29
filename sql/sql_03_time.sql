-- ============================================================
-- S3 · 时间规律（小时 / 星期 / 12-02 跳涨下钻）
-- 业务问题：用户什么时候最想买？运营动作该排几点？
--
-- 口径提示（重要）：
--   下面按小时分组里的"活跃用户数"，指的是【9 天里在这个时段出现过的人】，
--   同一个人在不同天都出现在 20 点，只算 1 次。所以它不是"某一天这个时段的人数"，
--   24 个小时加起来会远大于 99,020。这个口径适合回答"谁会在这个时段出现"，
--   不适合回答"总量"。要看量，请用 S1 的每日概览。
-- ============================================================

-- 结果1：全站 24 小时形态（几点人最多）
SELECT
    hr                                                 AS 小时,
    COUNT(*)                                           AS 行为行数,
    COUNT(DISTINCT user_id)                            AS 该时段出现过的用户数,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_id), 2) AS 人均行为数
FROM events
GROUP BY hr
ORDER BY hr;

-- 结果2：小时 × 行为——看"逛"的高峰和"买"的高峰是不是同一个时段
SELECT
    hr                                                            AS 小时,
    COUNT(DISTINCT CASE WHEN behavior = 'pv'   THEN user_id END)  AS 浏览人数,
    COUNT(DISTINCT CASE WHEN behavior = 'cart' THEN user_id END)  AS 加购人数,
    COUNT(DISTINCT CASE WHEN behavior = 'fav'  THEN user_id END)  AS 收藏人数,
    COUNT(DISTINCT CASE WHEN behavior = 'buy'  THEN user_id END)  AS 购买人数
FROM events
GROUP BY hr
ORDER BY hr;

-- 结果3：该时段"来的人有多想买"——购买人数占该时段活跃人数的比
-- 这是 S3 的落点：找的不是"人最多的时段"，而是"动机最强的时段"
--
-- 最后一列是本节的钥匙：在【已经加购的人】里，有多少最终也买了。
-- 如果某时段这一列明显偏低，说明那个时段的人"加购了但不买"——
-- 那正是 S2 说的"购物车是比价清单而非待付款清单"的时间维度证据。
SELECT
    hr                                                            AS 小时,
    COUNT(DISTINCT user_id)                                       AS 活跃用户数,
    COUNT(DISTINCT CASE WHEN behavior = 'buy' THEN user_id END)   AS 购买人数,
    ROUND(COUNT(DISTINCT CASE WHEN behavior = 'buy' THEN user_id END) * 100.0
          / COUNT(DISTINCT user_id), 2)                           AS 该时段购买渗透率,
    ROUND(COUNT(DISTINCT CASE WHEN behavior = 'cart' THEN user_id END) * 100.0
          / COUNT(DISTINCT user_id), 2)                           AS 该时段加购渗透率,
    ROUND(COUNT(DISTINCT CASE WHEN behavior = 'buy' THEN user_id END) * 100.0
          / COUNT(DISTINCT CASE WHEN behavior = 'cart' THEN user_id END), 2)
                                                                  AS 加购者中的购买率
FROM events
GROUP BY hr
ORDER BY hr;

-- 结果4（下钻）：12-02 那次跳涨，逐小时长什么样
-- 关键看法：活动通常有明确的起止时点（某个小时突然翘起来）；
-- 如果只是整体等比例抬高、没有突变点，那更像渠道引流而不是限时活动
SELECT
    hr                                                              AS 小时,
    COUNT(DISTINCT CASE WHEN dt = DATE '2017-11-25' THEN user_id END) AS 周六_1125,
    COUNT(DISTINCT CASE WHEN dt = DATE '2017-11-26' THEN user_id END) AS 周日_1126,
    COUNT(DISTINCT CASE WHEN dt = DATE '2017-12-02' THEN user_id END) AS 周六_1202,
    COUNT(DISTINCT CASE WHEN dt = DATE '2017-12-03' THEN user_id END) AS 周日_1203
FROM events
GROUP BY hr
ORDER BY hr;

-- 结果5（下钻）：跳涨的人是"新面孔"还是"老用户变活跃"
-- 判据：当日活跃用户里，有多少是这 9 天窗口中此前从没出现过的
-- 注意：11-25 必然 100%（它是窗口第一天，所有人都"第一次出现"），所以从 11-26 开始看
WITH first_seen AS (
    SELECT user_id, MIN(dt) AS 首次出现日
    FROM events
    GROUP BY user_id
)
SELECT
    e.dt                                                       AS 日期,
    COUNT(DISTINCT e.user_id)                                  AS 当日活跃用户,
    COUNT(DISTINCT CASE WHEN f.首次出现日 = e.dt THEN e.user_id END) AS 窗口内首次出现,
    ROUND(COUNT(DISTINCT CASE WHEN f.首次出现日 = e.dt THEN e.user_id END)
          * 100.0 / COUNT(DISTINCT e.user_id), 2)              AS 新面孔占比
FROM events e
JOIN first_seen f ON e.user_id = f.user_id
GROUP BY e.dt
ORDER BY e.dt;
