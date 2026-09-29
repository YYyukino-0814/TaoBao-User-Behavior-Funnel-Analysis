# -*- coding: utf-8 -*-
"""SQL 执行器：跑一个 sql/*.sql 文件，把每个结果集打印出来并存成 csv。

用法：
    python code/run_sql.py sql/sql_01_overview.sql

约定：
  - sql 文件里用分号分隔多个结果集（注释行以 -- 开头）；
  - 每个结果存到 output/tables/<文件名>_r1.csv, _r2.csv ...
  - SQL 里可直接 FROM events —— 那是分析主表（1000 万行样本）。
"""
import os
import sys

import db


def split_statements(text):
    """去掉整行注释，再按分号切成一条条 SQL。"""
    kept = [ln for ln in text.splitlines() if not ln.strip().startswith('--')]
    return [s.strip() for s in '\n'.join(kept).split(';') if s.strip()]


def main():
    if len(sys.argv) < 2:
        raise SystemExit('用法：python code/run_sql.py sql/sql_01_overview.sql')

    sql_file = sys.argv[1]
    if not os.path.isabs(sql_file):
        sql_file = os.path.join(db.BASE, sql_file)
    tag = os.path.splitext(os.path.basename(sql_file))[0]

    con = db.connect()
    os.makedirs(db.TABLES, exist_ok=True)

    statements = split_statements(open(sql_file, encoding='utf-8').read())
    print(f'>>> {tag}：共 {len(statements)} 个结果集\n')

    for i, stmt in enumerate(statements, 1):
        df = con.execute(stmt).fetchdf()
        print(f'—— 结果 {i} ——')
        print(df.to_string(index=False))
        print()
        df.to_csv(os.path.join(db.TABLES, f'{tag}_r{i}.csv'),
                  index=False, encoding='utf-8-sig')

    print(f'已存 output/tables/{tag}_r*.csv')


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
