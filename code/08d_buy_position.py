# -*- coding: utf-8 -*-
"""S8 补充之三：把「买之前发生了什么」这一类数算干净。

第一版这里出过两个问题，都记在文档里：
  1) CASE 少写了一类（买是会话第一个动作、但后面还有别的行为），
     16.89% 落进了"其它"。
  2) 更要命的是：这类"进来第一件事就是下单"里，有多少是真直接下单，
     有多少是"先逛了半小时以上、被 30 分钟阈值切成两个会话"造成的假象？
     换三个阈值各算一遍，看这个比例会不会塌。

用法：python code/08d_buy_position.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db


def build(sid_col):
    return f"""
WITH fb AS (
    SELECT user_id, {sid_col} AS sid, ts, item_id,
           ROW_NUMBER() OVER (PARTITION BY user_id, {sid_col}
                              ORDER BY ts, item_id) AS rk
    FROM sessions WHERE behavior = 'buy'
),
sz AS (
    SELECT user_id, {sid_col} AS sid, COUNT(*) AS 会话长度
    FROM sessions GROUP BY 1, 2
),
前 AS (
    SELECT s.user_id, s.{sid_col} AS sid,
           MAX(CASE WHEN s.behavior='pv'   THEN 1 ELSE 0 END) AS 浏览过,
           MAX(CASE WHEN s.behavior='cart' THEN 1 ELSE 0 END) AS 加购过,
           MAX(CASE WHEN s.behavior='fav'  THEN 1 ELSE 0 END) AS 收藏过
    FROM sessions s
    JOIN fb f ON f.user_id = s.user_id AND f.sid = s.{sid_col} AND f.rk = 1
    WHERE (s.ts, s.item_id) < (f.ts, f.item_id)
    GROUP BY 1, 2
)
SELECT
    CASE
        WHEN p.加购过 = 1 THEN '先加购过'
        WHEN p.收藏过 = 1 THEN '先收藏过'
        WHEN p.浏览过 = 1 THEN '只先浏览过'
        WHEN z.会话长度 = 1 THEN '整场只此一个动作'
        ELSE '第一单就是会话开头（后面还有行为）'
    END AS 第一单之前发生了什么,
    COUNT(*) AS 会话数,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比
FROM fb f
JOIN sz z ON z.user_id = f.user_id AND z.sid = f.sid
LEFT JOIN 前 p ON p.user_id = f.user_id AND p.sid = f.sid
WHERE f.rk = 1
GROUP BY 1
"""


def main():
    con = db.connect()
    frames = []
    for label, col in [('15 分钟', 'sid15'), ('30 分钟（主口径）', 'sid30'),
                       ('60 分钟', 'sid60')]:
        print(f'\n{"=" * 62}\n会话阈值 {label}\n{"=" * 62}')
        df = con.execute(build(col)).df()
        df.insert(0, '会话阈值', label)
        print(df.to_string(index=False), flush=True)
        frames.append(df)
    # 画图脚本要的：三个阈值下「第一单之前发生了什么」的横向对比
    pd.concat(frames).to_csv(os.path.join(db.TABLES, 's8d_buy_position.csv'),
                             index=False, encoding='utf-8-sig')

    # 「第一单前面没有任何前序行为」的总占比，三个阈值横向对比
    print(f'\n{"=" * 62}\n汇总：进来第一件事就是下单的占比\n{"=" * 62}')
    rows = []
    for label, col in [('15 分钟', 'sid15'), ('30 分钟', 'sid30'), ('60 分钟', 'sid60')]:
        v = con.execute(f"""
        WITH fb AS (
            SELECT user_id, {col} AS sid, ts, item_id,
                   ROW_NUMBER() OVER (PARTITION BY user_id, {col}
                                      ORDER BY ts, item_id) AS rk
            FROM sessions WHERE behavior='buy'
        ),
        有前序 AS (
            SELECT DISTINCT s.user_id, s.{col} AS sid
            FROM sessions s
            JOIN fb f ON f.user_id=s.user_id AND f.sid=s.{col} AND f.rk=1
            WHERE (s.ts, s.item_id) < (f.ts, f.item_id)
        ),
        n AS (SELECT COUNT(*) AS tot FROM fb WHERE rk=1)
        SELECT ROUND((SELECT tot FROM n) * 1.0 - COUNT(*) , 0) AS 无前序,
               (SELECT tot FROM n) AS 有第一单的会话数,
               ROUND(((SELECT tot FROM n) - COUNT(*)) * 100.0
                     / (SELECT tot FROM n), 2) AS 占比
        FROM 有前序""").df()
        v.insert(0, '会话阈值', label)
        print(v.to_string(index=False, header=(label == '15 分钟')), flush=True)
        rows.append(v)
    pd.concat(rows).to_csv(os.path.join(db.TABLES, 's8d_no_prior.csv'),
                           index=False, encoding='utf-8-sig')


if __name__ == '__main__':
    main()
