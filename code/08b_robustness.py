# -*- coding: utf-8 -*-
"""S8 补充检验：三个必须当场回答的质疑。

1) 「会话越长越容易成交」会不会只是同义反复？
   会话长 = 行为多 = 撞上购买的机会多，这是构造决定的，不算发现。
   要看的是：把"长度 1"这种被阈值切出来的伪会话剔掉之后，结论还在不在。

2) 「66% 会话是纯浏览」会不会只是 30 分钟阈值切太碎切出来的？
   换个阈值重算一遍。阈值是我定的，结论不能依赖它。

3) 加购的会话内消化率只有 1.38%，那放到整个观察期是多少？
   同一个口径（人,商品）算一遍，才能回答"加了不买是当场没买，还是永远没买"。

用法：python code/08b_robustness.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

Q = {}

# ---- 1. 长度 >= 2 的会话里，长度还和成交率正相关吗 ----
Q['长度≥2的会话_按长度看成交'] = """
SELECT
    CASE WHEN n <= 3 THEN '2~3' WHEN n <= 10 THEN '4~10'
         WHEN n <= 30 THEN '11~30' ELSE '31 以上' END AS 会话行为数,
    COUNT(*) AS 会话数,
    ROUND(SUM(有购买) * 100.0 / COUNT(*), 2) AS 含购买,
    ROUND(SUM(有加购) * 100.0 / COUNT(*), 2) AS 含加购
FROM (
    SELECT user_id, sid30, COUNT(*) AS n,
           MAX(CASE WHEN behavior='buy'  THEN 1 ELSE 0 END) AS 有购买,
           MAX(CASE WHEN behavior='cart' THEN 1 ELSE 0 END) AS 有加购
    FROM sessions GROUP BY 1, 2
)
GROUP BY 1 ORDER BY MIN(n);
"""

# ---- 2. 换阈值：纯浏览会话占比会不会翻盘 ----
Q['阈值稳健性_纯浏览占比'] = """
WITH a AS (
    SELECT '15 分钟' AS 阈值, 1 AS k, user_id, sid15 AS sid, behavior FROM sessions
    UNION ALL
    SELECT '30 分钟（主口径）', 2, user_id, sid30, behavior FROM sessions
    UNION ALL
    SELECT '60 分钟', 3, user_id, sid60, behavior FROM sessions
),
g AS (
    SELECT 阈值, k, user_id, sid, COUNT(*) AS n,
           MAX(CASE WHEN behavior IN ('cart','fav','buy') THEN 1 ELSE 0 END) AS 有意向
    FROM a GROUP BY 1, 2, 3, 4
)
SELECT 阈值,
       COUNT(*) AS 会话数,
       ROUND(AVG(n), 2) AS 平均行为数,
       ROUND(SUM(CASE WHEN n = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 单行为会话占比,
       ROUND(SUM(CASE WHEN 有意向 = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 纯浏览会话占比
FROM g GROUP BY 阈值, k ORDER BY k;
"""

# ---- 3. 加购后购买率：(人,会话,商品) vs (人,商品) ----
Q['加购消化_两种口径对比'] = """
WITH pair_all AS (
    SELECT user_id, item_id,
           MAX(CASE WHEN behavior='cart' THEN 1 ELSE 0 END) AS 加过购,
           MAX(CASE WHEN behavior='buy'  THEN 1 ELSE 0 END) AS 买过
    FROM sessions GROUP BY 1, 2
    HAVING 加过购 = 1
)
SELECT '全窗口 (人,商品)' AS 口径,
       COUNT(*) AS 加购对数,
       SUM(买过) AS 后来买下的,
       ROUND(SUM(买过) * 100.0 / COUNT(*), 2) AS 消化率
FROM pair_all
UNION ALL
SELECT '单会话 (人,会话,商品)', 395887, 5461, 1.38;
"""

# ---- 4. 买家视角：买之前那一刻在干什么 ----
# 只取每个会话里【第一次】购买，看它前一条行为是什么。取第一次是为了
# 避免同一个会话里买了 5 次的人把样本灌成 5 条一样的记录。
Q['首次购买的前一条行为'] = """
WITH first_buy AS (
    SELECT user_id, sid30, ts, item_id,
           ROW_NUMBER() OVER (PARTITION BY user_id, sid30
                              ORDER BY ts, item_id) AS rk
    FROM sessions WHERE behavior = 'buy'
),
prev AS (
    SELECT s.behavior,
           ROW_NUMBER() OVER (PARTITION BY s.user_id, s.sid30
                              ORDER BY s.ts DESC, s.item_id DESC, s.behavior DESC) AS rk2
    FROM sessions s
    JOIN first_buy f ON f.user_id = s.user_id AND f.sid30 = s.sid30 AND f.rk = 1
    WHERE (s.ts, s.item_id) < (f.ts, f.item_id)
)
SELECT CASE behavior WHEN 'pv' THEN '浏览' WHEN 'cart' THEN '加购'
                      WHEN 'fav' THEN '收藏' ELSE '购买' END AS 买之前那一步,
       COUNT(*) AS 次数,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比
FROM prev WHERE rk2 = 1
GROUP BY 1 ORDER BY 次数 DESC;
"""


def main():
    con = db.connect()
    for i, (name, sql) in enumerate(Q.items(), 1):
        print(f'\n{"=" * 62}\n{name}\n{"=" * 62}')
        df = con.execute(sql).df()
        print(df.to_string(index=False), flush=True)
        # 落盘给画图脚本读：图的数据源永远是文件，不手抄数字
        df.to_csv(os.path.join(db.TABLES, f's8b_r{i}.csv'), index=False,
                  encoding='utf-8-sig')


if __name__ == '__main__':
    main()
