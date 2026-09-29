# -*- coding: utf-8 -*-
"""S9 · 加购召回的两张结论图。

用法：
    python code/09_make_charts_recall.py

数据源：sql/sql_09_recall.sql 跑出来的 output/tables/sql_09_recall_r*.csv
"""
import os
import sys

import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from viz import (SURFACE, INK, INK2, MUTED, AXIS, S1, S2, RESID,
                 dress, title, load, save)


# ============================================================
# 图19 · 盘子有多大，盘子握在谁手里
# ============================================================
def chart_pool():
    r1 = load('sql_09_recall', 1).iloc[0]
    r5 = load('sql_09_recall', 5)
    dead = r1['沉默占比']
    alive = 100 - dead

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(12.4, 4.6), gridspec_kw={'width_ratios': [0.9, 1.35]})
    dress(axL, xgrid=True, ygrid=False)
    dress(axR, ygrid=True)

    # ---- 左：389,170 件加购，七天内成交的只有 6.21% ----
    axL.barh([0], [alive], height=0.5, color=S2, zorder=3)
    axL.barh([0], [dead], left=[alive + 1.0], height=0.5, color=S1, zorder=3)
    # 数值写在色块【下面】：白字压橙对比度不够，这条规矩在 S8 已经吃过一次
    axL.text(alive / 2, -0.36, f'七天内成交\n{alive:.2f}%\n{r1["七天内买下的"]:,.0f} 件',
             ha='center', va='top', fontsize=10.5, color=INK, fontweight='bold')
    axL.text(alive + 1.0 + dead / 2, -0.36,
             f'沉默：七天内没成交\n{dead:.2f}%\n{r1["沉默加购对"]:,.0f} 件',
             ha='center', va='top', fontsize=10.5, color=INK, fontweight='bold')
    axL.set_xlim(0, 101)
    axL.set_ylim(-1.05, 0.42)
    axL.set_yticks([])
    axL.xaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axL.set_xlabel(f'加购商品共 {r1["加购商品对"]:,.0f} 对（人 × 商品，去重）',
                   fontsize=9.5, color=MUTED, labelpad=30)
    title(axL, '九成四的加购商品，七天内没有成交',
          f'涉及 {r1["加购人数"]:,.0f} 个加购的人')

    # ---- 右：这批沉默件握在谁手里 ----
    d = r5.sort_values('分层').reset_index(drop=True)
    names = [n.split(' ', 1)[1] for n in d['分层']]
    x = list(range(len(d)))
    w = 0.34
    axR.bar([i - w / 2 for i in x], d['人数占比'], width=w, color=S1, zorder=3,
            label='占加购人数的比例')
    axR.bar([i + w / 2 for i in x], d['沉默件数占比'], width=w, color=S2,
            zorder=3, label='占全部沉默件的比例')
    for i, (va, vb) in enumerate(zip(d['人数占比'], d['沉默件数占比'])):
        axR.text(i - w / 2, va + 1.5, f'{va:.1f}%', ha='center', fontsize=10.5,
                 color=INK, fontweight='bold')
        axR.text(i + w / 2, vb + 1.5, f'{vb:.1f}%', ha='center', fontsize=10.5,
                 color=INK, fontweight='bold')
    axR.set_xticks(x)
    axR.set_xticklabels([f'{n}\n{int(c):,} 人' for n, c in
                         zip(names, d['人数'])], fontsize=10)
    axR.set_ylim(0, 96)
    axR.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axR.set_ylabel('占比', fontsize=9.5, color=MUTED)
    axR.legend(loc='upper left', frameon=False, fontsize=9.5, handlelength=1.2,
               labelcolor=INK2)
    axR.annotate('近一半的人，一个人就攒了 4 件以上没买的；\n'
                 '召回名单该发给他们，不是发给只沉默 1 件的人',
                 xy=(3.18, 84.47), xytext=(1.32, 63), ha='center', fontsize=9,
                 color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    title(axR, '沉默件高度集中：一半的人握着八成半的机会',
          '按每个人"沉默了几件"分层　·　沉默 = 加了购但七天内没买')

    save(fig, 's9_recall_pool.png')


# ============================================================
# 图20 · 召回该在什么时候打
# ============================================================
def chart_timing():
    r2 = load('sql_09_recall', 2)
    r3 = load('sql_09_recall', 3)
    r4 = load('sql_09_recall', 4).iloc[0]

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(12.4, 4.6), gridspec_kw={'width_ratios': [1, 1.15]})
    dress(axL, ygrid=True)
    dress(axR, ygrid=True)

    # ---- 左：加购之后多久才买（累计曲线）----
    x = list(range(len(r2)))
    cum = r2['累计占比']
    axL.plot(x, cum, color=S1, linewidth=2, marker='o', markersize=7,
             markeredgecolor=SURFACE, markeredgewidth=2, zorder=3,
             label='累计成交占比')
    for i, v in enumerate(cum):
        axL.text(i, v + 3.2, f'{v:.1f}%', ha='center', fontsize=10,
                 color=INK, fontweight='bold')
    axL.axvline(2, color=AXIS, linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
    axL.text(2.08, 8, '24 小时线', fontsize=9, color=MUTED, va='bottom')
    axL.set_xticks(x)
    axL.set_xticklabels(r2['加购到购买'], fontsize=9)
    axL.set_xlim(-0.35, len(x) - 0.5)
    axL.set_ylim(0, 112)
    axL.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axL.set_ylabel('累计成交占比', fontsize=9.5, color=MUTED)
    axL.set_xlabel('从加购到买下隔了多久', fontsize=9.5, color=MUTED, labelpad=8)
    axL.legend(loc='lower right', frameon=False, fontsize=9.5, handlelength=1.4,
               labelcolor=INK2)
    title(axL, '六成三在一天内成交，九成二在三天内',
          f'只看七天内真的买回来的 {int(r2["对数"].sum()):,} 对加购商品\n'
          f'（另有 {r1_gap():,} 对是"买在前、加在后"，不算买回，已剔除）')

    # ---- 右：截断检验 —— 两个短口径是平的，只有长口径在掉 ----
    days = [str(d)[5:] for d in r3['加购日']]
    series = [('一小时内成交率', '一小时内成交率', S1),
              ('一天内成交率', '一天内成交率', S2)]
    for label, col, c in series:
        axR.plot(range(len(r3)), r3[col], color=c, linewidth=2, marker='o',
                 markersize=7, markeredgecolor=SURFACE, markeredgewidth=2,
                 zorder=3, label=label)
    # 三条线在 12-01 收敛到同一处，逐条标端点会叠在一起 ——
    # 图例已经把三条线分清楚了，这里改成直接标那句结论
    axR.plot(range(len(r3)), r3['窗口内成交率'], color=MUTED, linewidth=2,
             marker='s', markersize=7, markeredgecolor=SURFACE,
             markeredgewidth=2, zorder=3, label='窗口内成交率（受截断影响）')
    axR.annotate('窗口内成交率一路下滑，\n是"越晚加购、剩的时间越短"造成的',
                 xy=(4.1, 6.85), xytext=(1.2, 8.6), ha='left', fontsize=9,
                 color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    axR.annotate('这两条基本是平的\n→ 转化能力没变',
                 xy=(4.4, 4.33), xytext=(1.4, 1.6), ha='left', fontsize=9,
                 color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    axR.set_xticks(range(len(r3)))
    axR.set_xticklabels(days, fontsize=9.5)
    axR.set_xlim(-0.35, len(r3) - 0.55)
    axR.set_ylim(0, 9.6)
    axR.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axR.set_ylabel('成交率', fontsize=9.5, color=MUTED)
    axR.set_xlabel('加购发生在哪一天　（越靠右，剩下能观察的时间越短）',
                   fontsize=9.5, color=MUTED, labelpad=8)
    axR.legend(loc='upper right', frameon=False, fontsize=9.5, handlelength=1.4,
               labelcolor=INK2)
    title(axR, '掉的只有长口径 —— 那是窗口不够，不是转化变差',
          '前两条线基本是平的：一小时内 1.45~1.84%，一天内 3.98~4.67%')

    save(fig, 's9_recall_timing.png')


def r1_gap():
    """买在前、加在后的对数：结果1 的成交对 减去 结果2 的对数。"""
    r1 = load('sql_09_recall', 1).iloc[0]
    r2 = load('sql_09_recall', 2)
    return int(r1['七天内买下的'] - r2['对数'].sum())


if __name__ == '__main__':
    chart_pool()
    chart_timing()
    print('S9 图完成。')
