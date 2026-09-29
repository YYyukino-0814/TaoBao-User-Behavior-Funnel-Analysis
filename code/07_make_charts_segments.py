# -*- coding: utf-8 -*-
"""S7 · 用户分层的两张结论图。

用法：
    python code/07_make_charts_segments.py

数据源：sql/sql_07_segments.sql 跑出来的 output/tables/sql_07_segments_r*.csv
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from viz import (SURFACE, INK, INK2, MUTED, AXIS, S1, S2, RESID,
                 dress, title, load, save)


# ============================================================
# 图14 · 谁在贡献行为量，谁在贡献购买量 —— 这两个不是同一批人
# ============================================================
def chart_contribution():
    r1 = load('sql_07_segments', 1)
    r4 = load('sql_07_segments', 4)
    d = r4.sort_values('分层').reset_index(drop=True)
    names = [n.split(' ', 1)[1] for n in d['分层']]
    ppl = dict(zip(r1['分层'], r1['人数']))
    labels = [f'{n}\n{ppl[d["分层"][i]]:,} 人' for i, n in enumerate(names)]

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(11.6, 4.5), gridspec_kw={'width_ratios': [1.25, 1]})
    dress(axL, ygrid=True)
    dress(axR, ygrid=True)

    # ---- 左：行为量占比 vs 购买量占比 ----
    x = list(range(len(d)))
    w = 0.34
    a = d['行为量占比']
    b = d['购买量占比']
    axL.bar([i - w / 2 for i in x], a, width=w, color=S1, zorder=3,
            label='占全部行为量的比例')
    axL.bar([i + w / 2 for i in x], b, width=w, color=S2, zorder=3,
            label='占全部购买量的比例')
    for i, (va, vb) in enumerate(zip(a, b)):
        axL.text(i - w / 2, va + 1.4, f'{va:.1f}%', ha='center', fontsize=10.5,
                 color=INK, fontweight='bold')
        axL.text(i + w / 2, vb + 1.4, f'{vb:.1f}%', ha='center', fontsize=10.5,
                 color=INK, fontweight='bold')
    axL.set_xticks(x)
    axL.set_xticklabels(labels, fontsize=10)
    axL.set_ylim(0, 84)
    axL.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axL.set_ylabel('占比', fontsize=9.5, color=MUTED)
    axL.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2,
               frameon=False, fontsize=9.5, handlelength=1.2,
               handleheight=1.2, labelcolor=INK2)
    axL.annotate('重度用户拿走 68% 的行为量，\n只产出 53% 的购买量',
                 xy=(1.86, 66.0), xytext=(0.78, 72), ha='center', fontsize=9,
                 color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    title(axL, '行为量高度集中，购买量却没那么集中',
          '三层各占约三分之一人数（按行为总数三分位切分）')

    # ---- 右：单位行为的购买产出 —— 越"轻"的人，每一份行为越值钱 ----
    eff = (b / a).tolist()
    axR.bar(x, eff, width=0.5, color=S1, zorder=3)
    for i, e in enumerate(eff):
        axR.text(i, e + 0.055, f'{e:.2f}', ha='center', fontsize=12,
                 color=INK, fontweight='bold')
        axR.text(i, 0.09, ('买得比\n逛得多' if e > 1 else '逛得比\n买得多'),
                 ha='center', fontsize=8.5, color='#ffffff')
    axR.axhline(1.0, color=AXIS, linewidth=1.2, zorder=2)
    axR.text(2.42, 1.04, '1.0 = 产出与\n行为量成正比', ha='right', fontsize=8.5,
             color=MUTED, va='bottom')
    axR.set_xticks(x)
    axR.set_xticklabels(names, fontsize=10.5)
    axR.set_ylim(0, 2.45)
    axR.set_ylabel('购买量占比 ÷ 行为量占比', fontsize=9.5, color=MUTED)
    title(axR, '轻度用户的"单位行为购买产出"是重度的 2.6 倍',
          '2.02 ÷ 0.78 = 2.59　·　越活跃的人，行为里购买占比越低')

    save(fig, 's7_contribution.png')


# ============================================================
# 图15 · 换个分层标准，结论还站得住吗
# ============================================================
def chart_robustness():
    r5 = load('sql_07_segments', 5)
    r5 = r5.sort_values('按活跃天数分层').reset_index(drop=True)
    names = [n.split(' ', 1)[1] for n in r5['按活跃天数分层']]
    labels = [f'{n}\n{r5["人数"][i]:,} 人' for i, n in enumerate(names)]

    fig, ax = plt.subplots(figsize=(8.6, 4.3))
    dress(ax, ygrid=True)

    x = list(range(len(r5)))
    w = 0.34
    ax.bar([i - w / 2 for i in x], r5['加购渗透率'], width=w, color=S1,
           zorder=3, label='加购渗透率（这类人里有多少加过购）')
    ax.bar([i + w / 2 for i in x], r5['购买渗透率'], width=w, color=S2,
           zorder=3, label='购买渗透率（这类人里有多少买过）')
    for i, (va, vb) in enumerate(zip(r5['加购渗透率'], r5['购买渗透率'])):
        ax.text(i - w / 2, va + 1.6, f'{va:.1f}', ha='center', fontsize=10,
                color=INK, fontweight='bold')
        ax.text(i + w / 2, vb + 1.6, f'{vb:.1f}', ha='center', fontsize=10,
                color=INK, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    ax.set_ylabel('占该层人数的比例', fontsize=9.5, color=MUTED)
    ax.set_xlabel('换一个分层标准：按"来了几天"分层，而不是按行为数',
                  fontsize=9.5, color=MUTED, labelpad=10)
    ax.legend(loc='upper left', frameon=False, fontsize=9.5, handlelength=1.2,
              handleheight=1.2, labelcolor=INK2)
    title(ax, '换个标准切，方向完全一致 —— 分层这件事本身是稳的',
          '两个指标都随活跃程度单调上升（28.5% → 75.0%），'
          '与按行为数分层得到的排序一致')

    save(fig, 's7_robustness.png')


if __name__ == '__main__':
    chart_contribution()
    chart_robustness()
    print('S7 图完成。')
