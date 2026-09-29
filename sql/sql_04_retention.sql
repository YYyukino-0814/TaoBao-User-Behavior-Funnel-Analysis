-- ============================================================
-- S4 · 日活留存（代理口径）
-- 业务问题：来逛过的人，过几天还会不会来？
--
-- ⚠️ 两条必须先读的口径警告，否则这一节会讲错：
--
-- 1) 数据集没有注册时间、没有首访时间，只能用"在观察窗口内第一次出现"
--    冒充"新用户"。后果：11-25（窗口第一天）把所有本来就已经存在的老用户
--    全算成"新用户"——首批队列被严重注水。
--    所以本节一律说【回访率】，不说"新客留存"。
--
-- 2) 12-02 / 12-03 两天有异常：全体 99,020 个用户里，这两天各有约 97,000 人
--    活跃（98%+），而前 7 天稳定在 72~75%。这是断崖式跳变，不像真实业务。
--    见结果4。这两天的数据会把任何"第 N 天回访"彻底污染
--    （第一版没排除，算出 11-25 队列的 D7 = 98.54% > D1 = 78.77%，不可能）。
--    因此本节的观察窗口一律截止到 2017-12-01。
-- ============================================================

-- 结果1：回访矩阵（观察窗 11-25 ~ 12-01）
-- 不可观察的格子返回 NULL，不是 0 —— 0 的意思是"一个都没回来"，两回事
WITH first_seen AS (
    SELECT user_id, MIN(dt) AS cohort
    FROM events
    GROUP BY user_id
),
act AS (
    SELECT DISTINCT user_id, dt FROM events WHERE dt <= DATE '2017-12-01'
)
SELECT
    f.cohort                          AS 首次出现日,
    COUNT(DISTINCT f.user_id)         AS 队列人数,
    CASE WHEN f.cohort + 1 <= DATE '2017-12-01' THEN
        ROUND(COUNT(DISTINCT CASE WHEN a.dt = f.cohort + 1 THEN a.user_id END)
              * 100.0 / COUNT(DISTINCT f.user_id), 2) END AS D1,
    CASE WHEN f.cohort + 2 <= DATE '2017-12-01' THEN
        ROUND(COUNT(DISTINCT CASE WHEN a.dt = f.cohort + 2 THEN a.user_id END)
              * 100.0 / COUNT(DISTINCT f.user_id), 2) END AS D2,
    CASE WHEN f.cohort + 3 <= DATE '2017-12-01' THEN
        ROUND(COUNT(DISTINCT CASE WHEN a.dt = f.cohort + 3 THEN a.user_id END)
              * 100.0 / COUNT(DISTINCT f.user_id), 2) END AS D3
FROM first_seen f
LEFT JOIN act a ON a.user_id = f.user_id
GROUP BY f.cohort
ORDER BY f.cohort;

-- 结果2：合并回访曲线（只取能完整观察到 D3 的队列：首次出现日 <= 11-28）
WITH first_seen AS (
    SELECT user_id, MIN(dt) AS cohort
    FROM events
    GROUP BY user_id
    HAVING MIN(dt) <= DATE '2017-11-28'
),
act AS (
    SELECT DISTINCT user_id, dt FROM events WHERE dt <= DATE '2017-12-01'
)
SELECT
    g.n                                                             AS 距离首次出现的天数,
    COUNT(DISTINCT f.user_id)                                       AS 队列人数合计,
    ROUND(COUNT(DISTINCT CASE WHEN a.dt = f.cohort + g.n THEN a.user_id END)
          * 100.0 / COUNT(DISTINCT f.user_id), 2)                   AS 回访率
FROM first_seen f
CROSS JOIN (SELECT UNNEST([1, 2, 3]) AS n) g
LEFT JOIN act a ON a.user_id = f.user_id
GROUP BY g.n
ORDER BY g.n;

-- 结果3：首次出现那天的行为，会不会影响后来的回访
-- 这是本节唯一可能开出运营动作的结论
WITH first_seen AS (
    SELECT user_id, MIN(dt) AS cohort
    FROM events
    GROUP BY user_id
    HAVING MIN(dt) <= DATE '2017-11-28'
),
grp AS (
    SELECT f.user_id, f.cohort,
           MAX(CASE WHEN e.behavior = 'cart' THEN 1 ELSE 0 END) AS 首日加购
    FROM first_seen f
    JOIN events e ON e.user_id = f.user_id AND e.dt = f.cohort
    GROUP BY f.user_id, f.cohort
),
act AS (
    SELECT DISTINCT user_id, dt FROM events WHERE dt <= DATE '2017-12-01'
)
SELECT
    CASE WHEN g.首日加购 = 1 THEN '首日有加购' ELSE '首日只浏览' END  AS 分组,
    COUNT(DISTINCT g.user_id)                                       AS 人数,
    ROUND(COUNT(DISTINCT CASE WHEN a.dt = g.cohort + 1 THEN a.user_id END)
          * 100.0 / COUNT(DISTINCT g.user_id), 2)                   AS D1回访率,
    ROUND(COUNT(DISTINCT CASE WHEN a.dt = g.cohort + 3 THEN a.user_id END)
          * 100.0 / COUNT(DISTINCT g.user_id), 2)                   AS D3回访率,
    ROUND(COUNT(DISTINCT CASE WHEN a.dt >= g.cohort + 1
                               AND a.dt <= g.cohort + 3 THEN a.user_id END)
          * 100.0 / COUNT(DISTINCT g.user_id), 2)                   AS 三天内至少回访一次
FROM grp g
LEFT JOIN act a ON a.user_id = g.user_id
GROUP BY 1
ORDER BY 分组;

-- 结果4（关键佐证）：每日活跃用户占全体用户的比例
-- 前 7 天稳定在 72~75%，12-02/12-03 突然到 98% —— 这就是上面说的异常
SELECT
    dt                                                              AS 日期,
    COUNT(DISTINCT user_id)                                         AS 当日活跃用户,
    (SELECT COUNT(DISTINCT user_id) FROM events)                     AS 全体用户,
    ROUND(COUNT(DISTINCT user_id) * 100.0
          / (SELECT COUNT(DISTINCT user_id) FROM events), 2)        AS 当日活跃覆盖率
FROM events
GROUP BY dt
ORDER BY dt;

-- 结果5：每个用户这 9 天里活跃了几天（解释为什么"回访率"这么高）
SELECT
    n                                                               AS 活跃天数,
    COUNT(*)                                                        AS 人数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS 占比
FROM (
    SELECT user_id, COUNT(DISTINCT dt) AS n FROM events GROUP BY user_id
)
GROUP BY n
ORDER BY n;
