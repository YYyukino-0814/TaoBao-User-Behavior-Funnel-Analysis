# data/ · 数据说明

> **这个目录不在仓库里。**
> 原始数据 + 中间 parquet 合计约 **4.4 GB**，超过 GitHub 单文件 100 MB 的上限，
> 所以仓库里只保留这份说明。按下面三步能把整条流程原样跑起来。

数据不跟着仓库走是**刻意的**：这份数据集任何人都能免费下到，
而把 3.67 GB 的 csv 塞进 git 只会让 clone 变得没法用。

---

## 一、原始数据

| 项 | 内容 |
|---|---|
| 数据集 | User Behavior Data from Taobao（淘宝用户行为数据集） |
| 来源 | Kaggle / 阿里天池（同源） |
| 放置路径 | `data/raw/UserBehavior.csv` |
| 体积 | 3.67 GB，约 **1 亿行** |
| 格式 | **没有表头**，逗号分隔，5 列 |

列顺序（原始文件里没有列名，这是约定顺序）：

```
user_id, item_id, category_id, behavior, timestamp
```

- `behavior` 四种取值：`pv` 浏览 / `fav` 收藏 / `cart` 加购 / `buy` 购买
- `timestamp` 是 **Unix 秒**
- 数据覆盖 2017-11-25 ~ 2017-12-03（本项目分析窗口截至 12-01，剔除了末尾两天异常）

---

## 二、运行环境

```bash
pip install duckdb pandas numpy matplotlib scipy pyarrow
```

取数全部由 **DuckDB** 直接读 csv / parquet 完成，不需要装数据库。
项目在 Windows + Python 3.13 上跑通。

---

## 三、复现顺序

```bash
# 1. 建库 —— 读 3.67 GB 原始 csv，按用户抽 10%、算北京时间、剔异常时间戳
#    产出分析主表 data/clean/events.parquet（1000 万行）
python code/01_build_sample.py

# 2. 切会话 —— S8 / S9 依赖它。900 万行跑窗口函数很贵，所以物化成 parquet
python code/08_build_sessions.py

# 3. 各节 SQL —— 结果落到 output/tables/，文件名形如 sql_02_funnel_r1.csv
python code/run_sql.py sql/sql_01_overview.sql
python code/run_sql.py sql/sql_02_funnel.sql
python code/run_sql.py sql/sql_03_time.sql
python code/run_sql.py sql/sql_04_retention.sql
python code/run_sql.py sql/sql_05_repurchase.sql
python code/run_sql.py sql/sql_06_category.sql
python code/run_sql.py sql/sql_07_segments.sql
python code/run_sql.py sql/sql_08_paths.sql
python code/run_sql.py sql/sql_09_recall.sql

# 4. 画图 / 检验 / 出表 —— 依赖第 3 步的结果
python code/02_make_charts.py
python code/03_make_charts_time.py
python code/04_make_charts_retention.py
python code/05_make_charts_repurchase.py
python code/06_chi_square.py            # 卡方 + 效应量 + 跨天排序稳定性检验
python code/07_make_charts_segments.py
python code/08_make_charts_paths.py
python code/08b_robustness.py           # S8 三个稳健性检验
python code/08c_transitions.py
python code/08d_buy_position.py
python code/09_make_charts_recall.py
python code/10_build_tableau_tables.py  # 看板数据源（内置 assert 自检）
```

**依赖关系是干净的**：建库 → SQL → 画图，后者只读前者的产物，
没有任何一步会回头改上一步的东西，所以单独重跑任何一节都可以。

> 不想跑数据也完全可以：`output/` 里的 20 张结论图、9 组取数结果和 4 张看板表
> 都已经随仓库提交了，`分析文档/` 里每篇都对着图讲了结论。
