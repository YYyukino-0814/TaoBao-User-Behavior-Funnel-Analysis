# -*- coding: utf-8 -*-
"""S8 补充之二：行为之间的转移概率。

为什么必须算这个：
  第一版我算的是「买之前那一步是什么」，跑出来 94.05% 是浏览。但浏览本来
  就占全部行为的九成（S1 的结论），所以任何一条行为的前一步大概率是浏览
  —— 这个数是被基础比例算出来的，不是发现。

  真正有信息量的问法是：站在某个动作上，下一步成交的条件概率是多少？
  再拿它和"随便站在哪个动作上，下一步成交的基础概率"比，看放大倍数。

用法：python code/08c_transitions.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

Q = {}

# ---- 1. 会话内一阶转移矩阵：当前动作 -> 下一个动作 ----
Q['会话内转移概率'] = """
WITH nx AS (
    SELECT behavior AS 当前,
           LEAD(behavior) OVER (PARTITION BY user_id, sid30
                                ORDER BY ts, item_id, behavior) AS 下一个
    FROM sessions
)
SELECT 当前,
       COUNT(*) AS 出现次数,
       -- 原始计数也带出来：画图脚本要拿它算"基础概率"，
       -- 不能用四舍五入过的百分比回推（那样算出来的数会有零点几个点的假误差）
       SUM(CASE WHEN 下一个='buy' THEN 1 ELSE 0 END) AS 下一步购买次数,
       ROUND(SUM(CASE WHEN 下一个='pv'   THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS 下一步浏览,
       ROUND(SUM(CASE WHEN 下一个='cart' THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS 下一步加购,
       ROUND(SUM(CASE WHEN 下一个='fav'  THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS 下一步收藏,
       ROUND(SUM(CASE WHEN 下一个='buy'  THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS 下一步购买,
       ROUND(SUM(CASE WHEN 下一个 IS NULL THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS 会话结束
FROM nx GROUP BY 当前 ORDER BY 当前;
"""

# ---- 2. 购买那一刻的分母到底是谁：会话里第一次购买之前有没有先逛 ----
Q['购买在会话中的位置'] = """
WITH fb AS (
    SELECT user_id, sid30, ts, item_id,
           ROW_NUMBER() OVER (PARTITION BY user_id, sid30 ORDER BY ts, item_id) AS rk,
           COUNT(*)     OVER (PARTITION BY user_id, sid30) AS 会话内购买次数,
           ROW_NUMBER() OVER (PARTITION BY user_id, sid30
                              ORDER BY ts, item_id) AS 位置序
    FROM sessions WHERE behavior='buy'
),
sz AS (SELECT user_id, sid30, COUNT(*) AS 会话长度 FROM sessions GROUP BY 1,2),
前 AS (
    SELECT s.user_id, s.sid30,
           MAX(CASE WHEN s.behavior='cart' THEN 1 ELSE 0 END) AS 购买前加过购,
           MAX(CASE WHEN s.behavior='fav'  THEN 1 ELSE 0 END) AS 购买前收藏过,
           MAX(CASE WHEN s.behavior='pv'   THEN 1 ELSE 0 END) AS 购买前浏览过
    FROM sessions s
    JOIN fb f ON f.user_id=s.user_id AND f.sid30=s.sid30 AND f.rk=1
    WHERE (s.ts, s.item_id) < (f.ts, f.item_id)
    GROUP BY 1, 2
)
SELECT
    CASE WHEN z.会话长度 = 1 THEN '整场只有一个动作：直接下单'
         WHEN p.购买前加过购 = 1 THEN '买之前先加过购'
         WHEN p.购买前收藏过 = 1 THEN '买之前先收藏过'
         WHEN p.购买前浏览过 = 1 THEN '买之前只浏览过'
         ELSE '其它' END AS 第一单之前发生了什么,
    COUNT(*) AS 会话数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比
FROM fb f
JOIN sz z ON z.user_id=f.user_id AND z.sid30=f.sid30
LEFT JOIN 前 p ON p.user_id=f.user_id AND p.sid30=f.sid30
WHERE f.rk = 1
GROUP BY 1 ORDER BY 会话数 DESC;
"""

# ---- 3. 加购转化的时间归属：当场 vs 事后 ----
Q['加购转化发生在当场还是事后'] = """
WITH pairs AS (
    SELECT user_id, item_id,
           MIN(CASE WHEN behavior='cart' THEN sid30 END) AS 加购会话,
           MIN(CASE WHEN behavior='buy'  THEN sid30 END) AS 购买会话
    FROM sessions GROUP BY 1, 2
    HAVING MIN(CASE WHEN behavior='cart' THEN sid30 END) IS NOT NULL
       AND MIN(CASE WHEN behavior='buy'  THEN sid30 END) IS NOT NULL
)
SELECT COUNT(*) AS 七天内买下的加购对,
       SUM(CASE WHEN 加购会话 = 购买会话 THEN 1 ELSE 0 END) AS 同一会话内买下,
       ROUND(SUM(CASE WHEN 加购会话 = 购买会话 THEN 1 ELSE 0 END)
             * 100.0 / COUNT(*), 2) AS 当场成交占比
FROM pairs;
"""


def main():
    con = db.connect()
    for i, (name, sql) in enumerate(Q.items(), 1):
        print(f'\n{"=" * 62}\n{name}\n{"=" * 62}')
        df = con.execute(sql).df()
        print(df.to_string(index=False), flush=True)
        df.to_csv(os.path.join(db.TABLES, f's8c_r{i}.csv'), index=False,
                  encoding='utf-8-sig')


if __name__ == '__main__':
    main()
