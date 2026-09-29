-- ============================================================
-- S2 · 交易漏斗主线（本项目的核心）
-- 业务问题：从"逛"到"买"，人到底丢在哪一步？运营该在哪一步使劲？
--
-- 口径（重要，曾经算错过）：
--   1) 一律按【去重人数】算——一个用户刷 100 次浏览也只是 1 个人，
--      用次数算会被少数重度用户把比率拉偏。
--   2) 漏斗必须【严格嵌套】：下一层的人一定是上一步的人的子集。
--      否则会算出 >100% 的"转化率"这种不可能的数字。
--      · 收藏 / 加购 是【并联】的两条意向路径，不是串联层级，不能串成一条链；
--      · 买的人里有相当一部分从没加过购物车（直接购买），
--        所以"购买人数 ÷ 加购人数"不是"加购到购买率"。
-- ============================================================

-- 结果1：人数漏斗各级（严格嵌套）
WITH u AS (
    SELECT
        user_id,
        MAX(CASE WHEN behavior = 'pv'   THEN 1 ELSE 0 END) AS has_pv,
        MAX(CASE WHEN behavior = 'fav'  THEN 1 ELSE 0 END) AS has_fav,
        MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS has_cart,
        MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS has_buy
    FROM events
    GROUP BY user_id
)
SELECT
    COUNT(*)     AS 总用户,
    SUM(has_pv)  AS 浏览人数,
    SUM(has_cart) AS 加购人数,
    SUM(CASE WHEN has_cart = 1 AND has_buy = 1 THEN 1 ELSE 0 END) AS 加购且购买,
    SUM(has_buy) AS 购买人数_全路径
FROM u;

-- 结果2：嵌套转化率（分母是上一步的人数，分子是上一步的人里走到下一步的）
WITH u AS (
    SELECT
        user_id,
        MAX(CASE WHEN behavior = 'pv'   THEN 1 ELSE 0 END) AS has_pv,
        MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS has_cart,
        MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS has_buy
    FROM events
    GROUP BY user_id
)
SELECT
    ROUND(SUM(has_cart) * 100.0 / SUM(has_pv), 2) AS 浏览到加购率,
    ROUND(SUM(CASE WHEN has_cart = 1 AND has_buy = 1 THEN 1 ELSE 0 END) * 100.0
          / SUM(has_cart), 2)                     AS 加购到购买率,
    ROUND(SUM(has_buy) * 100.0 / SUM(has_pv), 2)  AS 浏览到购买率_全路径
FROM u;

-- 结果3：路径拆解——买的人是怎么走到购买的
WITH u AS (
    SELECT
        user_id,
        MAX(CASE WHEN behavior = 'fav'  THEN 1 ELSE 0 END) AS has_fav,
        MAX(CASE WHEN behavior = 'cart' THEN 1 ELSE 0 END) AS has_cart,
        MAX(CASE WHEN behavior = 'buy'  THEN 1 ELSE 0 END) AS has_buy
    FROM events
    GROUP BY user_id
)
SELECT
    SUM(CASE WHEN has_cart = 1 AND has_buy = 1 THEN 1 ELSE 0 END) AS 加购且购买,
    SUM(CASE WHEN has_cart = 1 AND has_buy = 0 THEN 1 ELSE 0 END) AS 加购未购买,
    SUM(CASE WHEN has_cart = 0 AND has_buy = 1 THEN 1 ELSE 0 END) AS 未加购直接购买,
    SUM(CASE WHEN has_buy = 1 THEN 1 ELSE 0 END)                  AS 购买总数,
    ROUND(SUM(CASE WHEN has_buy = 1 AND has_cart = 1 THEN 1 ELSE 0 END) * 100.0
          / SUM(CASE WHEN has_buy = 1 THEN 1 ELSE 0 END), 2)      AS 购买者中加购过的占比,
    ROUND(SUM(CASE WHEN has_buy = 1 AND has_fav = 1 THEN 1 ELSE 0 END) * 100.0
          / SUM(CASE WHEN has_buy = 1 THEN 1 ELSE 0 END), 2)      AS 购买者中收藏过的占比
FROM u;

-- 结果4（深水区）：商品级加购成交率
-- 上面都是"人"的口径。真正尖锐的问题是：放进购物车的【这个商品】，最后买了吗？
-- 用 (用户, 商品) 配对来算，比人的口径严格得多。
-- 同时给一个放宽口径：买了"同类目"的东西也算——用来排除
-- "同款不同颜色是不同 item_id"这个解释（如果放宽后猛涨，说明只是 SKU 口径问题）
WITH cart_items AS (
    SELECT DISTINCT user_id, item_id, category_id FROM events WHERE behavior = 'cart'
),
buy_items AS (
    SELECT DISTINCT user_id, item_id FROM events WHERE behavior = 'buy'
),
buy_cats AS (
    SELECT DISTINCT user_id, category_id FROM events WHERE behavior = 'buy'
)
SELECT
    (SELECT COUNT(*) FROM cart_items) AS 加购商品项数,
    (SELECT COUNT(*) FROM cart_items c JOIN buy_items b
        ON c.user_id = b.user_id AND c.item_id = b.item_id) AS 买了同款,
    ROUND((SELECT COUNT(*) FROM cart_items c JOIN buy_items b
        ON c.user_id = b.user_id AND c.item_id = b.item_id) * 100.0
        / (SELECT COUNT(*) FROM cart_items), 2) AS 同款成交率,
    (SELECT COUNT(*) FROM cart_items c JOIN buy_cats b
        ON c.user_id = b.user_id AND c.category_id = b.category_id) AS 买了同款或同类目,
    ROUND((SELECT COUNT(*) FROM cart_items c JOIN buy_cats b
        ON c.user_id = b.user_id AND c.category_id = b.category_id) * 100.0
        / (SELECT COUNT(*) FROM cart_items), 2) AS 同类目口径成交率
;

-- 结果5（深水区）：人级视角——加购的人里，有多少买回了自己加过的商品
-- 和"加购到购买率 71.87%"对着看：
-- 71.87% 说的是"加购的人最终买了东西"，这个说的是"买的是不是自己加购的那些"
WITH c AS (
    SELECT DISTINCT user_id, item_id FROM events WHERE behavior = 'cart'
),
b AS (
    SELECT DISTINCT user_id, item_id FROM events WHERE behavior = 'buy'
)
SELECT
    (SELECT COUNT(DISTINCT user_id) FROM c) AS 加购人数,
    (SELECT COUNT(DISTINCT c.user_id) FROM c JOIN b
        ON c.user_id = b.user_id AND c.item_id = b.item_id) AS 买回自己加购过的人,
    ROUND((SELECT COUNT(DISTINCT c.user_id) FROM c JOIN b
        ON c.user_id = b.user_id AND c.item_id = b.item_id) * 100.0
        / (SELECT COUNT(DISTINCT user_id) FROM c), 2) AS 加购者买回率
;

-- 结果6（稳健性检验，不可省）：窗口截断检验
-- 数据只有 9 天，越晚加购的商品"剩余可购买时间"越短，成交率自然越低。
-- 若成交率随加购日期单调下降，说明 6.47% 被窗口截断压低了，真实值应取前几天。
WITH c AS (
    SELECT DISTINCT user_id, item_id, dt FROM events WHERE behavior = 'cart'
),
b AS (
    SELECT DISTINCT user_id, item_id FROM events WHERE behavior = 'buy'
)
SELECT
    c.dt AS 加购日期,
    COUNT(*) AS 加购项数,
    ROUND(SUM(CASE WHEN EXISTS (SELECT 1 FROM b
        WHERE b.user_id = c.user_id AND b.item_id = c.item_id)
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 同款成交率
FROM c
GROUP BY c.dt
ORDER BY c.dt
;
