# -*- coding: utf-8 -*-
"""S3 · 时间规律的两张结论图。

用法：
    python code/03_make_charts_time.py

数据源：sql/sql_03_time.sql 跑出来的 output/tables/sql_03_time_r*.csv
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from viz import (SURFACE, INK, INK2, MUTED, AXIS, S1, S2, S3,
                 dress, title, load, save)


# ============================================================
# 图6 · 一天里的形态：人最多的时候，是不是最想买的时候
# ============================================================
def chart_hourly_shape():
    r1 = load('sql_03_time', 1)
    r3 = load('sql_03_time', 3)
    hr = list(r1['小时'])

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(9.2, 6.2), sharex=True,
        gridspec_kw={'height_ratios': [1, 1.15], 'hspace': 0.2})

    for ax in (ax1, ax2):
        dress(ax, ygrid=True)

    # 上：活跃用户数——人数只有一个序列，不需要图例
    ax1.bar(hr, r1['该时段出现过的用户数'], width=0.62, color=S1, zorder=3)
    ax1.set_ylim(0, 78000)
    ax1.yaxis.set_major_formatter(lambda v, p: '0' if v == 0 else f'{v/10000:.0f}万')
    ax1.set_ylabel('该时段出现过的用户数', fontsize=9.5, color=MUTED)
    title(ax1, '人最多的是晚上 9 点，但成交动机最强的是上午 10 点',
          '上面是"来了多少人"，下面是"来了的人有多想买"　·　横轴 = 北京时间整点')
    for h in (10, 21):
        v = r1.loc[r1['小时'] == h, '该时段出现过的用户数'].iloc[0]
        ax1.annotate(f'{h}点\n{v/10000:.1f}万', xy=(h, v), xytext=(0, 8),
                     textcoords='offset points', ha='center', fontsize=9.5,
                     color=INK, fontweight='bold')

    # 下：三条渗透率，都是百分比，共用一根轴
    series = [
        ('加购者中的购买率', r3['加购者中的购买率'], S3),
        ('该时段加购渗透率', r3['该时段加购渗透率'], S2),
        ('该时段购买渗透率', r3['该时段购买渗透率'], S1),
    ]
    for name, vals, c in series:
        ax2.plot(hr, vals, color=c, linewidth=2, zorder=3, label=name)
        ax2.plot(hr, vals, 'o', color=c, markersize=4.5,
                 markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4)
        ax2.annotate(f'{vals.iloc[-1]:.0f}%', xy=(hr[-1], vals.iloc[-1]),
                     xytext=(7, 0), textcoords='offset points',
                     ha='left', va='center', fontsize=9.5,
                     color=INK, fontweight='bold')
    ax2.set_xlim(-0.6, 24.4)
    ax2.set_ylim(0, 72)
    ax2.set_xticks(range(0, 24, 2))
    ax2.set_xticklabels([f'{h}点' for h in range(0, 24, 2)], fontsize=9)
    ax2.set_ylabel('占该时段活跃人数的比例', fontsize=9.5, color=MUTED)
    ax2.legend(loc='lower center', bbox_to_anchor=(0.5, -0.34), ncol=3,
               frameon=False, fontsize=9.5, handlelength=1.6, labelcolor=INK2)
    ax2.annotate('白天加购的人\n六成会买', xy=(10, 62.81), xytext=(10, 68.5),
                 ha='center', fontsize=9, color=INK2)
    ax2.annotate('深夜加购的人\n只有四成会买', xy=(16.5, 7.5), ha='center',
                 va='center', fontsize=9, color=INK2)

    save(fig, 's3_hourly_shape.png')


# ============================================================
# 图7 · 12-02 那次跳涨，到底是什么
# ============================================================
def chart_spike_drilldown():
    r4 = load('sql_03_time', 4)
    r5 = load('sql_03_time', 5)
    hr = list(r4['小时'])

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(11.8, 4.2), gridspec_kw={'width_ratios': [1.15, 1]})
    dress(axL, ygrid=True)
    dress(axR, ygrid=True)

    # 左：两个周六的逐小时人数之比。线平 = 等比例抬高，不是某个时点爆的
    ratio = r4['周六_1202'] / r4['周六_1125']
    axL.plot(hr, ratio, color=S1, linewidth=2, zorder=3)
    axL.plot(hr, ratio, 'o', color=S1, markersize=5,
             markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4)
    axL.axhline(1.0, color=AXIS, linewidth=1, zorder=2)
    mean = ratio.mean()
    axL.axhline(mean, color=S2, linewidth=1.6, linestyle=(0, (5, 4)), zorder=2)
    axL.annotate(f'平均 {mean:.2f} 倍', xy=(0.4, mean), xytext=(0, 6),
                 textcoords='offset points', ha='left', fontsize=9.5,
                 color=S2, fontweight='bold')
    axL.annotate('基准线 = 1.0 倍\n（两周六完全一样）', xy=(17.5, 1.0),
                 xytext=(0, -30), textcoords='offset points', ha='center',
                 fontsize=9, color=MUTED)
    axL.set_ylim(0.8, 1.6)
    axL.set_xticks(range(0, 24, 3))
    axL.set_xticklabels([f'{h}点' for h in range(0, 24, 3)], fontsize=9)
    axL.set_ylabel('12-02 人数 ÷ 11-25 人数', fontsize=9.5, color=MUTED)
    title(axL, '跳涨是"整体等比例抬高"', '若是限时活动，某个小时会突然翘起来——没有')

    # 右：每天的新面孔占比
    d = r5.iloc[1:].reset_index(drop=True)   # 11-25 必然 100%，剔除
    d['lab'] = d['日期'].astype(str).str.slice(5)
    x = range(len(d))
    axR.bar(x, d['新面孔占比'], width=0.6, color=S2, zorder=3)
    for i, v in enumerate(d['新面孔占比']):
        if v > 0.5:
            axR.text(i, v + 0.7, f'{v:.0f}%', ha='center', fontsize=9,
                     color=INK, fontweight='bold')
    axR.annotate('12-02 当天 9.7 万活跃用户里\n只有 2 人是没出现过的\n'
                 '→ 排除"拉新"，但真正原因是\n　　次日查到的覆盖率断崖（98%）',
                 xy=(7, 0.0), xytext=(5.0, 13.5), ha='center', fontsize=9.2,
                 color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    axR.set_xticks(list(x))
    axR.set_xticklabels(d['lab'], fontsize=9)
    axR.set_ylim(0, 26)
    axR.set_ylabel('当日活跃用户中"新面孔"占比（%）', fontsize=9.5, color=MUTED)
    axR.set_xlabel('（11-25 是窗口第一天，必然 100%，已剔除）',
                   fontsize=9, color=MUTED, labelpad=10)
    title(axR, '先排除"拉新"这一条', '但不是"老用户回流"——是数据异常，见 `03_时间规律.md`')

    save(fig, 's3_spike_drilldown.png')


if __name__ == '__main__':
    chart_hourly_shape()
    chart_spike_drilldown()
    print('S3 图完成。')
