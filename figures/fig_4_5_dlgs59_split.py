#!/usr/bin/env python
"""
Figure 4.5 — D.Lgs. 59/2010: Lamfalussy tier composition before and after splitting.

Four horizontal stacked-bar rows:
  Row 0  Intact act   — aggregate lamf distribution over all 86 articles
  Row 1  L1 block     — general framework  (36 art.)
  Row 2  L23 block    — operational rules  (39 art.)
  Row 3  L4 block     — enforcement        (11 art.)

Data:
  splits.json                       → block lamf_avg, H_block, n_articles
  data/output/appalti_it/nodes_hybridity.csv  → intact-act lamf, H, n counts
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

plt.rcParams.update({
    'font.family':      'serif',
    'figure.facecolor': 'white',
    'axes.facecolor':   'white',
    'pdf.fonttype':      42,
    'ps.fonttype':       42,
})

TIER_NAMES   = ['L1', 'L2', 'L3', 'L4']
TIER_HEX     = {'L1': '#4f8ef7', 'L2': '#b090e0', 'L3': '#3a9c6e', 'L4': '#c85c3a'}
TIER_LABELS  = ['L1 — Framework', 'L2 — Operational',
                'L3 — Technical standards', 'L4 — Enforcement']
BLOCK_TITLES = {
    'L1':   'L1 block — general framework',
    'L23':  'L2/L3 block — operational rules',
    'L234': 'L2/L3/L4 block — operational rules',
    'L4':   'L4 block — enforcement',
}
CELEX = 'dlgs_59_2010'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)

# ── Data ──────────────────────────────────────────────────────────────────────
with open(os.path.join(ROOT_DIR, 'splits.json'), 'r', encoding='utf-8') as fh:
    sp = json.load(fh)

hyb     = pd.read_csv(os.path.join(ROOT_DIR, 'data', 'output', 'appalti_it', 'nodes_hybridity.csv'))
act_row = hyb[hyb['celex'] == CELEX].iloc[0]

n_sub   = int(act_row.get('n_articles',   0))
n_uns   = int(act_row.get('n_unassigned', 0))
n_total = n_sub + n_uns
H_intact = float(sp['splits'][CELEX]['H_before'])

# Intact act lamf — normalise to 100 %
intact_vals = [float(act_row[f'lamf_{k}']) for k in TIER_NAMES]
s = sum(intact_vals)
if s > 0:
    intact_vals = [v / s * 100 for v in intact_vals]

# Build row list
rows = []
rows.append({
    'label': f'Intact act\n({n_total} art.)',
    'bold':  True,
    'vals':  intact_vals,
    'H':     H_intact,
})
for b in sp['splits'][CELEX]['blocks']:
    pk    = b['partition_key']
    title = BLOCK_TITLES.get(pk, f'{pk} block')
    n     = b['n_articles']
    vals  = [float(b['lamf_avg'].get(k, 0)) for k in TIER_NAMES]
    # Normalise each block's lamf to 100 %
    s = sum(vals)
    if s > 0:
        vals = [v / s * 100 for v in vals]
    rows.append({
        'label': f'{title}\n({pk}, {n} art.)',
        'bold':  False,
        'vals':  vals,
        'H':     float(b['H_block']),
    })

print(f'Intact act: n={n_total}  H={H_intact:.4f}  lamf={[round(v,1) for v in intact_vals]}')
for rd in rows[1:]:
    label_short = rd['label'].split('\n')[0]
    print(f'  {label_short:<35} H={rd["H"]:.4f}  lamf={[round(v,1) for v in rd["vals"]]}')

# ── Figure ────────────────────────────────────────────────────────────────────
N   = len(rows)
fig, ax = plt.subplots(figsize=(7.5, 0.80 * N + 1.8))

BAR_H    = 0.54
# y-positions: intact at top, then blocks descending
y_pos = list(range(N - 1, -1, -1))   # [N-1, N-2, ..., 0]

for rd, yp in zip(rows, y_pos):
    left = 0.0
    for k in TIER_NAMES:
        v = rd['vals'][TIER_NAMES.index(k)]
        if v <= 0:
            left += v
            continue
        ax.barh(yp, v, height=BAR_H, left=left, color=TIER_HEX[k], zorder=2)
        if v >= 6.5:
            ax.text(left + v / 2, yp,
                    f'{v:.0f}%',
                    ha='center', va='center',
                    fontsize=8.5, fontfamily='serif',
                    color='white', fontweight='semibold', zorder=3)
        left += v

    # H label on right
    ax.text(103, yp, f'H = {rd["H"]:.3f}',
            ha='left', va='center', fontsize=8.0, fontfamily='serif',
            color='#222222',
            fontweight='bold' if rd['bold'] else 'normal')

    # Row label on left
    ax.text(-2, yp, rd['label'],
            ha='right', va='center', fontsize=8.0, fontfamily='serif',
            color='#111111',
            fontweight='bold' if rd['bold'] else 'normal')

# Thin separator between intact row and blocks
ax.axhline(y=y_pos[0] - 0.48, color='#cccccc', linewidth=0.8, zorder=1)

# ── Axes ──────────────────────────────────────────────────────────────────────
ax.set_xlim(-2, 116)
ax.set_ylim(-0.65, N - 0.35)
ax.set_xlabel('Lamfalussy tier composition', fontsize=9.5, fontfamily='serif')
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'],
                   fontsize=8.0, fontfamily='serif')
ax.set_yticks([])
for sp in ['top', 'right', 'left']:
    ax.spines[sp].set_visible(False)
ax.spines['bottom'].set_color('#aaaaaa')
ax.spines['bottom'].set_linewidth(0.8)

# Legend
legend_patches = [mpatches.Patch(color=TIER_HEX[k], label=lbl)
                  for k, lbl in zip(TIER_NAMES, TIER_LABELS)]
ax.legend(handles=legend_patches, loc='lower center', ncol=2,
          fontsize=7.5, frameon=False, bbox_to_anchor=(0.42, -0.22))

fig.tight_layout()

# ── Save ──────────────────────────────────────────────────────────────────────
for ext in ('pdf', 'png'):
    path = os.path.join(SCRIPT_DIR, f'fig_4_5_dlgs59_split.{ext}')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    print(f'Saved: {path}')
plt.close(fig)
