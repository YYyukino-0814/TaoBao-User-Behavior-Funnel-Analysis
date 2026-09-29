# -*- coding: utf-8 -*-
"""S6 · 类目转化差异的统计检验 + 两张结论图。

用法：
    python code/06_chi_square.py

要做四件事，顺序不能反：
  1. 卡方检验：类目和"买不买"到底相不相关         -> p 值
  2. 效应量 Cramér's V：相关有多强                 -> p 值之外必须有这个
  3. 每个类目转化率的 95% 置信区间                 -> 看"显著"这个词在这里多廉价
  4. 分半复现：前后两半窗口的类目排序是否一致       -> 比显著性好用的稳健性证据

数据源：sql/sql_06_category.sql 跑出来的 output/tables/sql_06_category_r*.csv
"""
import os
import sys

import numpy as np
import pandas as pd
import scipy.stats as st

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from viz import (SURFACE, INK, INK2, MUTED, AXIS, S1, S2, S3, RESID,
                 dress, title, load, save)


def wilson_ci(k, n, z=1.959964):
    """Wilson 置信区间。比正态近似稳，小比例时不会算出负数下界。"""
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z / d * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return center - half, center + half


# ============================================================
# 统计检验
# ============================================================
def run_tests():
    d = load('sql_06_category', 2)
    table = d[['购买', '未购买']].to_numpy()
    n = table.sum()

    chi2, p, dof, expected = st.chi2_contingency(table)
    # 40 行 × 2 列，min(r-1, c-1) = 1
    cramers_v = np.sqrt(chi2 / (n * min(table.shape[0] - 1, table.shape[1] - 1)))

    # 行间转化率的最大最小之比
    rate = d['转化率']
    spread = rate.max() / rate.min()

    # 每个类目的 95% CI 宽度（这是"显著"有多廉价的关键）
    widths = []
    for k, tot in zip(d['购买'], d['合计']):
        lo, hi = wilson_ci(k, tot)
        widths.append((hi - lo) * 100)

    print('=' * 62)
    print('S6 · 类目转化差异的统计检验')
    print('=' * 62)
    print(f'参与检验的类目数        {len(d)}')
    print(f'总样本（人 × 类目配对）  {n:,}')
    print()
    print(f'卡方统计量 chi2         {chi2:,.1f}')
    print(f'自由度 dof              {dof}')
    print(f'p 值                    {p:.3e}')
    print(f'Cramér\'s V（效应量）     {cramers_v:.4f}')
    print()
    print(f'转化率范围              {rate.min():.2f}% ~ {rate.max():.2f}%'
          f'（相差 {spread:.1f} 倍）')
    print(f'95% 置信区间的宽度      中位数 {np.median(widths):.2f} 个百分点，'
          f'最大 {max(widths):.2f}')
    print()
    print('解读：p 值小到没有意义（样本量太大），V 才是要看的那个数。')
    print('      CI 宽度中位数只有 %.2f 个百分点 —— 意味着任意两个类目的' % np.median(widths))
    print('      转化率只要差超过 1 个百分点，卡方就会判为"显著"。')
    print()

    # ---- 分半复现 ----
    s = load('sql_06_category', 5).dropna()
    rho, p_rho = st.spearmanr(s['前半段转化率'], s['后半段转化率'])
    pear, _ = st.pearsonr(s['前半段转化率'], s['后半段转化率'])
    rank_a = s['前半段转化率'].rank(ascending=False)
    rank_b = s['后半段转化率'].rank(ascending=False)
    top10_a = set(s.loc[rank_a <= 10, '类目'])
    top10_b = set(s.loc[rank_b <= 10, '类目'])
    overlap = len(top10_a & top10_b)

    print('-' * 62)
    print(f'分半复现（{len(s)} 个类目，前后各约 4 天）')
    print(f'Spearman 秩相关          {rho:.3f}  (p = {p_rho:.2e})')
    print(f'Pearson 相关             {pear:.3f}')
    print(f'前后两半"转化率 Top 10"的重合个数  {overlap} / 10')
    print('-' * 62)

    return {
        '表': d,
        'chi2': chi2,
        'p': p,
        'V': cramers_v,
        'ci宽度中位数': float(np.median(widths)),
        '分半秩相关': rho,
        'top10重合': overlap,
        'top10总数': 10,
    }


# ============================================================
# 图12 · 类目转化率的分布，以及那条窄到看不见的置信区间
# ============================================================
def chart_category_spread(d, ci_median, v):
    d = d.sort_values('转化率').reset_index(drop=True)
    los, his = [], []
    for k, tot in zip(d['购买'], d['合计']):
        lo, hi = wilson_ci(k, tot)
        los.append(lo * 100)
        his.append(hi * 100)

    fig, ax = plt.subplots(figsize=(9.0, 7.4))
    dress(ax, xgrid=True, ygrid=False)

    y = list(range(len(d)))
    ax.barh(y, d['转化率'], height=0.66, color=S1, zorder=3)
    # 置信区间：宽度只有零点几个百分点，画上去几乎看不见 —— 这正是要展示的
    ax.errorbar(d['转化率'], y,
                xerr=[d['转化率'] - los, np.array(his) - d['转化率']],
                fmt='none', ecolor=INK, elinewidth=1.2, capsize=2.5, zorder=4)

    # 注意：循环变量不能叫 v，否则会盖掉传进来的 Cramér's V（参数同名会串）
    for i, (rate, _tot) in enumerate(zip(d['转化率'], d['合计'])):
        ax.text(rate + 0.42, i, f'{rate:.2f}%', va='center', fontsize=8.6,
                color=INK, fontweight='bold')
    ax.set_yticks(y)
    ax.set_yticklabels([f'类目 {c}' for c in d['类目']], fontsize=8.4)
    ax.set_xlim(0, 18.5)
    ax.set_xticks([0, 3, 6, 9, 12, 15, 18])
    ax.set_xlabel('浏览过该类目的人里，最终买过该类目的人占比',
                  fontsize=9.5, color=MUTED, labelpad=10)
    ax.xaxis.set_major_formatter(lambda x, p: f'{x:.0f}%')

    ax.annotate(f'最低 {d["转化率"].iloc[0]:.2f}%',
                xy=(d['转化率'].iloc[0], 0), xytext=(4.6, 1.4),
                fontsize=9.5, color=INK2,
                arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    ax.annotate(f'最高 {d["转化率"].iloc[-1]:.2f}%，相差 '
                f'{d["转化率"].iloc[-1] / d["转化率"].iloc[0]:.1f} 倍',
                xy=(d['转化率'].iloc[-1] * 0.94, len(d) - 2.0),
                xytext=(11.0, 30), ha='left', fontsize=9.5,
                color=INK2,
                arrowprops=dict(arrowstyle='-', color=AXIS, linewidth=1))
    ax.text(6.3, 3.0, '黑色短线 = 95% 置信区间，\n宽度中位数只有 '
                      f'{ci_median:.2f} 个百分点，\n窄到在这张图上几乎看不见\n'
                      '→ 任意两个类目差 1 个点就算"显著"',
            fontsize=9, color=INK2, va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor=SURFACE,
                      edgecolor=AXIS, linewidth=0.8))

    title(ax, f'类目之间的转化率差了 {d["转化率"].iloc[-1] / d["转化率"].iloc[0]:.0f} 倍，'
              '但"显著"这个词在这里不值钱',
          f'Top {len(d)} 类目（按浏览人数），人 × 类目粒度，窗口 11-25 ~ 12-01'
          f'　·　卡方 p 小到打印不出来，Cramér\'s V 只有 {v:.2f}')

    save(fig, 's6_category_spread.png')


# ============================================================
# 图13 · 分半复现：把窗口切成两半，类目排名还站得住吗
# ============================================================
def chart_split_half(rho, overlap):
    s = load('sql_06_category', 5).dropna()

    fig, ax = plt.subplots(figsize=(7.6, 6.2))
    dress(ax, xgrid=True, ygrid=True)

    lim = max(s['前半段转化率'].max(), s['后半段转化率'].max()) * 1.12
    ax.plot([0, lim], [0, lim], color=AXIS, linewidth=1, zorder=2)
    ax.text(lim * 0.72, lim * 0.79, '完全一致（y = x）', fontsize=9,
            color=MUTED, rotation=38, rotation_mode='anchor', ha='center')

    ax.scatter(s['前半段转化率'], s['后半段转化率'], s=58, color=S1,
               edgecolor=SURFACE, linewidth=1.6, zorder=4)

    # 标出前后差异最大的两个，供正文点名
    s = s.copy()
    s['偏离'] = (s['后半段转化率'] - s['前半段转化率']).abs()
    for _, row in s.nlargest(2, '偏离').iterrows():
        ax.annotate(f'类目 {int(row["类目"])}',
                    xy=(row['前半段转化率'], row['后半段转化率']),
                    xytext=(10, -12), textcoords='offset points',
                    fontsize=8.6, color=INK2)

    ticks = [0, 3, 6, 9, 12, 15, 18]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel('前半段（11-25 ~ 11-28）转化率', fontsize=9.5, color=MUTED,
                  labelpad=8)
    ax.set_ylabel('后半段（11-29 ~ 12-01）转化率', fontsize=9.5, color=MUTED,
                  labelpad=8)
    ax.xaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')
    ax.yaxis.set_major_formatter(lambda v, p: f'{v:.0f}%')

    title(ax, '类目排序两半之间几乎完全复现',
          f'每个点 = 一个类目　·　Spearman 秩相关 {rho:.3f}　·　'
          f'前后两半的 Top 10 重合 {overlap} / 10　·　点数 {len(s)}')

    save(fig, 's6_split_half.png')


if __name__ == '__main__':
    r = run_tests()
    chart_category_spread(r['表'], r['ci宽度中位数'], r['V'])
    chart_split_half(r['分半秩相关'], r['top10重合'])
    print('S6 完成。')
