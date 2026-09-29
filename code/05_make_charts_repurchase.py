# -*- coding: utf-8 -*-
"""S5 · 复购的两张结论图。

用法：
    python code/05_make_charts_repurchase.py

数据源：sql/sql_05_repurchase.sql 跑出来的 output/tables/sql_05_repurchase_r*.csv
"""
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from viz import (SURFACE, INK, INK2, MUTED, AXIS, S1, S2,
                 dress, title, load, save)

BLUE_RAMP = LinearSegmentedColormap.from_list('ord4', ['#9dc4f2', '#104281'])


# ============================================================
# 图10 · "一次即走"到底有多少 —— 以及回购率为什么会自己往下掉
# ============================================================
def chart_one_and_done():
    r1 = load('sql_05_repurchase', 1)
    r2 = load('sql_05_repurchase', 2)
    r4 = load('sql_05_repurchase', 4)

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(12.0, 4.5), gridspec_kw={'width_ratios': [1, 1.15]})
    dress(axL, ygrid=True)
    dress(axR, ygrid=True)

    # ---- 左：按"购买天数"分层 ----
    x = list(range(len(r2)))
    colors = [BLUE_RAMP(i / (len(r2) - 1)) for i in x]
    axL.bar(x, r2['占购买者比例'], width=0.6, color=colors, zorder=3)
    for i, (v, n) in enumerate(zip(r2['占购买者比例'], r2['人数'])):
        axL.text(i, v + 1.2, f'{v:.1f}%', ha='center', fontsize=11.5,
                 color=INK, fontweight='bold')
        if v > 30:                       # 柱子够高，人数标签放进柱内，别顶到副标题
            axL.text(i, v - 6.0, f'{n:,} 人', ha='center', fontsize=9,
                     color='#ffffff')
        else:
            axL.text(i, v + 5.0, f'{n:,} 人', ha='center', fontsize=9,
                     color=MUTED)
    axL.set_xticks(x)
    axL.set_xticklabels(r2['购买天数分层'], fontsize=10)
    axL.set_ylim(0, 68)
    axL.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axL.set_ylabel('占购买者的比例', fontsize=9.5, color=MUTED)
    axL.set_xlabel('这个用户有几天产生过购买行为（窗口内有 57,470 人买过）',
                   fontsize=9, color=MUTED, labelpad=12)
    # 口径对照：同一批人，换个口径，"一次即走"从 40.6% 变成 54.3%
    axL.annotate('同样这批人，若按「购买记录数」算，\n'
                 '只有 40.6% 是单次——差 13.7 个点，\n'
                 '全是"同一天买了好几件"撑起来的',
                 xy=(0.13, 43), xytext=(2.05, 38), ha='center', fontsize=9,
                 color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    title(axL, '一半以上的购买者，只在一个日子里买过东西',
          '口径 = 购买天数，不是购买记录数　·　观察窗 11-25 ~ 12-01')

    # ---- 右：窗口截断检验 ----
    d = r4[r4['此后还剩几天可观察'] >= 0].reset_index(drop=True)
    x = list(range(len(d)))
    axR.bar(x, d['回购率'], width=0.6, color=S2, zorder=3)
    for i, (v, days) in enumerate(zip(d['回购率'], d['此后还剩几天可观察'])):
        axR.text(i, v + 1.6, f'{v:.1f}', ha='center', fontsize=10,
                 color=INK, fontweight='bold')
        axR.text(i, -6.5, f'{days}天', ha='center', fontsize=8.5, color=MUTED)
    axR.set_ylim(0, 82)
    axR.set_xticks(x)
    axR.set_xticklabels([str(v)[5:] for v in d['首次购买日']], fontsize=9)
    axR.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axR.set_ylabel('之后又买过的人占比', fontsize=9.5, color=MUTED)
    axR.set_xlabel('首次购买日期（下方数字 = 此后还剩几天可以观察）',
                   fontsize=9, color=MUTED, labelpad=18)
    axR.text(3.4, 62, '这条下降不是"用户变心了"，是右端\n'
                      '没时间了 —— 要读量级，只能看\n最左边那条',
             ha='center', va='center', fontsize=9, color=INK2)
    title(axR, '回购率一路下滑，但这是窗口截断，不是行为',
          '首购越晚的人，剩余可观察天数越少 —— 不看这一列就会读成规律')

    save(fig, 's5_one_and_done.png')


# ============================================================
# 图11 · 回购是"买别的"，不是"重复买同一件"
# ============================================================
def chart_repeat_pattern():
    r3 = load('sql_05_repurchase', 3)
    r6 = load('sql_05_repurchase', 6).iloc[0]

    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    dress(ax, ygrid=True)

    x = list(range(len(r3)))
    ax.bar(x, r3['占比'], width=0.56, color=S1, zorder=3)
    for i, (v, n) in enumerate(zip(r3['占比'], r3['次数'])):
        ax.text(i, v + 1.1, f'{v:.1f}%', ha='center', fontsize=10.5,
                color=INK, fontweight='bold')
        ax.text(i, v + 5.4, f'{n:,} 次', ha='center', fontsize=8.5, color=MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels([f'隔 {n} 天' for n in r3['间隔天数']], fontsize=10)
    ax.set_ylim(0, 62)
    ax.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    ax.set_ylabel('占全部相邻两次购买的比例', fontsize=9.5, color=MUTED)
    ax.set_xlabel('同一个人相邻两次购买之间隔了几天', fontsize=9.5,
                  color=MUTED, labelpad=10)

    n_item = int(r6['人去重后的购买商品对数'])
    ax.annotate(f'跨天重复买同一个商品的，只有 {r6["占比"]:.2f}%\n'
                f'（{n_item:,} 个"人 × 商品"配对里只有 {int(r6["跨天重复买过同一商品的"]):,} 个）\n'
                f'→ 回购是"换别的东西买"，不是认准一件反复买',
                xy=(4.15, 37), ha='center', fontsize=9.5, color=INK2,
                bbox=dict(boxstyle='round,pad=0.5', facecolor=SURFACE,
                          edgecolor=AXIS, linewidth=0.8))
    title(ax, '回购隔得越久越少，而且几乎不买同一件',
          '间隔分布　·　呼应 S2：购物车是比价清单，用户是在"逛"，不是在"认品牌"')

    save(fig, 's5_repeat_pattern.png')


if __name__ == '__main__':
    chart_one_and_done()
    chart_repeat_pattern()
    print('S5 图完成。')
