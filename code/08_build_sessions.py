# -*- coding: utf-8 -*-
"""S8 前置：给每条行为打上会话号，物化成 parquet。

用法：
    python code/08_build_sessions.py

为什么要单独做这一步：
  会话切分要按用户排序 + 跑窗口函数，900 万行算一次不便宜。
  S8 的 SQL 里有 6 个结果集，如果每个都重算一遍，总时间会到十几分钟。
  物化一次（约 1 分钟），后面每个查询都是秒级。

会话定义：同一用户，相邻两条行为间隔超过阈值 -> 新会话。
  同时算三个阈值（15 / 30 / 60 分钟）。30 分钟是主口径，
  另两个用于稳健性检验——**阈值是我定的，不是数据给的**，得证明结论不依赖它。

排序键：(ts, item_id, behavior)。
  时间戳只到秒，同一秒内会有多条行为，只按 ts 排序结果不稳定，同一份数据两次跑
  可能得到不同的会话内部顺序。加上后两级才能保证可复现。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

SQL = """
CREATE OR REPLACE TABLE sess AS
WITH base AS (
    SELECT
        user_id, item_id, category_id, behavior, ts, dt,
        ts - LAG(ts) OVER w AS gap
    FROM events
    WHERE dt <= DATE '2017-12-01'
    WINDOW w AS (PARTITION BY user_id ORDER BY ts, item_id, behavior)
)
SELECT
    user_id, item_id, category_id, behavior, ts, dt,
    SUM(CASE WHEN gap IS NULL OR gap >  900 THEN 1 ELSE 0 END) OVER w AS sid15,
    SUM(CASE WHEN gap IS NULL OR gap > 1800 THEN 1 ELSE 0 END) OVER w AS sid30,
    SUM(CASE WHEN gap IS NULL OR gap > 3600 THEN 1 ELSE 0 END) OVER w AS sid60
FROM base
WINDOW w AS (PARTITION BY user_id ORDER BY ts, item_id, behavior)
"""


def main():
    con = db.connect()

    n_in = con.execute(
        "SELECT COUNT(*) FROM events WHERE dt <= DATE '2017-12-01'").fetchone()[0]
    print(f'窗口内行为数 {n_in:,}，开始切会话……')

    con.execute(SQL)

    out = {
        '行为数': con.execute('SELECT COUNT(*) FROM sess').fetchone()[0],
        '用户数': con.execute('SELECT COUNT(DISTINCT user_id) FROM sess').fetchone()[0],
        '15分钟会话数': con.execute(
            'SELECT COUNT(DISTINCT (user_id, sid15)) FROM sess').fetchone()[0],
        '30分钟会话数': con.execute(
            'SELECT COUNT(DISTINCT (user_id, sid30)) FROM sess').fetchone()[0],
        '60分钟会话数': con.execute(
            'SELECT COUNT(DISTINCT (user_id, sid60)) FROM sess').fetchone()[0],
        '有购买行为的用户数(自检)': con.execute(
            "SELECT COUNT(DISTINCT user_id) FROM sess WHERE behavior='buy'"
        ).fetchone()[0],
    }
    for k, v in out.items():
        print(f'  {k:<26} {v:,}')

    os.makedirs(os.path.dirname(db.SESSION_PQ), exist_ok=True)
    con.execute(f"COPY sess TO '{db.SESSION_PQ}' (FORMAT PARQUET)")
    print(f'\n已写出 {db.SESSION_PQ}')


if __name__ == '__main__':
    main()
