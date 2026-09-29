# -*- coding: utf-8 -*-
"""共用工具：项目路径 + DuckDB 连接（自动挂上分析主表视图 events）。

所有分析脚本都从这里拿连接，保证大家读的是同一张表、同一套路径。
"""
import os
import sys

import duckdb

# Windows 控制台默认 GBK，中文会报 UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(*parts):
    """拼项目内路径，统一正斜杠（DuckDB / Windows 都吃）。"""
    return os.path.join(BASE, *parts).replace('\\', '/')


MAIN_PQ = path('data', 'clean', 'events.parquet')   # 分析主表（1000 万行样本，已清洗）
# 会话表（S8 用）：由 code/08_build_sessions.py 生成，每个行为挂上它所属的会话号。
# 切会话要按用户排序 + 跑窗口函数，900 万行算一次很贵；物化成 parquet 后所有
# 后续查询直接读，避免同一个窗口在每个结果集里重算一遍。
SESSION_PQ = path('data', 'clean', 'session_events.parquet')
TABLES = path('output', 'tables')
CHARTS = path('output', 'charts')


def connect():
    """返回 DuckDB 连接，并把分析主表挂成视图 events，SQL 里直接 FROM events。

    如果会话表已经建好，再挂一个视图 sessions（列里带 sid15 / sid30 / sid60，
    对应三种会话阈值），S8 的 SQL 直接用；没建好就只挂 events。
    """
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW events AS SELECT * FROM '{MAIN_PQ}'")
    if os.path.exists(SESSION_PQ):
        con.execute(f"CREATE OR REPLACE VIEW sessions AS SELECT * FROM '{SESSION_PQ}'")
    return con
