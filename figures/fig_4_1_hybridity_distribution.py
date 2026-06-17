#!/usr/bin/env python
"""
Figure 4.1 — Violin + strip plot of act-level local hybridity H_loc.

Data: data/output/appalti_it/nodes_hybridity.csv  (hybridity_score column)
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
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

# ── Data ──────────────────────────────────────────────────────────────────────
hyb = pd.read_csv(os.path.join(ROOT_DIR, 'data', 'output', 'appalti_it', 'nodes_hybridity.csv'))
# Robust cleanup: drop spurious empty rows (e.g. trailing NaN row, fully-abrogated
# acts with no celex) and coerce the score to numeric so the mean/median never NaN.
hyb = hyb[hyb['celex'].notna()].copy()
hyb['hybridity_score'] = pd.to_numeric(hyb['hybridity_score'], errors='coerce').fillna(0.0)
hyb = hyb.reset_index(drop=True)

scores = hyb['hybridity_score'].values
mean_h = float(scores.mean())
med_h  = float(np.median(scores))
max_i  = int(hyb['hybridity_score'].idxmax())
max_v  = float(hyb.loc[max_i, 'hybridity_score'])
max_cx = str(hyb.loc[max_i, 'celex'])

print('=' * 50)
print(f'N = {len(scores)}')
print(f'Mean   = {mean_h:.4f}')
print(f'Median = {med_h:.4f}')
print(f'Max    = {max_v:.4f}  ({max_cx})')
print('=' * 50)

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.0, 6.0))

# Violin
vp = ax.violinplot(scores, positions=[0], widths=0.55,
                   showmeans=False, showmedians=False, showextrema=False)
for body in vp['bodies']:
    body.set_facecolor('#aac8e8')
    body.set_edgecolor('#2a5c8a')
    body.set_alpha(0.65)
    body.set_linewidth(1.2)

# Strip plot with deterministic jitter
np.random.seed(42)
jitter = np.random.uniform(-0.07, 0.07, size=len(scores))
ax.scatter(jitter, scores, color='#1a3a5c', s=16, alpha=0.80, zorder=3, linewidths=0)

# Blended transform: x in axes fraction, y in data coords
blend = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)

# Splitting threshold
ax.axhline(0.35, color='#aaaaaa', linewidth=1.0, linestyle=':', zorder=2)
ax.text(1.02, 0.357, 'H = 0.35 (splitting threshold)',
        ha='left', va='bottom', fontsize=6.5, fontfamily='serif', color='#aaaaaa',
        transform=blend, clip_on=False)

# Mean
ax.axhline(mean_h, color='#d4691e', linewidth=1.8, linestyle='--', zorder=4)
ax.text(1.02, mean_h + 0.013, f'Mean = {mean_h:.3f}',
        ha='left', va='bottom', fontsize=9.0, fontfamily='serif',
        color='#d4691e', fontweight='semibold', transform=blend, clip_on=False)

# Median
ax.axhline(med_h, color='#2e8b57', linewidth=2.0, linestyle='-', zorder=4)
ax.text(1.02, med_h + 0.013, f'Median = {med_h:.3f}',
        ha='left', va='bottom', fontsize=9.0, fontfamily='serif',
        color='#2e8b57', fontweight='semibold', transform=blend, clip_on=False)

# Annotation: highest-hybridity act — placed above the violin body (clear of data)
ax.annotate(
    f'{max_cx} ({max_v:.3f})',
    xy=(jitter[max_i], max_v),
    xytext=(-0.46, max_v + 0.03),
    fontsize=7.5, fontfamily='serif', color='#1a3a5c',
    arrowprops=dict(arrowstyle='->', color='#1a3a5c', lw=0.8),
    ha='left', va='bottom', clip_on=False,
)

ax.set_ylabel('Act-level hybridity $H_{\\mathrm{loc}}$', fontsize=10, fontfamily='serif')
ax.set_xlim(-0.50, 0.50)
ax.set_ylim(-0.02, 1.02)
ax.set_xticks([])
ax.tick_params(axis='y', labelsize=8)
for sp in ['top', 'right', 'bottom']:
    ax.spines[sp].set_visible(False)
ax.spines['left'].set_color('#aaaaaa')
ax.spines['left'].set_linewidth(0.8)

# Legend (bottom-left) — line samples for mean and median
legend_handles = [
    Line2D([0], [0], color='#d4691e', lw=1.8, linestyle='--', label=f'Mean ({mean_h:.3f})'),
    Line2D([0], [0], color='#2e8b57', lw=2.0, linestyle='-',  label=f'Median ({med_h:.3f})'),
]
ax.legend(handles=legend_handles, loc='lower left', fontsize=8,
          frameon=False, handlelength=2.2, borderaxespad=0.8)

fig.tight_layout()

# ── Save ──────────────────────────────────────────────────────────────────────
for ext in ('pdf', 'png'):
    path = os.path.join(SCRIPT_DIR, f'fig_4_1_hybridity_distribution.{ext}')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    print(f'Saved: {path}')
plt.close(fig)
