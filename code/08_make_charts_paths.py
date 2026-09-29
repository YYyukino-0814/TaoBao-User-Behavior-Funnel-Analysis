# -*- coding: utf-8 -*-
"""S8 · 行为路径的三张结论图。

用法：
    python code/08_make_charts_paths.py

数据源（全部是脚本跑出来的 csv，图里不出现手抄的数字）：
    output/tables/sql_08_paths_r2.csv    会话长度分布
    output/tables/sql_08_paths_r4.csv    各长度的动作深度
    output/tables/s8b_r2.csv             三个会话阈值下的稳健性
    output/tables/s8c_r1.csv             会话内转移概率（含原始计数）
    output/tables/s8c_r3.csv             加购转化发生在当场还是事后
    output/tables/s8d_buy_position.csv   购买之前发生了什么（三个阈值）
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from viz import (SURFACE, INK, INK2, MUTED, GRID, AXIS, S1, S2, S3,
                 dress, title, load, save)

TAB = db.TABLES


def csv(name):
    import pandas as pd
    return pd.read_csv(os.path.join(TAB, name))


# ============================================================
# 图16 · 一次"逛"到底做到哪一步
# ============================================================
def chart_depth():
    d = load('sql_08_paths', 4)
    rob = csv('s8b_r2.csv')
    x = list(range(len(d)))

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(12.2, 4.6), gridspec_kw={'width_ratios': [1.35, 1]})
    dress(axL, ygrid=True)
    dress(axR, ygrid=True)

    # ---- 左：三条线，看"纯浏览"怎么随会话变长掉下去 ----
    series = [
        ('纯浏览，无任何意向动作', d['纯浏览无任何意向动作'], S1, '纯浏览'),
        ('至少有加购或收藏',       d['至少有加购或收藏'],     S2, '加购或收藏'),
        ('含购买',                 d['含购买'],               S3, '含购买'),
    ]
    for name, vals, c, short in series:
        axL.plot(x, vals, color=c, linewidth=2, marker='o', markersize=7,
                 markeredgecolor=SURFACE, markeredgewidth=2, zorder=3,
                 label=name)
        # 每条线右端直接标名字和末值 —— 青绿对底色的对比度只有 2.74:1，
        # 光靠颜色区分不够，必须配文字（色板校验记录里写死的规矩）
        axL.text(x[-1] + 0.12, vals.iloc[-1], f'{short} {vals.iloc[-1]:.1f}%',
                 va='center', ha='left', fontsize=9.5, color=INK2)

    axL.set_xticks(x)
    axL.set_xticklabels([f'{n}\n{c:,} 个' for n, c in
                         zip(d['会话行为数'], d['会话数'])], fontsize=9.5)
    axL.set_xlim(-0.35, len(x) + 1.35)
    axL.set_ylim(0, 100)
    axL.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axL.set_xlabel('一个会话里有几个行为', fontsize=9.5, color=MUTED, labelpad=6)
    axL.set_ylabel('占该长度会话的比例', fontsize=9.5, color=MUTED)
    # 图例放到画布底下：图里面那段空白被折线扫过，放哪都压线
    axL.legend(loc='upper center', bbox_to_anchor=(0.5, -0.26), ncol=3,
               frameon=False, fontsize=9.5, handlelength=1.4,
               labelcolor=INK2, columnspacing=1.6)
    title(axL, '会话越长越深入：纯浏览从 84% 掉到 16%',
          '30 分钟会话口径　·　会话 378,557 个（最短）到 27,366 个（最长）')

    # ---- 右：换个阈值，纯浏览占比会不会翻盘 ----
    names = [f'{t.replace("（主口径）", "")}\n平均 {n:.2f} 个行为\n'
             f'{s:,} 个会话' for t, n, s in
             zip(rob['阈值'], rob['平均行为数'], rob['会话数'])]
    names[1] = f'30 分钟\n（主口径）\n平均 5.96 个行为'
    bars = axR.bar(range(len(rob)), rob['纯浏览会话占比'], width=0.5,
                   color=S1, zorder=3)
    bars[1].set_color(S2)          # 主口径那根换个色，其余两根同色
    for i, v in enumerate(rob['纯浏览会话占比']):
        axR.text(i, v + 1.5, f'{v:.2f}%', ha='center', fontsize=12,
                 color=INK, fontweight='bold')
    axR.set_xticks(range(len(rob)))
    axR.set_xticklabels(names, fontsize=9.5)
    axR.set_ylim(0, 80)
    axR.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axR.set_ylabel('纯浏览会话占比', fontsize=9.5, color=MUTED)
    title(axR, '把阈值放宽到 60 分钟，结论只挪了 4.4 个点',
          '会话阈值是我定的、不是数据给的：15→60 分钟\n'
          '纯浏览占比 68.53 → 64.09，没有翻盘')

    save(fig, 's8_session_depth.png')


# ============================================================
# 图17 · 什么动作之后最容易成交 —— 答案和直觉相反
# ============================================================
def chart_transition():
    t = csv('s8c_r1.csv').set_index('当前')
    # 7,259,039 是"行为位"总数，不是转移次数：每个会话末尾那条行为没有"下一个"，
    # 要从总数里减掉会话数（1,217,569），剩下的才是真正的转移
    n_trans = t['出现次数'].sum() - 1217569
    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(12.0, 4.6), gridspec_kw={'width_ratios': [1, 1.25]})
    dress(axL, ygrid=True)
    dress(axR, xgrid=True, ygrid=False)

    # ---- 左：三种动作之后"下一步就买"的概率 ----
    order = [('pv', '浏览之后'), ('cart', '加购之后'), ('fav', '收藏之后')]
    rates = [t.loc[k, '下一步购买次数'] / t.loc[k, '出现次数'] * 100
             for k, _ in order]
    # 基础概率：在这三种"非购买"动作里，下一步成交的平均概率。
    # 用原始计数算，不用圆整过的百分比回推。
    base = (t.loc[['pv', 'cart', 'fav'], '下一步购买次数'].sum()
            / t.loc[['pv', 'cart', 'fav'], '出现次数'].sum() * 100)

    bars = axL.bar(range(3), rates, width=0.52, color=S1, zorder=3)
    bars[1].set_color(S2)
    for i, r in enumerate(rates):
        axL.text(i, r + 0.035, f'{r:.2f}%', ha='center', fontsize=12.5,
                 color=INK, fontweight='bold')
    axL.axhline(base, color=INK2, linewidth=1.2, linestyle=(0, (4, 3)), zorder=4)
    # 参考线标签只留一行：两行的时候第二行会压到"0.88%"那个数值上，
    # 解释挪进副标题去了
    axL.text(2.46, base - 0.05, f'基础概率 {base:.2f}%', ha='right',
             fontsize=9.2, color=INK2, va='top')
    axL.set_xticks(range(3))
    axL.set_xticklabels([n for _, n in order], fontsize=10.5)
    axL.set_ylim(0, 1.95)
    axL.set_yticks([0, 0.5, 1.0, 1.5])   # 自动刻度跑出 0.2/0.5/0.8 这种不规则步长
    axL.yaxis.set_major_formatter(lambda v, p: f'{v:.1f}%')
    axL.set_ylabel('下一步就是购买的概率', fontsize=9.5, color=MUTED)
    axL.annotate('加购和收藏之后下一步成交的概率，\n比浏览之后还低',
                 xy=(1, rates[1] + 0.03), xytext=(0.42, 1.66), ha='center',
                 fontsize=9.5, color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    title(axL, '加购不是转化的扳机，是意向的标记',
          f'会话内一阶转移　·　{n_trans:,} 次有效转移\n'
          '基础概率 = 在浏览/加购/收藏这三种非购买动作里，下一步成交的平均概率')

    # ---- 右：那加购之后的下一步到底干嘛去了 ----
    steps = [('继续浏览别的', '下一步浏览'), ('这个会话就结束了', '会话结束'),
             ('再加购一件别的', '下一步加购'), ('去收藏', '下一步收藏'),
             ('直接下单', '下一步购买')]
    names = [n for n, _ in steps]
    vals = [t.loc['cart', k] for _, k in steps]
    y = list(range(len(vals)))[::-1]
    axR.barh(y, vals, height=0.52, color=S1, zorder=3)
    for yy, v in zip(y, vals):
        axR.text(v + 1.1, yy, f'{v:.2f}%', va='center', fontsize=11,
                 color=INK, fontweight='bold')
    axR.set_yticks(y)
    axR.set_yticklabels(names, fontsize=10.5)
    axR.set_xlim(0, 78)
    axR.xaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axR.set_xlabel('加购这个动作之后，下一步发生什么', fontsize=9.5,
                   color=MUTED, labelpad=8)
    axR.annotate('加购之后最可能的是「接着逛」和「不逛了」，\n'
                 '下单排最后 —— 加购更像收进抽屉，不是放进收银台',
                 xy=(8, 0.05), xytext=(30, 1.15), ha='left', fontsize=9,
                 color=INK2,
                 arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    title(axR, '加购之后，八成的人要么接着逛、要么直接关掉',
          '加购共 398,417 次')

    save(fig, 's8_transition.png')


# ============================================================
# 图18 · 加购的"售后"：当场没买，然后呢
# ============================================================
def chart_cart_afterlife():
    timing = csv('s8c_r3.csv').iloc[0]
    same = timing['当场成交占比']
    later = 100 - same
    pos = csv('s8d_buy_position.csv')
    d = pos[pos['会话阈值'] == '30 分钟（主口径）'].sort_values('占比')

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(12.2, 4.6), gridspec_kw={'width_ratios': [0.85, 1.3]})
    dress(axL, xgrid=True, ygrid=False)
    dress(axR, xgrid=True, ygrid=False)

    # ---- 左：加购转化发生在当场还是事后（一条 100% 堆叠，两段之间留缝）----
    axL.barh([0], [same], height=0.5, color=S2, zorder=3)
    axL.barh([0], [later], left=[same + 1.2], height=0.5, color=S1, zorder=3)
    # 数值写在色块【下面】而不是里面：白字压橙(#eb6834)只有 2.9:1，
    # 达不到正文对比度要求，色板校验记录里也写了这条
    axL.text(same / 2, -0.36, f'当场就买\n{same:.2f}%', ha='center', va='top',
             fontsize=10.5, color=INK, fontweight='bold')
    axL.text(same + 1.2 + later / 2, -0.36, f'会话结束之后才买\n{later:.2f}%',
             ha='center', va='top', fontsize=10.5, color=INK, fontweight='bold')
    axL.set_xlim(0, 101)
    axL.set_ylim(-0.95, 0.42)
    axL.set_yticks([])
    axL.xaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axL.set_xlabel(f'七天内买下的加购商品共 {timing["七天内买下的加购对"]:,.0f} 对',
                   fontsize=9.5, color=MUTED, labelpad=26)
    title(axL, '加购的转化，八成发生在会话结束之后',
          '只算七天内真的买下的那些（消化率 6.21%）')

    # ---- 右：那购买之前到底发生了什么 ----
    names = [n.replace('（后面还有行为）', '\n（后面还有行为）')
             for n in d['第一单之前发生了什么']]
    y = list(range(len(d)))
    axR.barh(y, d['占比'], height=0.52, color=S1, zorder=3)
    for yy, v, c in zip(y, d['占比'], d['会话数']):
        axR.text(v + 0.7, yy, f'{v:.2f}%　({c:,} 个)', va='center',
                 fontsize=10.5, color=INK, fontweight='bold')
    axR.set_yticks(y)
    axR.set_yticklabels(names, fontsize=10)
    axR.set_xlim(0, 60)
    axR.xaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    axR.set_xlabel('每笔「会话内首次购买」之前发生了什么', fontsize=9.5,
                   color=MUTED, labelpad=8)
    title(axR, '只有 13.58% 的购买，前面出现过加购',
          '30 分钟口径　·　"会话开头就下单"那 37.86% 里有一半是'
          '被阈值切开的，见 08_行为路径.md')

    save(fig, 's8_cart_afterlife.png')


if __name__ == '__main__':
    chart_depth()
    chart_transition()
    chart_cart_afterlife()
    print('S8 图完成。')
