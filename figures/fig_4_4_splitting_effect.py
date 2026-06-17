#!/usr/bin/env python
"""
Figure 4.4 — Dumbbell plot: act-level H_loc before vs. after splitting.

One row per split act, sorted by H_improvement descending.
Top row shows the network-wide mean (all 32 acts, before / all 53 acts, after).

Data: splits.json  (root copy produced by nb05)
"""

import os
import json
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

plt.rcParams.update({
    'font.family':      'serif',
    'figure.facecolor': 'white',
    'axes.facecolor':   'white',
    'pdf.fonttype':      42,
    'ps.fonttype':       42,
})

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)

COL_BEF = '#e09020'   # orange — before splitting
COL_AFT = '#2a7fc9'   # blue   — after  splitting

# ── Data ──────────────────────────────────────────────────────────────────────
with open(os.path.join(ROOT_DIR, 'splits.json'), 'r', encoding='utf-8') as fh:
    sp = json.load(fh)

meta   = sp['meta']
splits = sp['splits']


def fmt_celex(celex: str) -> str:
    """Convert slug to human-readable act label."""
    m = re.match(r'3(\d{4})L(\d{4})', celex)
    if m:
        return f'Dir. {m.group(1)}/{int(m.group(2))}/UE'
    parts = celex.split('_')
    if len(parts) == 3:
        tipo, num, anno = parts
        tipo_map = {
            'dlgs': 'D.Lgs.', 'dpr': 'D.P.R.',
            'dl':   'D.L.',   'l':   'L.',    'dm': 'D.M.',
        }
        return f'{tipo_map.get(tipo, tipo.upper())} {num}/{anno}'
    return celex


# Sort by H_improvement descending (largest reduction first = top of chart)
rows = sorted(splits.values(), key=lambda s: s['H_improvement'], reverse=True)
labels   = [fmt_celex(s['celex'])      for s in rows]
h_before = [float(s['H_before'])       for s in rows]
h_after  = [float(s['H_after'])        for s in rows]
h_improv = [float(s['H_improvement'])  for s in rows]

net_bef  = float(meta['H_local_before'])
net_aft  = float(meta['H_local_after'])
net_imp  = float(meta['H_local_improvement'])

N     = len(rows)
# y positions: rows[0] (highest) → top (y = N-1), rows[-1] → bottom (y = 0)
y_act = list(range(N - 1, -1, -1))
Y_NET = N + 0.8

print(f'Acts: {N}  network mean: {net_bef:.4f} -> {net_aft:.4f}  (-{net_imp:.1%})')
for lbl, hb, ha, hi in zip(labels, h_before, h_after, h_improv):
    print(f'  {lbl:<22}  {hb:.3f} -> {ha:.3f}  (-{hi:.1%})')

# ── Figure ────────────────────────────────────────────────────────────────────
fig_h = 0.44 * (N + 2) + 1.4
fig, ax = plt.subplots(figsize=(6.5, fig_h))

# Background stripe for network-mean row
ax.axhspan(Y_NET - 0.48, Y_NET + 0.48, color='#f0f0f0', zorder=0)

# Per-act dumbbells
for ypos, hb, ha, hi in zip(y_act, h_before, h_after, h_improv):
    ax.plot([ha, hb], [ypos, ypos], color='#cccccc', lw=1.4, zorder=1)
    ax.scatter([hb], [ypos], color=COL_BEF, s=52, zorder=3, linewidths=0)
    ax.scatter([ha], [ypos], color=COL_AFT, s=52, zorder=3, linewidths=0)
    ax.text(hb + 0.013, ypos, f'−{hi:.1%}',
            va='center', ha='left', fontsize=7.0, fontfamily='serif', color='#444444')

# Network-mean row
ax.plot([net_aft, net_bef], [Y_NET, Y_NET], color='#cccccc', lw=1.6, zorder=1)
ax.scatter([net_bef], [Y_NET], color=COL_BEF, s=64, marker='D', zorder=3, linewidths=0)
ax.scatter([net_aft], [Y_NET], color=COL_AFT, s=64, marker='D', zorder=3, linewidths=0)
ax.text(net_bef + 0.013, Y_NET, f'−{net_imp:.1%}',
        va='center', ha='left', fontsize=7.5, fontfamily='serif',
        color='#222222', fontweight='bold')

# Y-axis ticks: acts + network mean
all_y      = [Y_NET] + y_act
all_labels = ['Network mean'] + labels
ax.set_yticks(all_y)
ax.set_yticklabels(all_labels, fontsize=8.0, fontfamily='serif')
for tick, lbl in zip(ax.get_yticklabels(), all_labels):
    if lbl == 'Network mean':
        tick.set_fontweight('bold')
        tick.set_fontsize(8.5)

# X-axis
x_max = max(h_before + [net_bef]) + 0.17
ax.set_xlabel('Act-level hybridity $H_{\\mathrm{loc}}$', fontsize=9, fontfamily='serif')
ax.set_xlim(-0.02, x_max)
ax.set_ylim(-0.65, Y_NET + 0.6)
ax.tick_params(axis='x', labelsize=8)

# Legend
ax.legend(handles=[
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COL_BEF,
           markersize=7, label='$H_{\\mathrm{loc}}$ before splitting'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=COL_AFT,
           markersize=7, label='$H_{\\mathrm{loc}}$ after splitting'),
], loc='lower left', fontsize=8.0, frameon=False)

ax.spines['left'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_color('#aaaaaa')
ax.spines['bottom'].set_linewidth(0.8)
ax.tick_params(axis='y', length=0, pad=6)

fig.tight_layout()

# ── Save ──────────────────────────────────────────────────────────────────────
for ext in ('pdf', 'png'):
    path = os.path.join(SCRIPT_DIR, f'fig_4_4_splitting_effect.{ext}')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    print(f'Saved: {path}')
plt.close(fig)
