#!/usr/bin/env python
"""
Figure 4.2 — Article-by-level heatmap, D.Lgs. 36/2023.

Layout: [Book band | 229-row x 4-tier heatmap | Mean L1 per Book panel]

The right panel makes the argument visible: L1 (framework language) is NOT
concentrated at the head of the code — its per-Book mean is lowest in Book II
(the main procurement body) and highest in Books III-IV (sector-specific /
PPP books), demonstrating persistent framework density across all structural
levels of the code.

Book structure (confirmed from official HTML TOC):
  Book I   arts  1-47   Dei principi, digitalizzazione, programmazione, progettazione
  Book II  arts 48-140  Dell'appalto
  Book III arts141-173  Dell'appalto nei settori speciali
  Book IV  arts174-208  Del partenariato pubblico-privato e delle concessioni
  Book V   arts209-229  Del contenzioso e dell'ANAC. Disposizioni finali e transitorie
"""

import json
import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

# ── Style ──────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':      'serif',
    'figure.facecolor': 'white',
    'axes.facecolor':   'white',
    'pdf.fonttype':      42,
    'ps.fonttype':       42,
})

# ── Tier palette (matches network_template.html interface) ─────────────────────
TIER_HEX   = {'L1': '#4f8ef7', 'L2': '#b090e0', 'L3': '#3a9c6e', 'L4': '#c85c3a'}
TIER_NAMES = ['L1', 'L2', 'L3', 'L4']
TIER_COL_LABELS = [
    'L1\nFramework',
    'L2\nOperational',
    'L3\nSupervisory\nconvergence',
    'L4\nEnforcement',
]

# Muted fill colours for Book bands (same 5-colour set)
BOOK_COLORS = ['#cfe2f5', '#c5ead6', '#fde8c5', '#e5d4ef', '#f8d4d2']

# ── Book structure ─────────────────────────────────────────────────────────────
BOOKS = [
    ( 1,  47, 'Book I',   'Dei principi, digitalizzazione,\nprogrammazione, progettazione'),
    (48, 140, 'Book II',  "Dell'appalto"),
    (141,173, 'Book III', "Dell'appalto nei settori speciali"),
    (174,208, 'Book IV',  'Del partenariato pubblico-privato\ne delle concessioni'),
    (209,229, 'Book V',   "Del contenzioso e dell'ANAC.\nDisp. finali e transitorie"),
]

# ── Load data ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)

with open(os.path.join(ROOT_DIR, 'heatmaps.json'), 'r', encoding='utf-8') as fh:
    heatmaps = json.load(fh)

raw = heatmaps['dlgs_36_2023']

def art_num(item):
    m = re.match(r'art(\d+)', item['id'])
    return int(m.group(1)) if m else 99999

articles = sorted(raw, key=art_num)
art_nums = np.array([art_num(a) for a in articles])
mat = np.array(
    [[a['lamf']['L1'], a['lamf']['L2'], a['lamf']['L3'], a['lamf']['L4']]
     for a in articles],
    dtype=float,
)  # (229, 4)

# ── Sanity checks ──────────────────────────────────────────────────────────────
print('=' * 60)
print('SANITY CHECK -- dlgs_36_2023')
print(f'  Articles loaded : {len(mat)}')
row_sums = mat.sum(axis=1)
print(f'  Row sums        : min={row_sums.min():.2f}%  '
      f'max={row_sums.max():.2f}%  mean={row_sums.mean():.2f}%')
missing = sorted(set(range(1, 230)) - set(art_nums.tolist()))
print(f'  Missing art nums: {missing if missing else "none"}')
bad = np.where(np.abs(row_sums - 100) > 1.0)[0]
if len(bad):
    print(f'  WARNING: {len(bad)} rows with sum != 100%')
    for r in bad:
        print(f'    art{art_nums[r]}: {mat[r]}  sum={row_sums[r]:.2f}')
print()
print('  First 8 rows (art | L1 | L2 | L3 | L4 | sum):')
for i in range(8):
    print(f'    art{art_nums[i]:3d}: '
          f'{mat[i,0]:5.1f}%  {mat[i,1]:5.1f}%  '
          f'{mat[i,2]:5.1f}%  {mat[i,3]:5.1f}%  '
          f'sum={row_sums[i]:.1f}%')

# ── Book mapping ───────────────────────────────────────────────────────────────
book_of_row = np.full(len(art_nums), -1, dtype=int)
for i, n in enumerate(art_nums):
    for bi, (lo, hi, *_) in enumerate(BOOKS):
        if lo <= n <= hi:
            book_of_row[i] = bi
            break

book_row_ranges = []
for bi in range(len(BOOKS)):
    rows = np.where(book_of_row == bi)[0]
    book_row_ranges.append((int(rows[0]), int(rows[-1])))

# ── Per-Book L1 statistics ─────────────────────────────────────────────────────
book_l1_means = []
print()
print('=' * 60)
print('PER-BOOK L1 STATISTICS')
print('-' * 60)
for bi, (lo, hi, bname, _) in enumerate(BOOKS):
    rows = np.where(book_of_row == bi)[0]
    l1   = mat[rows, 0]
    mean = float(l1.mean())
    book_l1_means.append(mean)
    dom  = int((np.argmax(mat[rows], axis=1) == 0).sum())
    pct  = dom / len(rows) * 100
    print(
        f'  {bname} (arts {lo:3d}-{hi:3d}, n={len(rows):2d}):  '
        f'mean L1 = {mean:5.1f}%   '
        f'L1-dominant = {dom:2d}/{len(rows)} ({pct:4.0f}%)'
    )
overall_mean_l1 = float(mat[:, 0].mean())
print(f'  Overall mean L1 = {overall_mean_l1:.1f}%')
print('=' * 60)

# ── Build RGB image for heatmap ────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)])

WHITE  = np.ones(3)
n_rows = len(mat)
img    = np.ones((n_rows, 4, 3), dtype=float)

for c, tier in enumerate(TIER_NAMES):
    col   = hex_to_rgb(TIER_HEX[tier])
    alpha = mat[:, c] / 100.0
    img[:, c, :] = np.outer(1 - alpha, WHITE) + np.outer(alpha, col)

# ── Figure layout ──────────────────────────────────────────────────────────────
# Columns: [book band | heatmap | L1-per-Book panel]
# Rows:    [main content | thin colorbar strip]
# A small gap between heatmap and L1 panel is introduced by shifting ax_l1
# 1.5% of figure width to the right after creation.

fig = plt.figure(figsize=(7.0, 10.0))

gs = gridspec.GridSpec(
    2, 3,
    figure       = fig,
    width_ratios = [0.15, 1.0, 0.34],
    height_ratios= [1.0,  0.025],
    wspace       = 0.0,
    hspace       = 0.015,
    left=0.03, right=0.97, top=0.945, bottom=0.065,
)

ax_book  = fig.add_subplot(gs[0, 0])   # Book band
ax_heat  = fig.add_subplot(gs[0, 1])   # Heatmap
ax_l1    = fig.add_subplot(gs[0, 2])   # Mean L1 per Book bar panel
ax_cb    = fig.add_subplot(gs[1, 1])   # Colorbar under heatmap
ax_cbpad = fig.add_subplot(gs[1, 0])   # spacer
ax_cbpad.set_visible(False)

# Shift ax_l1 right to create a visible gap from the heatmap
_pos = ax_l1.get_position()
_gap = 0.018
ax_l1.set_position([_pos.x0 + _gap, _pos.y0, _pos.width - _gap, _pos.height])

# ── Heatmap ────────────────────────────────────────────────────────────────────
ax_heat.imshow(
    img, aspect='auto', interpolation='nearest', origin='upper',
    extent=[-0.5, 3.5, n_rows - 0.5, -0.5],
)

# Column headers at top, coloured by tier
ax_heat.set_xticks([0, 1, 2, 3])
ax_heat.set_xticklabels(TIER_COL_LABELS, fontsize=10.0, fontfamily='serif')
ax_heat.xaxis.set_ticks_position('top')
ax_heat.xaxis.set_label_position('top')
for tick, tier in zip(ax_heat.get_xticklabels(), TIER_NAMES):
    tick.set_color(TIER_HEX[tier])
    tick.set_fontweight('semibold')
    tick.set_linespacing(1.15)
ax_heat.tick_params(axis='x', which='both', top=False, length=0, pad=6)

# Y-axis: article numbers every 20 rows, plus first and last
ytick_idx = list(range(0, n_rows, 20))
for edge in [0, n_rows - 1]:
    if edge not in ytick_idx:
        ytick_idx.append(edge)
ytick_idx.sort()
ax_heat.set_yticks(ytick_idx)
ax_heat.set_yticklabels(
    [str(int(art_nums[i])) for i in ytick_idx],
    fontsize=8.0, fontfamily='serif', color='#222222',
)
ax_heat.tick_params(axis='y', which='both', left=False, right=False, length=0, pad=3)
ax_heat.set_ylim(n_rows - 0.5, -0.5)
ax_heat.set_xlim(-0.5, 3.5)

# Book separator lines
for bi in range(1, len(BOOKS)):
    sep = book_row_ranges[bi][0] - 0.5
    ax_heat.axhline(y=sep, color='#3a3a3a', linewidth=0.75, alpha=0.8, zorder=5)

# Thin column separators
for xv in [0.5, 1.5, 2.5]:
    ax_heat.axvline(x=xv, color='#bbbbbb', linewidth=0.25, alpha=0.6, zorder=4)

for sp in ax_heat.spines.values():
    sp.set_visible(False)

# ── Book bands ─────────────────────────────────────────────────────────────────
ax_book.set_xlim(0, 1)
ax_book.set_ylim(n_rows - 0.5, -0.5)
ax_book.set_xticks([])
ax_book.set_yticks([])
for sp in ax_book.spines.values():
    sp.set_visible(False)

for bi, (lo, hi, bname, _) in enumerate(BOOKS):
    r0, r1 = book_row_ranges[bi]
    rect = mpatches.Rectangle(
        (0.08, r0 - 0.45), 0.84, (r1 - r0 + 0.9),
        facecolor=BOOK_COLORS[bi], edgecolor='none', alpha=0.88, zorder=2,
    )
    ax_book.add_patch(rect)
    mid = (r0 + r1) / 2.0
    ax_book.text(
        0.34, mid, bname,
        ha='center', va='center', rotation=90,
        fontsize=7.8, fontfamily='serif', color='#111111', zorder=3,
    )
    if bi < len(BOOKS) - 1:
        sep = book_row_ranges[bi + 1][0] - 0.5
        ax_book.axhline(y=sep, color='#3a3a3a', linewidth=0.75, alpha=0.8, zorder=4)

# ── Mean L1 per Book panel ─────────────────────────────────────────────────────
L1_COL   = hex_to_rgb(TIER_HEX['L1'])
X_MAX    = 45.0   # x-axis ceiling (%)
REF_COL  = '#888888'

ax_l1.set_xlim(0, X_MAX)
ax_l1.set_ylim(n_rows - 0.5, -0.5)   # inverted, same as heatmap
ax_l1.set_yticks([])

# Light background band behind bars (Book colours, same as left band)
for bi in range(len(BOOKS)):
    r0, r1 = book_row_ranges[bi]
    ax_l1.axhspan(r0 - 0.5, r1 + 0.5, facecolor=BOOK_COLORS[bi],
                  alpha=0.35, zorder=0)

# Horizontal bars (one per Book), height = 80% of book row span
for bi, (lo, hi, bname, _) in enumerate(BOOKS):
    r0, r1 = book_row_ranges[bi]
    mid      = (r0 + r1) / 2.0
    bar_half = (r1 - r0 + 1) * 0.40   # 80% fill, symmetric
    l1_val   = book_l1_means[bi]

    ax_l1.barh(
        y=mid, width=l1_val, height=bar_half * 2,
        left=0, color=TIER_HEX['L1'], alpha=0.78,
        edgecolor='none', zorder=3,
    )
    # Value label at end of bar
    ax_l1.text(
        l1_val + 0.7, mid,
        f'{l1_val:.1f}%',
        va='center', ha='left',
        fontsize=8.5, fontfamily='serif', color='#111111', zorder=4,
    )

# Overall mean reference line (dashed)
ax_l1.axvline(
    x=overall_mean_l1,
    color=REF_COL, linewidth=0.8, linestyle='--', alpha=0.85, zorder=2,
)
# Book separator lines (carry through from heatmap)
for bi in range(1, len(BOOKS)):
    sep = book_row_ranges[bi][0] - 0.5
    ax_l1.axhline(y=sep, color='#3a3a3a', linewidth=0.5, alpha=0.5, zorder=3)

# X-axis ticks at bottom only
ax_l1.set_xticks([0, 10, 20, 30, 40])
ax_l1.set_xticklabels(['0', '10', '20', '30', '40'],
                       fontsize=8.0, fontfamily='serif', color='#222222')
ax_l1.tick_params(axis='x', which='both', bottom=True, top=False,
                  length=3, direction='out', pad=3)
ax_l1.tick_params(axis='y', which='both', left=False, right=False, length=0)
ax_l1.xaxis.set_ticks_position('bottom')

# Spines: only bottom
for side, sp in ax_l1.spines.items():
    sp.set_visible(side == 'bottom')
ax_l1.spines['bottom'].set_color('#aaaaaa')
ax_l1.spines['bottom'].set_linewidth(0.6)

# Panel title (aligned with column headers of heatmap)
ax_l1.set_title(
    f'Mean L1 share\nper Book (%)\nOverall average: {overall_mean_l1:.1f}%',
    fontsize=8.3, fontfamily='serif', color='#111111',
    pad=6, loc='center', linespacing=1.15,
)

# ── Colorbar strip (under heatmap) ─────────────────────────────────────────────
N_GRAD = 200
ax_cb.set_xlim(-0.5, 3.5)
ax_cb.set_ylim(0, 1)
ax_cb.set_xticks([])
ax_cb.set_yticks([])
for sp in ax_cb.spines.values():
    sp.set_visible(False)

for c, tier in enumerate(TIER_NAMES):
    col = hex_to_rgb(TIER_HEX[tier])
    t   = np.linspace(0, 1, N_GRAD)
    bar = (np.outer(1 - t, WHITE) + np.outer(t, col)).reshape(1, N_GRAD, 3)
    ax_cb.imshow(bar, aspect='auto', origin='upper',
                 extent=[c - 0.45, c + 0.45, 0, 1], zorder=2)

ax_cb.text(-0.48, -0.15, '0 %',   ha='left',  va='top', fontsize=7.8,
           fontfamily='serif', color='#333333',
           transform=ax_cb.transData, clip_on=False)
ax_cb.text( 3.48, -0.15, '100 %', ha='right', va='top', fontsize=7.8,
           fontfamily='serif', color='#333333',
           transform=ax_cb.transData, clip_on=False)
ax_cb.text(1.5, -0.95,
           'Token share per tier  (pale = 0 %, saturated = 100 %)',
           ha='center', va='top', fontsize=10.2, fontfamily='serif',
           color='#333333', style='italic',
           transform=ax_cb.transData, clip_on=False)

# ── Save ───────────────────────────────────────────────────────────────────────
out_dir = os.path.join(ROOT_DIR, 'figures')
os.makedirs(out_dir, exist_ok=True)

pdf_path = os.path.join(out_dir, 'fig_4_2_dlgs36_heatmap.pdf')
png_path = os.path.join(out_dir, 'fig_4_2_dlgs36_heatmap.png')

fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
fig.savefig(png_path, dpi=300, bbox_inches='tight')

print(f'\nSaved:')
print(f'  {pdf_path}')
print(f'  {png_path}')

plt.close(fig)
