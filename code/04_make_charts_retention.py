# -*- coding: utf-8 -*-
"""S4 · 日活留存的两张结论图。

用法：
    python code/04_make_charts_retention.py

数据源：sql/sql_04_retention.sql 跑出来的 output/tables/sql_04_retention_r*.csv
"""
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from viz import (SURFACE, INK, INK2, MUTED, AXIS, GRID, S1, S2,
                 dress, title, load, save)

# 序数蓝阶（浅 -> 深），沿用 viz.ORD 的两端色，中间做等距插值
BLUE_RAMP = LinearSegmentedColormap.from_list('ord9', ['#9dc4f2', '#104281'])


# ============================================================
# 图8 · 留存曲线为什么不往下掉
# ============================================================
def chart_why_flat():
    r2 = load('sql_04_retention', 2)
    r5 = load('sql_04_retention', 5)

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(11.8, 4.3), gridspec_kw={'width_ratios': [1, 1.3]})
    dress(axL, ygrid=True)
    dress(axR, ygrid=True)

    # ---- 左：合并回访曲线。从 0 起画，不做截断，否则"平"是画出来的 ----
    x = list(range(len(r2)))
    axL.bar(x, r2['回访率'], width=0.52, color=S1, zorder=3)
    for i, v in enumerate(r2['回访率']):
        axL.text(i, v + 1.6, f'{v:.1f}%', ha='center', fontsize=11,
                 color=INK, fontweight='bold')
    axL.set_xticks(x)
    axL.set_xticklabels([f'第 {n} 天' for n in r2['距离首次出现的天数']], fontsize=10)
    axL.set_ylim(0, 92)
    axL.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axL.set_ylabel('回访率（当天又来了的人占比）', fontsize=9.5, color=MUTED)
    axL.annotate('三天一共只掉 1.78 个百分点', xy=(1, 73.46), xytext=(1, 84),
                 ha='center', fontsize=9.5, color=INK2, fontweight='bold')
    title(axL, '回访率三天几乎没动',
          f'合并所有队列（11-25 ~ 11-28 首次出现，共 '
          f'{int(r2["队列人数合计"].iloc[0]):,} 人）')

    # ---- 右：每个用户这 9 天活跃了几天。为什么平，看这张 ----
    d = r5
    x = list(range(len(d)))
    colors = [BLUE_RAMP(i / (len(d) - 1)) for i in x]
    axR.bar(x, d['占比'], width=0.72, color=colors, zorder=3,
            edgecolor=SURFACE, linewidth=1.2)
    for i, (v, n) in enumerate(zip(d['占比'], d['活跃天数'])):
        if v >= 1.0:
            axR.text(i, v + 0.7, f'{v:.1f}%', ha='center', fontsize=9,
                     color=INK, fontweight='bold')
    axR.set_xticks(x)
    axR.set_xticklabels([f'{n}天' for n in d['活跃天数']], fontsize=9.5)
    axR.set_ylim(0, 31)
    axR.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axR.set_ylabel('人数占比', fontsize=9.5, color=MUTED)
    axR.set_xlabel('这个用户 9 天里活跃了几天（99,020 人）',
                   fontsize=9.5, color=MUTED, labelpad=10)
    # 左侧一小撮几乎贴地，点出来，否则读者会以为"没有只来一两天的人"
    axR.annotate('只活跃 1~3 天的人\n合计 1.03%（1,014 人）',
                 xy=(2, 0.91), xytext=(2.0, 12.5), ha='center', fontsize=9,
                 color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    title(axR, '这是一个几乎每天都来的群体',
          '活跃 ≥6 天的人占 78.9%，人均 7.06 天 —— 没有"流失"可以掉')

    save(fig, 's4_why_flat.png')


# ============================================================
# 图9 · "首日加购"那个差距，是怎么被观察窗吃掉的
# ============================================================
def chart_firstday_gap():
    r3 = load('sql_04_retention', 3)
    r3 = r3.set_index('分组')
    pv = r3.loc['首日只浏览']
    ct = r3.loc['首日有加购']

    metrics = ['第 1 天回来', '第 3 天回来', '三天内至少回来一次']
    a = [pv['D1回访率'], pv['D3回访率'], pv['三天内至少回访一次']]
    b = [ct['D1回访率'], ct['D3回访率'], ct['三天内至少回访一次']]

    fig, ax = plt.subplots(figsize=(9.0, 4.4))
    dress(ax, ygrid=True)

    x = range(len(metrics))
    w = 0.32
    ax.bar([i - w / 2 for i in x], a, width=w, color=S1, zorder=3,
           label=f'首日只浏览（{int(pv["人数"]):,} 人）')
    ax.bar([i + w / 2 for i in x], b, width=w, color=S2, zorder=3,
           label=f'首日有加购（{int(ct["人数"]):,} 人）')

    for i, (va, vb) in enumerate(zip(a, b)):
        ax.text(i - w / 2, va + 1.5, f'{va:.1f}', ha='center', fontsize=10,
                color=INK, fontweight='bold')
        ax.text(i + w / 2, vb + 1.5, f'{vb:.1f}', ha='center', fontsize=10,
                color=INK, fontweight='bold')
        # 两个柱子中间标出差距，左边大右边小 —— 这就是这张图要讲的事
        ax.annotate(f'差 {vb - va:.1f} 个点', xy=(i, max(va, vb) + 9.0),
                    ha='center', fontsize=10, color=INK2, fontweight='bold')

    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics, fontsize=10.5)
    ax.set_ylim(0, 118)
    ax.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    ax.set_ylabel('回访率', fontsize=9.5, color=MUTED)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.30), ncol=2,
              frameon=False, fontsize=9.5, handlelength=1.2, handleheight=1.2,
              labelcolor=INK2)
    title(ax, '"首日加购"的优势，一拉长观察窗就基本消失了',
          '8.9 个点 → 2.6 个点　·　加购预测的是"回访得多早"，不是"会不会回访"'
          '　·　选择效应，不可当因果')

    save(fig, 's4_firstday_gap.png')


if __name__ == '__main__':
    chart_why_flat()
    chart_firstday_gap()
    print('S4 图完成。')
