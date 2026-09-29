-- ============================================================
-- S9 · 加购未成交召回 + 机会量化（深水区）
-- 业务问题：加了购物车却没买的那批人，值不值得捞？捞得回来多少？
--
-- ⚠️ 这一节最重要的一条纪律：【这份数据没有金额字段】。
--    所以整个测算只用"件数"和"人数"，绝不乘客单价、绝不给 GMV。
--    任何看起来像"能省 XXX 万元"的数字，在这份数据里都是编的。
--    测算的产出只到"能多成交多少件 / 触达多少人"。
--
-- ⚠️ 第二条：窗口只有 7 天（12-02/12-03 已剔除）。跨时间的指标
--    一律要检查窗口截断——越晚加购的，能观察到的时间越短。
--    「加购后一天内成交率」在所有加购日都算得出来，是安全的口径；
--    「加购后 7 天内成交率」只在 11-25 加购的那批上算得准。见结果2 和结果3。
--
-- ⚠️ 第三条：本节【买回】的定义比 S2/S8 严格 —— 要求购买发生在加购【之后】。
--    买在前、加在后不算"买回加购的商品"。
--    另外本节窗口剔掉了 12-02/12-03，S2 没有剔，所以本节的"加购人数 66,542"
--    小于 S2 报的 74,220 —— 差的那些只在 12-02/12-03 加过购。
--    【这两个数不能互相印证，也不同时引用。】
-- ============================================================

-- 结果1：沉默加购的盘子有多大
-- 口径：同一个人对同一个商品，七天内既加过购、又买了
WITH pair AS (
    SELECT user_id, item_id,
           MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS 加过购,
           MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS 买过
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
    HAVING 加过购 = 1
)
-- 注意人数那几列：【一个用户可以既有买回的件、也有沉默的件】，
-- 所以"有沉默件的人数"和"至少买回一件的人数"是【重叠】的，不能相加。
-- 只有"全部买回的人数"是从总数里减出来的，那个才是不重叠的。
SELECT
    COUNT(*)                                                        AS 加购商品对,
    SUM(买过)                                                       AS 七天内买下的,
    COUNT(*) - SUM(买过)                                            AS 沉默加购对,
    ROUND((COUNT(*) - SUM(买过)) * 100.0 / COUNT(*), 2)             AS 沉默占比,
    COUNT(DISTINCT user_id)                                         AS 加购人数,
    COUNT(DISTINCT CASE WHEN 买过 = 0 THEN user_id END)             AS 有沉默件的人数,
    COUNT(DISTINCT CASE WHEN 买过 = 1 THEN user_id END)             AS 至少买回一件的人数,
    COUNT(DISTINCT user_id)
      - COUNT(DISTINCT CASE WHEN 买过 = 0 THEN user_id END)         AS 全部买回的人数
FROM pair;

-- 结果2：加购到购买隔了多久（累计口径）
-- 「买回」严格定义为：购买发生在加购【之后】。买在前、加在后不算。
WITH f AS (
    SELECT user_id, item_id,
           MIN(CASE WHEN behavior = 'cart' THEN ts END) AS 加购时间,
           MIN(CASE WHEN behavior = 'buy'  THEN ts END) AS 购买时间
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
    HAVING 加购时间 IS NOT NULL AND 购买时间 IS NOT NULL
       AND 购买时间 >= 加购时间
)
SELECT
    CASE WHEN d <  3600   THEN '1 小时内'
         WHEN d < 21600   THEN '1~6 小时'
         WHEN d < 86400   THEN '6~24 小时'
         WHEN d < 259200  THEN '1~3 天'
         WHEN d < 432000  THEN '3~5 天'
         ELSE '5~7 天' END                                          AS 加购到购买,
    COUNT(*)                                                        AS 对数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS 区间占比,
    ROUND(SUM(COUNT(*)) OVER (ORDER BY MIN(d)) * 100.0
          / SUM(COUNT(*)) OVER (), 2)                               AS 累计占比
FROM (SELECT *, 购买时间 - 加购时间 AS d FROM f)
GROUP BY 1
ORDER BY MIN(d);

-- 结果3：窗口截断检验 —— 24 小时口径 vs 7 天口径，按加购日拆开
-- 越晚加购的，能观察到的时间越短，7 天口径会被系统性低估。
WITH f AS (
    SELECT user_id, item_id,
           MIN(CASE WHEN behavior = 'cart' THEN ts END) AS 加购时间,
           MIN(CASE WHEN behavior = 'cart' THEN dt END) AS 加购日,
           MIN(CASE WHEN behavior = 'buy'  THEN ts END) AS 购买时间
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
    HAVING 加购时间 IS NOT NULL
)
SELECT
    加购日,
    COUNT(*)                                                        AS 加购对数,
    DATE '2017-12-01' - 加购日                                      AS 剩余可观察天数,
    -- 别名不能以数字开头，"24小时内成交率"会被 DuckDB 当成语法错误
    ROUND(SUM(CASE WHEN 购买时间 - 加购时间 < 3600
                   THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)        AS 一小时内成交率,
    ROUND(SUM(CASE WHEN 购买时间 - 加购时间 < 86400
                   THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)        AS 一天内成交率,
    ROUND(SUM(CASE WHEN 购买时间 >= 加购时间
                   THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)        AS 窗口内成交率
FROM f
GROUP BY 1
ORDER BY 1;

-- 结果4：这批人还回得来吗 —— 决定"站内召回"是不是可行
--
-- ⚠️ 这是【下界】，不是准确值。条件是"最后一次加购之后还在站内出现过"，
--    而窗口末端（12-01）加购的人根本没时间回来，被算进了"没回来"。
--    真实的可触达比例只会比这个数【更高】。
--    另外这个条件很松：加购后隔一分钟再点一次也算"回来过"。
--    它回答的是"站内有没有机会触达"，不是"触达了会不会看"。
WITH last_cart AS (
    SELECT user_id, MAX(ts) AS 最后一次加购时间
    FROM events WHERE dt <= DATE '2017-12-01' AND behavior = 'cart'
    GROUP BY 1
)
SELECT
    COUNT(*)                                                        AS 加购人数,
    SUM(CASE WHEN 之后还活跃 THEN 1 ELSE 0 END)                     AS 加购之后还回来过,
    ROUND(SUM(CASE WHEN 之后还活跃 THEN 1 ELSE 0 END) * 100.0
          / COUNT(*), 2)                                            AS 站内可触达占比
FROM (
    SELECT l.user_id,
           MAX(CASE WHEN e.ts > l.最后一次加购时间 THEN 1 ELSE 0 END) AS 之后还活跃
    FROM last_cart l
    JOIN events e ON e.user_id = l.user_id
    WHERE e.dt <= DATE '2017-12-01'
    GROUP BY 1
);

-- 结果5：沉默加购对象长什么样 —— 按"沉默件数"分层，看召回价值
-- 一个人加了很多件都没买，和只加了一件没买，不是一回事。
WITH pair AS (
    SELECT user_id, item_id,
           MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS 加过购,
           MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS 买过
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
    HAVING 加过购 = 1
),
per_user AS (
    SELECT user_id,
           COUNT(*)              AS 加购件数,
           SUM(1 - 买过)         AS 沉默件数,
           SUM(买过)             AS 买回件数
    FROM pair GROUP BY 1
)
SELECT
    CASE WHEN 沉默件数 = 0  THEN 'A 全部买回'
         WHEN 沉默件数 = 1  THEN 'B 沉默 1 件'
         WHEN 沉默件数 <= 3 THEN 'C 沉默 2~3 件'
         ELSE 'D 沉默 4 件以上' END                                  AS 分层,
    COUNT(*)                                                        AS 人数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)              AS 人数占比,
    SUM(沉默件数)                                                   AS 沉默件数合计,
    ROUND(SUM(沉默件数) * 100.0
          / SUM(SUM(沉默件数)) OVER (), 2)                          AS 沉默件数占比
FROM per_user
GROUP BY 1
ORDER BY 1;

-- 结果6：机会量化 —— 三档情景
--
-- ⚠️⚠️ 这张表是【算术换算器】，不是【预测】。⚠️⚠️
--    三个提升幅度（5 / 10 / 20 个百分点）是我【拍】的，不是数据算出来的。
--    这份数据里没有实验、没有对照组，【我无法验证任何一个提升率】。
--    它的唯一作用是回答："如果召回能把沉默加购的成交率提到 X，
--    对应多少件成交" —— 把问题变成可以坐下来谈的算术。
--
--    要拿到真实提升率，只有一条路：做 A/B 实验。这是本节的结论，不是局限。
--
-- 参照锚（用来判断哪一档现实）：
--   沉默加购件当前的成交率 = 0%（定义如此）
--   全部加购件当前的成交率 = 6.21%（24,155 / 389,170）
--   观察最充分的 11-25 批次，窗口内成交率 = 7.85%
--   所以"A 档 5%"相当于把沉默组拉到接近总体平均；
--   "C 档 20%"是总体平均的三倍多，【不现实，列出来只是说明上限在哪】。
WITH pair AS (
    SELECT user_id, item_id,
           MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS 加过购,
           MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS 买过
    FROM events WHERE dt <= DATE '2017-12-01'
    GROUP BY 1, 2
    HAVING 加过购 = 1
),
base AS (
    SELECT COUNT(*) AS 总加购件, SUM(买过) AS 已成交件,
           COUNT(*) - SUM(买过) AS 沉默件数
    FROM pair
)
SELECT '保守' AS 情景, '沉默组成交率 0 → 5%' AS 假设,
       ROUND(沉默件数 * 0.05, 0) AS 多成交件数,
       ROUND((已成交件 + 沉默件数 * 0.05) * 100.0 / 总加购件, 2) AS 提升后整体加购成交率,
       '接近总体平均 6.21%，属于"够得着"的目标' AS 现实性判断
FROM base
UNION ALL SELECT '中性', '0 → 10%', ROUND(沉默件数 * 0.10, 0),
       ROUND((已成交件 + 沉默件数 * 0.10) * 100.0 / 总加购件, 2),
       '明显高于总体平均，需要很强的触达和权益' FROM base
UNION ALL SELECT '乐观', '0 → 20%', ROUND(沉默件数 * 0.20, 0),
       ROUND((已成交件 + 沉默件数 * 0.20) * 100.0 / 总加购件, 2),
       '总体平均的三倍多，现实中基本达不到，只为说明上限' FROM base
UNION ALL SELECT '基准', '不做任何召回', 0, ROUND(已成交件 * 100.0 / 总加购件, 2),
       '现状：389,170 件加购里 24,155 件在七天内成交' FROM base;
