# -*- coding: utf-8 -*-
"""S1 / S2 的结论图（matplotlib -> png）。

原则：这个脚本只负责"画"，不负责"算"。
所有数字都从 output/tables/ 里 run_sql.py 导出的 csv 读，
保证图和 SQL 结果永远一致——改了 SQL 重跑，图跟着变。

用法：
    python code/02_make_charts.py
"""
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from viz import (SURFACE, INK, INK2, MUTED, GRID, AXIS, S1, S2, S3, RESID,
                 ORD, dress, title, load)


# ============================================================
# 图1 · 行为结构：四种行为各占多少
# ============================================================
def chart_behavior_structure():
    df = load('sql_01_overview', 2)
    order = ['pv', 'cart', 'fav', 'buy']
    df = df.set_index('行为').loc[order].reset_index()

    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    y = range(len(df))[::-1]           # 浏览在最上面
    ax.barh(list(y), df['行数占比'], height=0.5, color=S1, zorder=3)

    for yy, pct, cnt, ppl in zip(y, df['行数占比'], df['行数'], df['人数']):
        ax.text(pct + 1.4, yy, f'{pct:.2f}%',
                va='center', ha='left', fontsize=10, color=INK, fontweight='bold')
        ax.text(pct + 11.5, yy, f'{cnt:,} 条 · {ppl:,} 人',
                va='center', ha='left', fontsize=9, color=MUTED)

    ax.set_yticks(list(y))
    ax.set_yticklabels(df['中文'], fontsize=11, color=INK2)
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xticklabels(['0', '20', '40', '60', '80', '100%'])
    ax.set_xlabel('占全部行为记录的比例', fontsize=9.5, color=MUTED, labelpad=8)

    title(ax, '浏览占了近九成，购买不到 2%',
          '四种行为的记录数占比（2017-11-25 ~ 12-03，1000 万行样本）')
    dress(ax, xgrid=True, ygrid=False)

    out = os.path.join(db.CHARTS, 's1_behavior_structure.png')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    print(f'图1 已存 {out}')


# ============================================================
# 图4 · 每日趋势：两个指标两张图，绝不叠双轴
# ============================================================
def chart_daily_trend():
    df = load('sql_01_overview', 3)
    df['dt'] = pd.to_datetime(df['日期']).dt.strftime('%m-%d')
    x = range(len(df))
    # 9 个点（下标 0~8）：11-25/26 和 12-02/03 是周六日
    weekend = [0, 1, 7, 8]
    # 12-02/12-03 查实为数据异常（覆盖率断崖），灰底压在上面，读作"这两天不作数"
    anomaly = [7, 8]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(8.6, 5.6), sharex=True,
        gridspec_kw={'height_ratios': [1.25, 1], 'hspace': 0.22})

    for ax in (ax1, ax2):
        for i in weekend:
            ax.axvspan(i - 0.5, i + 0.5, color=S1, alpha=0.055, zorder=0)
        for i in anomaly:
            ax.axvspan(i - 0.5, i + 0.5, color=MUTED, alpha=0.16, zorder=1)
        dress(ax, ygrid=True)

    # 上：活跃用户数
    ax1.plot(x, df['活跃用户数'], color=S1, linewidth=2, zorder=3)
    ax1.plot(x, df['活跃用户数'], 'o', color=S1, markersize=6,
             markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    ax1.set_ylim(60000, 108000)
    ax1.yaxis.set_major_formatter(lambda v, p: f'{v/10000:.0f}万')
    title(ax1, '活跃用户在 12-02 突然多三成 —— 后查实为数据异常',
          '上：每天有多少人来（活跃用户数）　下：来的人平均干了几件事（人均行为数）'
          '　·　浅蓝底 = 周末　·　灰底 = 这两天的活跃覆盖率跳到 98%（前 7 天 72~75%），已排除')
    for i in (0, 1, 7, 8):
        ax1.annotate(f'{df["活跃用户数"][i]/10000:.1f}万',
                     (i, df['活跃用户数'][i]), textcoords='offset points',
                     xytext=(0, 11 if i < 7 else 11), ha='center', fontsize=9.5,
                     color=INK, fontweight='bold')
    ax1.annotate('+31%', xy=(6.5, 86500), ha='center', va='center',
                 fontsize=10.5, color=INK, fontweight='bold', zorder=5,
                 bbox=dict(boxstyle='round,pad=0.28', facecolor=SURFACE,
                           edgecolor='none'))
    # 第一个周末没有抬升 —— 必须点出来，否则读者会以为"周末=涨"
    ax1.annotate('同为周末，11-26 只比周六高 1%', (1, df['活跃用户数'][1]),
                 textcoords='offset points', xytext=(6, -34), ha='center',
                 fontsize=9, color=MUTED)
    ax1.set_ylabel('活跃用户数', fontsize=9.5, color=MUTED)

    # 下：人均行为数
    ax2.plot(x, df['人均行为数'], color=S2, linewidth=2, zorder=3)
    ax2.plot(x, df['人均行为数'], 'o', color=S2, markersize=6,
             markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    ax2.set_ylim(13.4, 15.4)
    for i in (0, 8):
        ax2.annotate(f'{df["人均行为数"][i]:.2f}',
                     (i, df['人均行为数'][i]), textcoords='offset points',
                     xytext=(0, -16 if i == 0 else 11), ha='center',
                     fontsize=9.5, color=INK, fontweight='bold')
    ax2.annotate('9 天全程落在 13.95 ~ 14.89 之间，人数翻上去的那两天也没变',
                 xy=(4.4, 15.16), ha='center', va='center',
                 fontsize=9, color=MUTED)
    ax2.set_ylabel('人均行为数（次）', fontsize=9.5, color=MUTED)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(df['dt'], fontsize=9.5)

    out = os.path.join(db.CHARTS, 's1_daily_trend.png')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    print(f'图4 已存 {out}')


# ============================================================
# 图2 · 交易漏斗主线（序数蓝阶）
# ============================================================
def chart_funnel():
    r1 = load('sql_02_funnel', 1).iloc[0]
    r2 = load('sql_02_funnel', 2).iloc[0]

    stages = ['浏览过商品', '加购过商品', '加购且最终成交']
    vals = [int(r1['浏览人数']), int(r1['加购人数']), int(r1['加购且购买'])]
    rates = [None, r2['浏览到加购率'], r2['加购到购买率']]

    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    base = vals[0]
    for i, (name, v) in enumerate(zip(stages, vals)):
        y = len(stages) - 1 - i
        ax.barh(y, v, height=0.46, color=ORD[i], zorder=3)
        ax.text(-base * 0.02, y, name, va='center', ha='right',
                fontsize=11, color=INK2)
        ax.text(v + base * 0.012, y,
                f'{v:,} 人　{v / base * 100:.1f}%',
                va='center', ha='left', fontsize=11, color=INK, fontweight='bold')

    # 层与层之间的转化率，画在两层中间偏右
    for i in (1, 2):
        y_hi = len(stages) - i          # 上一层
        y_lo = y_hi - 1                 # 下一层
        ax.annotate(f'↓ {rates[i]:.1f}%',
                    xy=(vals[i] * 0.55 + vals[i - 1] * 0.45, (y_hi + y_lo) / 2),
                    ha='center', va='center', fontsize=10.5,
                    color=INK2, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.34', facecolor=SURFACE,
                              edgecolor=GRID, linewidth=0.8))

    ax.set_xlim(0, base * 1.14)
    ax.set_ylim(-0.6, len(stages) - 0.35)
    ax.set_yticks([])
    ax.set_xticks([])
    for side in ('top', 'right', 'left', 'bottom'):
        ax.spines[side].set_visible(False)
    ax.grid(False)

    title(ax, '漏斗两步的通过率几乎一样，没有单点卡点',
          '同一批用户逐层留存（去重人数）　·　分母 = 浏览过的 98,611 人'
          '　·　75.3% 与 71.9% 只差 3.4 个百分点')

    out = os.path.join(db.CHARTS, 's2_funnel.png')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    print(f'图2 已存 {out}')


# ============================================================
# 图3 · 全站用户去向：钱是从哪条岔路上走掉的
# ============================================================
def chart_destination():
    r1 = load('sql_02_funnel', 1).iloc[0]
    r3 = load('sql_02_funnel', 3).iloc[0]

    total = int(r1['总用户'])
    segs = [
        ('加购且购买', int(r3['加购且购买']), S1),
        ('加购未购买', int(r3['加购未购买']), S2),
        ('没加购直接买', int(r3['未加购直接购买']), S3),
        ('只逛不买', total - int(r3['加购且购买']) - int(r3['加购未购买'])
                     - int(r3['未加购直接购买']), RESID),
    ]

    fig, ax = plt.subplots(figsize=(9.2, 3.2))
    left = 0.0
    for name, v, c in segs:
        ax.barh(0, v, left=left, height=0.26, color=c,
                edgecolor=SURFACE, linewidth=2, zorder=3)
        if v / total >= 0.14:          # 装得下才写在里面
            ax.text(left + v / 2, 0, f'{v / total * 100:.1f}%',
                    ha='center', va='center', fontsize=10.5,
                    color='#ffffff' if c != RESID else INK,
                    fontweight='bold', zorder=4)
        left += v

    ax.set_xlim(0, total)
    ax.set_ylim(-0.55, 0.62)
    ax.set_yticks([])
    ax.set_xticks([])
    for side in ('top', 'right', 'left', 'bottom'):
        ax.spines[side].set_visible(False)

    # 图例兼数值表：每个值都能读到，不依赖颜色
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in segs]
    labels = [f'{n}　{v:,} 人（{v / total * 100:.1f}%）' for n, v, _ in segs]
    ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.12),
              ncol=4, frameon=False, fontsize=9.5, handlelength=1.1,
              handleheight=1.1, columnspacing=1.4, labelcolor=INK2)

    title(ax, f'99,020 个用户里，只有 {segs[0][1]:,} 人走完了「加购 → 购买」',
          '全部用户按最终走到哪一步拆开看（去重人数，同一人只算一次）')

    out = os.path.join(db.CHARTS, 's2_user_destination.png')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    print(f'图3 已存 {out}')


# ============================================================
# 图5 · 深水区：加购的商品，最后到底有没有被买走
# ============================================================
def chart_cart_item_fate():
    r4 = load('sql_02_funnel', 4).iloc[0]
    r6 = load('sql_02_funnel', 6)

    n_all = int(r4['加购商品项数'])
    n_same = int(r4['买了同款'])
    n_cat = int(r4['买了同款或同类目'])
    segs = [
        ('买了同款', n_same, S1),
        ('买了同类目的其他商品', n_cat - n_same, S3),
        ('什么也没买', n_all - n_cat, RESID),
    ]

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(11.6, 4.3), gridspec_kw={'width_ratios': [1, 1.25]})

    # 左：加购商品的三条去向
    left = 0.0
    for name, v, c in segs:
        axL.barh(0, v, left=left, height=0.34, color=c,
                 edgecolor=SURFACE, linewidth=2, zorder=3)
        if v / n_all >= 0.10:
            axL.text(left + v / 2, 0, f'{v / n_all * 100:.1f}%', ha='center',
                     va='center', fontsize=12, zorder=4, fontweight='bold',
                     color='#ffffff' if c != RESID else INK)
        left += v
    axL.set_xlim(0, n_all)
    axL.set_ylim(-0.5, 0.5)
    axL.set_xticks([])
    axL.set_yticks([])
    for s in ('top', 'right', 'left', 'bottom'):
        axL.spines[s].set_visible(False)
    # 图例当数值表用：每个数都读得到，不依赖颜色
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, _, c in segs]
    labels = [f'{n}　{v:,} 项　（{v / n_all * 100:.1f}%）' for n, v, _ in segs]
    axL.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.02),
               ncol=1, frameon=False, fontsize=10, handlelength=1.1,
               handleheight=1.1, labelcolor=INK2, borderpad=0)
    title(axL, f'加进购物车的 {n_all / 10000:.0f} 万件商品，\n八成最后什么也没发生',
          '按 (用户, 商品) 配对统计')

    # 右：窗口截断检验
    d = r6.copy()
    d['剩余跟进天数'] = [8, 7, 6, 5, 4, 3, 2, 1, 0]
    x = range(len(d))
    axR.bar(x, d['同款成交率'], width=0.62, color=S2, zorder=3)
    for i, (v, days) in enumerate(zip(d['同款成交率'], d['剩余跟进天数'])):
        axR.text(i, v + 0.22, f'{v:.1f}', ha='center', fontsize=9.5,
                 color=INK, fontweight='bold')
        axR.text(i, -0.62, f'{days}天', ha='center', fontsize=8.5, color=MUTED)
    axR.set_ylim(0, 10.9)
    axR.set_xticks([])
    axR.set_ylabel('该日加购商品的同款成交率（%）', fontsize=9.5, color=MUTED)
    axR.set_xlabel('加购日期（下方数字 = 此后还有几天可以买）',
                   fontsize=9.5, color=MUTED, labelpad=16)
    dress(axR, ygrid=True)
    axR.annotate('最后一天加购的 2.25%：不是没人买，是没时间买了',
                 xy=(8, 2.25), xytext=(7.0, 9.9), fontsize=9.2, color=INK2,
                 ha='center',
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    title(axR, '6.47% 是被窗口截断压低的',
          '所以真实量级应看前几天：8.2 ~ 8.6%')

    out = os.path.join(db.CHARTS, 's2_cart_item_fate.png')
    fig.tight_layout()
    fig.savefig(out, bbox_inches='tight')
    plt.close(fig)
    print(f'图5 已存 {out}')


if __name__ == '__main__':
    os.makedirs(db.CHARTS, exist_ok=True)
    chart_behavior_structure()
    chart_daily_trend()
    chart_funnel()
    chart_destination()
    chart_cart_item_fate()
    print('全部完成。')
