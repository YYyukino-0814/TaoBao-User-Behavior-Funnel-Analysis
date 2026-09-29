# -*- coding: utf-8 -*-
"""S10 前置：生成喂 Tableau 的四张聚合小表。

用法：
    python code/10_build_tableau_tables.py

为什么单独做这一步：
  Tableau 读的是"已经聚合好的小表"，不是原始事件流。900 万行直接连
  Tableau 会又慢又没法用。所以每个看板屏配一张干净的 csv：
    01_funnel.csv    漏斗屏
    02_hourly.csv    24 小时屏
    03_retention.csv 留存屏（长表，Tableau 画队列热力图要用长表）
    04_category.csv  类目屏

列名全部用中文、不带空格、不带括号 —— 这四条是 Tableau 字段名的
踩坑点：带特殊字符的字段名在计算字段里要加方括号，很别扭。

⚠️ 每个 csv 的第一行是给人看的口径说明，写在单独一个 `_说明.txt` 里，
   不混进 csv —— 混进去 Tableau 会把说明当成第一条数据。
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

OUT = os.path.join(db.BASE, 'output', 'tableau')


def q(sql):
    return db.connect().execute(sql).df()


# ============================================================
# 屏1 · 漏斗
# ============================================================
def build_funnel():
    """漏斗屏 + 一张把所有分支都兜住、加得起来的口径核对表。

    为什么口径核对表必须做：
      第一版我按"购买者中加购过的 / 没加购直接买的"两分支拆，加起来是
      42,473 + 14,717 = 57,190，而购买者总数是 57,470 —— 【少了 280 人】。
      少的这批人是"加购过、也买过、但一次浏览都没有"。
      两分支加起来不等于总数，是必须停下来查的信号，不能就这么发出去。
      所以改成从【一张三维交叉表】派生所有数字，保证每个分支互斥且穷尽。
    """
    x = q("""
    WITH u AS (
        SELECT user_id,
               MAX(CASE WHEN behavior='pv'   THEN 1 ELSE 0 END) AS pv,
               MAX(CASE WHEN behavior='cart' THEN 1 ELSE 0 END) AS cart,
               MAX(CASE WHEN behavior='buy'  THEN 1 ELSE 0 END) AS buy
        FROM events WHERE dt <= DATE '2017-12-01'
        GROUP BY 1
    )
    SELECT pv AS 浏览, cart AS 加购, buy AS 购买, COUNT(*) AS 人数
    FROM u GROUP BY 1, 2, 3
    """)
    g = {(int(r.浏览), int(r.加购), int(r.购买)): int(r.人数)
         for r in x.itertuples()}
    c = lambda *k: g.get(k, 0)          # noqa: E731  少写点括号，读起来清楚

    全体      = sum(g.values())
    浏览人数  = c(1, 0, 0) + c(1, 0, 1) + c(1, 1, 0) + c(1, 1, 1)
    加购人数  = c(0, 1, 0) + c(0, 1, 1) + c(1, 1, 0) + c(1, 1, 1)   # 全部加购过的人
    购买人数  = c(0, 0, 1) + c(0, 1, 1) + c(1, 0, 1) + c(1, 1, 1)   # 全部购买过的人
    # 漏斗三步都要求"浏览过"，严格嵌套，所以第 2 步和上表的"加购人数"不等
    漏斗浏览  = 浏览人数
    漏斗加购  = c(1, 1, 0) + c(1, 1, 1)
    漏斗购买  = c(1, 1, 1)

    df = pd.DataFrame([
        dict(步骤序号=1, 步骤='浏览',       人数=漏斗浏览),
        dict(步骤序号=2, 步骤='浏览过且加购', 人数=漏斗加购),
        dict(步骤序号=3, 步骤='浏览过且加购且购买', 人数=漏斗购买),
    ])
    df['占上一步'] = (df['人数'] / df['人数'].shift(1) * 100).round(2)
    df.loc[0, '占上一步'] = 100.0
    df['占浏览人数'] = (df['人数'] / 漏斗浏览 * 100).round(2)
    df['口径说明'] = [
        f'样本内出现过的 {全体:,} 人里，浏览过的（去重）',
        '严格嵌套：上一步浏览过、且加购过',
        '严格嵌套：上一步加购过、且买过同一批人',
    ]

    rows = [
        ('全体', '样本内出现过的用户',   全体,     全体,     '全体用户'),
        ('全体', '一次浏览都没有的',     全体 - 浏览人数, 全体, '全体用户'),
        # 标签里写明"含 N 个没浏览过的"：否则看板上这行是 42,753、
        # 漏斗第三步是 42,473，差 280，读的人要靠猜才知道差在哪。
        ('购买者怎么来的', f'买过、也加购过（含 {c(0,1,1)} 人没浏览过）',
         c(0, 1, 1) + c(1, 1, 1), 购买人数, '全部购买者'),
        ('购买者怎么来的', '买过、没加购、浏览过', c(1, 0, 1),              购买人数, '全部购买者'),
        ('购买者怎么来的', '买过、连浏览都没有',   c(0, 0, 1),              购买人数, '全部购买者'),
        ('加购者后来怎么了', f'加购者中买了的（含 {c(0,1,1)} 人没浏览过）',
         c(0, 1, 1) + c(1, 1, 1), 加购人数, '全部加购者'),
        ('加购者后来怎么了', '加购者中没买的',     c(0, 1, 0) + c(1, 1, 0), 加购人数, '全部加购者'),
    ]
    split = pd.DataFrame(rows, columns=['口径类别', '口径', '人数', '分母', '分母是什么'])
    split['占比'] = (split['人数'] / split['分母'] * 100).round(2)
    return df, split, 全体, 加购人数, 购买人数


# ============================================================
# 屏2 · 24 小时
# ============================================================
def build_hourly():
    return q("""
    WITH e AS (SELECT * FROM events WHERE dt <= DATE '2017-12-01'),
    per_hour AS (
        -- 列名是 hr 不是 hour，而且 hr 已经是北京时间的小时（建表时加过 +8 小时）
        SELECT hr,
               COUNT(*)                                   AS 行为量,
               COUNT(DISTINCT user_id)                    AS 活跃用户数,
               COUNT(DISTINCT CASE WHEN behavior='pv'   THEN user_id END) AS 浏览人数,
               COUNT(DISTINCT CASE WHEN behavior='cart' THEN user_id END) AS 加购人数,
               COUNT(DISTINCT CASE WHEN behavior='buy'  THEN user_id END) AS 购买人数
        FROM e GROUP BY 1
    )
    SELECT hr                                        AS 小时,
           行为量,
           活跃用户数,
           ROUND(行为量 * 1.0 / 活跃用户数, 2)       AS 人均行为数,
           ROUND(加购人数 * 100.0 / 活跃用户数, 2)   AS 加购渗透率,
           ROUND(购买人数 * 100.0 / 活跃用户数, 2)   AS 购买渗透率,
           ROUND(购买人数 * 100.0 / 加购人数, 2)     AS 加购者购买率
    FROM per_hour ORDER BY hr
    """)


# ============================================================
# 屏3 · 留存（长表）
# ============================================================
def build_retention():
    return q("""
    WITH w AS (SELECT * FROM events WHERE dt <= DATE '2017-12-01'),
    first_seen AS (
        SELECT user_id, MIN(dt) AS 首次日 FROM w GROUP BY 1
    ),
    daily AS (
        SELECT DISTINCT user_id, dt FROM w
    ),
    joined AS (
        SELECT f.首次日, d.user_id, (d.dt - f.首次日) AS 第几天
        FROM first_seen f JOIN daily d ON d.user_id = f.user_id
        WHERE (d.dt - f.首次日) BETWEEN 1 AND 3
    ),
    cohort AS (
        -- 【必须数 user_id，不能数常量 1】
        -- COUNT(DISTINCT CASE WHEN 条件 THEN 1 END) 数的是"1 有几个不同取值"，
        -- 答案永远是 1 —— 整个队列人数全变成 1、回访率全变成 100%。
        -- 这个错误不会报错、不会给 NULL，只会安静地给出一张全 100% 的表。
        SELECT 首次日, COUNT(DISTINCT user_id) AS 队列人数
        FROM first_seen GROUP BY 1
    ),
    ret AS (
        SELECT 首次日, 第几天, COUNT(DISTINCT user_id) AS 回访人数
        FROM joined GROUP BY 1, 2
    )
    SELECT c.首次日                          AS 首次出现日,
           -- 【这是"首次出现在这份样本里"，不是"新用户"】——
           -- 数据只有 7 天，11-25 是第一天，所以 11-25 这个队列把当天所有
           -- 活跃的人都装了进去（70,991 人，占全体 71.7%），里面绝大多数是老客。
           -- 不写这一列，看板上"队列"两个字一定会被读成"新客"。
           CASE WHEN c.首次日 = DATE '2017-11-25'
                THEN '数据首日（把老客也算进来了，不是新客）'
                ELSE '此前未在样本中出现过' END AS 队列说明,
           c.队列人数,
           r.第几天                          AS 距首次出现天数,
           r.回访人数,
           ROUND(r.回访人数 * 100.0 / c.队列人数, 2) AS 回访率,
           (DATE '2017-12-01' - c.首次日)     AS 队列可观察天数
    FROM cohort c JOIN ret r ON r.首次日 = c.首次日
    -- 【只保留观察得到的格子】11-29 之后出现的队列，根本没有 D2/D3 ——
    -- 那些格子如果留着，值会是 0，热力图上看着像"这批人没回访"，
    -- 实际是"还没到那天"。所以直接不发出去，让 Tableau 显示为空白。
    WHERE r.第几天 <= (DATE '2017-12-01' - c.首次日)
    ORDER BY 1, 3
    """)


# ============================================================
# 屏4 · 类目
# ============================================================
def build_category():
    return q("""
    WITH w AS (SELECT * FROM events WHERE dt <= DATE '2017-12-01'),
    per AS (
        SELECT category_id,
               COUNT(DISTINCT CASE WHEN behavior='pv'  THEN user_id END) AS 浏览人数,
               COUNT(DISTINCT CASE WHEN behavior='buy' THEN user_id END) AS 购买人数,
               COUNT(*)                                                  AS 行为量
        FROM w GROUP BY 1
    )
    SELECT category_id                              AS 类目,
           浏览人数,
           购买人数,
           ROUND(购买人数 * 100.0 / 浏览人数, 2)     AS 转化率,
           行为量
    FROM per
    WHERE 浏览人数 >= 1000
    ORDER BY 行为量 DESC
    LIMIT 20
    """)


def main():
    os.makedirs(OUT, exist_ok=True)

    funnel, funnel_split, 全体, 加购人数, 购买人数 = build_funnel()
    # 自检：分支必须互斥且穷尽，加起来等于分母。加不起来就是还有分支没兜住。
    for name, sub in funnel_split.groupby('口径类别'):
        if name == '全体':
            continue
        assert sub['人数'].sum() == sub['分母'].iloc[0], \
            f'{name} 的分支加起来 {sub["人数"].sum()} ≠ 分母 {sub["分母"].iloc[0]}'
    funnel.to_csv(os.path.join(OUT, '01_funnel.csv'), index=False,
                  encoding='utf-8-sig')
    funnel_split.to_csv(os.path.join(OUT, '01b_funnel_split.csv'), index=False,
                        encoding='utf-8-sig')
    print(f'01_funnel        {len(funnel)} 行 + 口径核对表 {len(funnel_split)} 行'
          f'（自检通过：各分支互斥且穷尽）')

    hourly = build_hourly()
    hourly.to_csv(os.path.join(OUT, '02_hourly.csv'), index=False,
                  encoding='utf-8-sig')
    print(f'02_hourly        {len(hourly)} 行')

    ret = build_retention()
    ret.to_csv(os.path.join(OUT, '03_retention.csv'), index=False,
               encoding='utf-8-sig')
    print(f'03_retention     {len(ret)} 行（长表，已去掉观察不到的格子）')

    cat = build_category()
    cat.to_csv(os.path.join(OUT, '04_category.csv'), index=False,
               encoding='utf-8-sig')
    print(f'04_category      {len(cat)} 行')

    print(f'\n已写到 {OUT}')


if __name__ == '__main__':
    main()
