-- ============================================================
-- S8 · 行为路径 / 序列分析（深水区）
-- 业务问题：一个人一次"逛"的过程长什么样？逛的过程中，什么动作之后最容易成交？
--
-- ⚠️ 运行前提：先跑 code/08_build_sessions.py 生成会话表。
-- 它会挂出视图 sessions（列：user_id, item_id, category_id, behavior,
-- timestamp, dt, sid15, sid30, sid60）。本节全部 FROM sessions。
--
-- ⚠️ 五条必须先读的口径警告，否则整节都站不住：
--
-- 1) 数据里【没有会话 ID】，会话是我自己造的。
--    定义：同一用户，相邻两条行为间隔超过 30 分钟 -> 新会话（sid30）。
--    30 分钟是行业惯例阈值，但是【我定的】，不是数据给的。
--    换阈值结论会不会变 -> 见结果7。
--
-- 2) 观察窗只有 7 天（12-02/12-03 已剔除）。
--    窗口最后的那个会话一定是被切断的，不是自然结束 ——
--    这会系统性低估长会话、也低估"会话内转化"。
--
-- 3) 排序键固定为 (ts, item_id, behavior)。时间戳只到秒，
--    同一秒内多条行为若只按 ts 排序，每次跑出来的路径顺序会不一样。
--
-- 4) 「会话内买了同一款」是 (人, 会话, 商品) 三元组的配对口径，
--    和 S2 的 (人, 商品) 口径不同，两个数不能直接比大小。
--
-- 5) 性能坑：结果4 那种"先全量 string_agg 再筛"的写法，120 万组 × 726 万行
--    跑 5 分钟都出不来。必须【先用会话长度把行数筛下来，再聚合】——改完 2.7 秒。
-- ============================================================

-- 结果1：会话规模
SELECT
    COUNT(DISTINCT (user_id, sid30))                                AS 会话总数,
    COUNT(DISTINCT user_id)                                         AS 有会话的用户数,
    ROUND(COUNT(DISTINCT (user_id, sid30)) * 1.0
          / COUNT(DISTINCT user_id), 2)                             AS 人均会话数,
    ROUND(AVG(n), 2)                                                AS 平均每会话行为数,
    ROUND(MEDIAN(n), 1)                                             AS 会话行为数中位数,
    ROUND(AVG(时长秒) / 60.0, 2)                                    AS 平均会话时长分钟,
    ROUND(MEDIAN(时长秒) / 60.0, 2)                                 AS 会话时长中位数分钟
FROM (
    SELECT user_id, sid30, COUNT(*) AS n, MAX(ts) - MIN(ts) AS 时长秒
    FROM sessions GROUP BY user_id, sid30
);

-- 结果2：会话内行为数的分布 —— 大部分人一次逛多久
SELECT
    CASE WHEN n = 1 THEN '1'
         WHEN n <= 3 THEN '2~3'
         WHEN n <= 10 THEN '4~10'
         WHEN n <= 30 THEN '11~30'
         WHEN n <= 100 THEN '31~100'
         ELSE '100 以上' END                                        AS 会话行为数,
    COUNT(*)                                                        AS 会话数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS 占比
FROM (SELECT user_id, sid30, COUNT(*) AS n FROM sessions GROUP BY 1, 2)
GROUP BY 1
ORDER BY MIN(n);

-- 结果3：会话以什么行为结束，以及这种结局的整场成交率
WITH last_act AS (
    SELECT user_id, sid30, behavior,
           ROW_NUMBER() OVER (PARTITION BY user_id, sid30
                              ORDER BY ts DESC, item_id DESC, behavior DESC) AS rk
    FROM sessions
),
sess_buy AS (
    SELECT user_id, sid30,
           MAX(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS 有购买
    FROM sessions GROUP BY 1, 2
)
SELECT
    CASE la.behavior WHEN 'pv' THEN '浏览' WHEN 'cart' THEN '加购'
                     WHEN 'fav' THEN '收藏' ELSE '购买' END        AS 最后一个动作,
    COUNT(*)                                                        AS 会话数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS 占比,
    ROUND(SUM(sb.有购买) * 100.0 / COUNT(*), 2)                     AS 该结局的整场成交率
FROM last_act la
JOIN sess_buy sb ON sb.user_id = la.user_id AND sb.sid30 = la.sid30
WHERE la.rk = 1
GROUP BY 1
ORDER BY 会话数 DESC;

-- 结果4（深水区重点）：一次"逛"到底做到哪一步
-- 按会话长度分组，看这个长度里有多少会话产生了意向动作 / 成交
WITH sess AS (
    SELECT user_id, sid30,
           COUNT(*) AS n,
           MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS 有购买,
           MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS 有加购,
           MAX(CASE WHEN behavior = 'fav'  THEN 1 ELSE 0 END) AS 有收藏
    FROM sessions GROUP BY 1, 2
)
SELECT
    CASE WHEN n = 1 THEN '1'
         WHEN n <= 3 THEN '2~3'
         WHEN n <= 10 THEN '4~10'
         WHEN n <= 30 THEN '11~30'
         ELSE '31 以上' END                                         AS 会话行为数,
    COUNT(*)                                                        AS 会话数,
    ROUND(SUM(CASE WHEN NOT 有加购 AND NOT 有收藏 AND NOT 有购买
                   THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)        AS 纯浏览无任何意向动作,
    ROUND(SUM(有加购) * 100.0 / COUNT(*), 2)                        AS 含加购,
    ROUND(SUM(CASE WHEN 有加购 OR 有收藏 THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                    AS 至少有加购或收藏,
    ROUND(SUM(有购买) * 100.0 / COUNT(*), 2)                        AS 含购买
FROM sess
GROUP BY 1
ORDER BY MIN(n);

-- 结果5：最常见的会话内行为序列（长度 4~6）
-- 行为编码：p=浏览 c=加购 f=收藏 b=购买
--
-- ⚠️ 这里【故意不给"成交率"列】。第一版算过一个，跑出来全是 0% 或 100%：
--    序列里有 b 就是 100%，没有就是 0%。它不是转化率，是"序列含不含 b"
--    的恒等式——和 S5 那张"回购用户特征表"是同一类错误（分组变量和结果
--    变量在构造上重叠），所以这次直接不产出这个数。
WITH len AS (
    SELECT user_id, sid30 FROM sessions GROUP BY 1, 2
    HAVING COUNT(*) BETWEEN 4 AND 6
),
seq AS (
    SELECT s.user_id, s.sid30,
           string_agg(substr(s.behavior, 1, 1), ''
                      ORDER BY s.ts, s.item_id, s.behavior) AS seq,
           COUNT(*) AS n
    FROM sessions s
    JOIN len L ON L.user_id = s.user_id AND L.sid30 = s.sid30
    GROUP BY 1, 2
)
SELECT
    seq                                                             AS 行为序列,
    n                                                               AS 序列长度,
    COUNT(*)                                                        AS 出现会话数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY n), 2) AS 占同长度会话比例,
    CASE WHEN seq = repeat('p', n) THEN '纯浏览' ELSE '含意向动作' END AS 类型
FROM seq
GROUP BY seq, n
ORDER BY 出现会话数 DESC
LIMIT 20;

-- 结果6（深水区重点）：加购当场能不能被消化掉
-- 直接回答 S2 遗留的问题：那些"加了购物车没买"的，是当场没买，还是永远没买
WITH cart_sess AS (
    SELECT user_id, sid30, item_id,
           MAX(CASE WHEN behavior = 'buy' THEN 1 ELSE 0 END) AS 同会话买了同款
    FROM sessions
    GROUP BY user_id, sid30, item_id
    HAVING MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) = 1
)
SELECT
    COUNT(*)                                                        AS 加购的会话商品对,
    SUM(同会话买了同款)                                             AS 同一会话内就买下的,
    ROUND(SUM(同会话买了同款) * 100.0 / COUNT(*), 2)                AS 会话内消化率
FROM cart_sess;

-- 结果7（稳健性）：换会话阈值，结论会不会变
-- 会话阈值是我定的，不是数据给的 —— 必须证明结论不依赖它
WITH s AS (
    SELECT
        COUNT(DISTINCT (user_id, sid15)) AS n15,
        COUNT(DISTINCT (user_id, sid30)) AS n30,
        COUNT(DISTINCT (user_id, sid60)) AS n60,
        COUNT(*)                         AS 行为总数
    FROM sessions
)
SELECT '15 分钟' AS 会话阈值, n15 AS 会话数,
       ROUND(行为总数 * 1.0 / n15, 2) AS 平均每会话行为数 FROM s
UNION ALL SELECT '30 分钟（主口径）', n30, ROUND(行为总数 * 1.0 / n30, 2) FROM s
UNION ALL SELECT '60 分钟', n60, ROUND(行为总数 * 1.0 / n60, 2) FROM s;
