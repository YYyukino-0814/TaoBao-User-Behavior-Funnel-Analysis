# -*- coding: utf-8 -*-
"""
01_build_sample.py — P2：淘宝 UserBehavior 抽样与建库

输入：data/raw/UserBehavior.csv          原始 3.5GB，5 列无表头，只读不改
输出：data/clean/events_full.parquet     全量列式缓存（1 亿行，用于校验/对比）
      data/sample/events_sample.parquet  千万行样本（未清洗）
      data/clean/events.parquet          【分析主表】样本 ∩ 有效时间窗口
      output/tables/*.csv               体检结果

三个关键方法决策（面试可讲）：

1) 按【用户】抽样，不是按行截取、也不是按行随机抽。
   - 文件按 user_id 聚块排列 → 截前 N 行 = 只取最低 user_id 段 = 最早注册的老用户，有系统偏差；
   - 按行随机抽 → 稀有事件（buy 仅约 2%）会在单个用户内被抽没，导致转化率被系统性低估；
   - 按用户整块抽 → 每个用户"逛→加购→买"链路完整，且用户总体随机。

2) 时间按【北京时间】换算（Unix 秒 + 8 小时）。
   直接 to_timestamp() 得到的是 UTC，会让"晚高峰"整体偏移 8 小时，S3 时间规律分析全错。

3) 有效窗口 = 2017-11-25 ~ 2017-12-03。
   实测全量 1 亿行里有极少量时间戳损坏（出现 1902 年、2037 年、负数时间戳），
   剔除后 99.95% 的数据落在这 9 天内。
"""
import os
import sys
import time

import duckdb

# Windows 控制台默认 GBK，中文/符号会报 UnicodeEncodeError，强制 UTF-8 输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def p(*parts):
    """拼项目内路径，统一正斜杠（DuckDB / Windows 都吃）。"""
    return os.path.join(BASE, *parts).replace('\\', '/')


RAW_CSV = p('data', 'raw', 'UserBehavior.csv')
FULL_PQ = p('data', 'clean', 'events_full.parquet')
SAMPLE_PQ = p('data', 'sample', 'events_sample.parquet')
MAIN_PQ = p('data', 'clean', 'events.parquet')
TABLES = p('output', 'tables')

# 有效时间窗口（实测确定，见文件头注释 3）
WIN_START = '2017-11-25'
WIN_END = '2017-12-03'
WIN = f"dt BETWEEN DATE '{WIN_START}' AND DATE '{WIN_END}'"

KEEP_MOD = 100  # 哈希空间
KEEP_TH = 10    # 保留 10% 的用户 ≈ 1000 万行


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def main():
    for d in (os.path.dirname(FULL_PQ), os.path.dirname(SAMPLE_PQ), TABLES):
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(RAW_CSV):
        raise SystemExit(f'找不到原始文件：{RAW_CSV}')

    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")  # 固定 UTC，保证 +8h 换算确定

    log(f'原始文件 {os.path.getsize(RAW_CSV) / 1024 ** 3:.2f} GB')

    # ---------- 阶段 1：CSV → 全量列式缓存（已存在则跳过）----------
    if os.path.exists(FULL_PQ):
        log('阶段1/5：全量 parquet 已存在，跳过')
    else:
        log('阶段1/5：CSV → 全量 parquet（补 dt / hr，时区=北京时间）…')
        con.execute(f"""
            COPY (
                SELECT
                    user_id,
                    item_id,
                    category_id,
                    behavior,
                    ts,
                    CAST(to_timestamp(ts) + INTERVAL 8 HOUR AS DATE)       AS dt,
                    EXTRACT(hour FROM to_timestamp(ts) + INTERVAL 8 HOUR)  AS hr
                FROM read_csv('{RAW_CSV}', header = false, columns = {{
                    'user_id'    : 'BIGINT',
                    'item_id'    : 'BIGINT',
                    'category_id': 'BIGINT',
                    'behavior'   : 'VARCHAR',
                    'ts'         : 'BIGINT'
                }})
            ) TO '{FULL_PQ}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
        log('阶段1 完成')

    # ---------- 阶段 2：全量体检 ----------
    log('阶段2/5：全量体检')
    n, users, items, cats, ts_min, ts_max = con.execute(f"""
        SELECT COUNT(*), COUNT(DISTINCT user_id), COUNT(DISTINCT item_id),
               COUNT(DISTINCT category_id), MIN(ts), MAX(ts)
        FROM '{FULL_PQ}'
    """).fetchone()
    n_in = con.execute(f"SELECT COUNT(*) FROM '{FULL_PQ}' WHERE {WIN}").fetchone()[0]
    days_in = con.execute(f"SELECT COUNT(DISTINCT dt) FROM '{FULL_PQ}' WHERE {WIN}").fetchone()[0]

    print(f'  总行数       : {n:,}')
    print(f'  用户数       : {users:,}')
    print(f'  商品数       : {items:,}')
    print(f'  类目数       : {cats:,}')
    print(f'  时间戳跨度   : {ts_min} ~ {ts_max}   ← 含损坏时间戳')
    print(f'  有效窗口内   : {n_in:,} 行 / {days_in} 天  （{n_in / n * 100:.3f}%）')
    print(f'  窗口外异常行 : {n - n_in:,} 行  （{(n - n_in) / n * 100:.3f}%）')

    top = con.execute(f"""
        SELECT dt, COUNT(*) AS n, COUNT(DISTINCT user_id) AS users
        FROM '{FULL_PQ}' GROUP BY dt ORDER BY n DESC LIMIT 12
    """).fetchdf()
    top = top.sort_values('dt')
    print('\n  —— 全量：行数最多的 12 天（即真实窗口） ——')
    print(top.to_string(index=False))

    beh = con.execute(f"""
        SELECT behavior, COUNT(*) AS n, COUNT(DISTINCT user_id) AS users
        FROM '{FULL_PQ}' GROUP BY behavior ORDER BY n DESC
    """).fetchdf()
    beh['行数占比%'] = (beh['n'] / n * 100).round(3)
    beh['人数占比%'] = (beh['users'] / users * 100).round(2)
    print('\n  —— 全量：行为分布 ——')
    print(beh.to_string(index=False))
    beh.to_csv(os.path.join(TABLES, 'full_behavior_counts.csv'), index=False, encoding='utf-8-sig')

    # ---------- 阶段 3：按用户抽样（已存在则跳过）----------
    if os.path.exists(SAMPLE_PQ):
        log('阶段3/5：样本 parquet 已存在，跳过')
    else:
        log(f'阶段3/5：按用户抽样  hash(user_id) % {KEEP_MOD} < {KEEP_TH} …')
        con.execute(f"""
            COPY (
                SELECT * FROM '{FULL_PQ}'
                WHERE hash(user_id) % {KEEP_MOD} < {KEEP_TH}
            ) TO '{SAMPLE_PQ}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
        log('阶段3 完成')

    # ---------- 阶段 4：清洗 → 分析主表 ----------
    log('阶段4/5：清洗（只留有效窗口）→ 分析主表 data/clean/events.parquet')
    con.execute(f"""
        COPY (SELECT * FROM '{SAMPLE_PQ}' WHERE {WIN})
        TO '{MAIN_PQ}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    # ---------- 阶段 5：样本与主表校验 ----------
    log('阶段5/5：校验')
    sn_raw = con.execute(f"SELECT COUNT(*) FROM '{SAMPLE_PQ}'").fetchone()[0]
    sn, susers, s_min, s_max, sdays = con.execute(f"""
        SELECT COUNT(*), COUNT(DISTINCT user_id), MIN(dt), MAX(dt), COUNT(DISTINCT dt)
        FROM '{MAIN_PQ}'
    """).fetchone()

    print(f'  样本原始行数 : {sn_raw:,}  （占全量 {sn_raw / n * 100:.2f}%）')
    print(f'  主表行数     : {sn:,}  （清洗掉 {sn_raw - sn:,} 行异常时间戳）')
    print(f'  主表用户数   : {susers:,}  （占全量用户 {susers / users * 100:.2f}%）')
    print(f'  主表日期     : {s_min} ~ {s_max}  （{sdays} 天）')

    sbeh = con.execute(f"""
        SELECT behavior, COUNT(*) AS n, COUNT(DISTINCT user_id) AS users
        FROM '{MAIN_PQ}' GROUP BY behavior ORDER BY n DESC
    """).fetchdf()
    sbeh['行数占比%'] = (sbeh['n'] / sn * 100).round(3)
    sbeh['人数占比%'] = (sbeh['users'] / susers * 100).round(2)
    print('\n  —— 主表：行为分布 ——')
    print(sbeh.to_string(index=False))
    sbeh.to_csv(os.path.join(TABLES, 'sample_behavior_counts.csv'), index=False, encoding='utf-8-sig')

    sday = con.execute(f"""
        SELECT dt, COUNT(*) AS n, COUNT(DISTINCT user_id) AS users
        FROM '{MAIN_PQ}' GROUP BY dt ORDER BY dt
    """).fetchdf()
    print('\n  —— 主表：每日明细 ——')
    print(sday.to_string(index=False))
    sday.to_csv(os.path.join(TABLES, 'sample_day_counts.csv'), index=False, encoding='utf-8-sig')

    # 抽样代表性校验：样本行为占比 vs 全量行为占比
    print('\n  —— 抽样代表性（主表 vs 全量 行数占比差）——')
    cmp = beh[['behavior', '行数占比%']].merge(
        sbeh[['behavior', '行数占比%']], on='behavior', suffixes=('_全量', '_主表'))
    cmp['偏差'] = (cmp['行数占比%_主表'] - cmp['行数占比%_全量']).round(3)
    print(cmp.to_string(index=False))

    ok = (sdays == days_in) and sn > 0
    print(f'\n  日覆盖自检：主表 {sdays} 天 vs 全量有效窗口 {days_in} 天 → '
          f'{"通过" if ok else "不通过（需换抽样方式）"}')
    log('P2 完成')


if __name__ == '__main__':
    main()
