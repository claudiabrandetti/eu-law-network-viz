#!/usr/bin/env python
"""
Figure 4.3 — Local vs. global hybridity scatter (contamination drift via citations).

H_local  = act-internal entropy (article distribution across L1-L4).
H_global = entropy after diffusing Lamfalussy profiles along citation edges.
Delta    = H_global - H_local  (positive = act 'infected' by hybrid neighbours).

Data: data/output/appalti_it/nodes_diffusion.csv
EU nodes (celex starts with a digit) drawn as hollow circles.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

plt.rcParams.update({
    'font.family':      'serif',
    'figure.facecolor': 'white',
    'axes.facecolor':   'white',
    'pdf.fonttype':      42,
    'ps.fonttype':       42,
})

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)

# ── Load the scorable acts ────────────────────────────────────────────────────
nodes = pd.read_csv(os.path.join(
    ROOT_DIR, 'data', 'output', 'appalti_it', 'nodes_diffusion.csv'
)).dropna(subset=['H_local', 'H_global'])

ids   = nodes['celex'].astype(str).tolist()
hl    = nodes['H_local'].to_numpy(dtype=float)
hg    = nodes['H_global'].to_numpy(dtype=float)
delta = hg - hl
eu    = np.array([node_id[:1].isdigit() for node_id in ids])

print(f'Scorable acts: {len(nodes)}  EU: {eu.sum()}')
print(f'Delta  mean={delta.mean():+.4f}  max={delta.max():+.4f}  min={delta.min():+.4f}')
for nid, h1, h2, d in sorted(zip(ids, hl, hg, delta), key=lambda x: -x[3])[:8]:
    print(f'  {nid:<24} H_loc={h1:.3f}  H_glob={h2:.3f}  delta={d:+.3f}')

# ── Figure ────────────────────────────────────────────────────────────────────
# Restore the compact proportions of the original figure while keeping the
# updated observations and labels readable at thesis scale.
fig, ax = plt.subplots(figsize=(6.4, 4.9))

vlim = max(abs(delta.max()), abs(delta.min())) * 1.05
vlim = min(vlim, 0.75)
norm = mcolors.Normalize(vmin=-vlim, vmax=vlim)
cmap = plt.get_cmap('RdBu_r')

# IT nodes — filled circles. Strong dark ring so near-zero-drift markers
# (white fill from the diverging colormap) stay visible, even on the diagonal.
sc = ax.scatter(hl[~eu], hg[~eu], c=delta[~eu], cmap=cmap, norm=norm,
                s=32, zorder=3, linewidths=0.7, edgecolors='#1a1a1a', alpha=0.95)

# EU nodes — hollow circles with a fixed dark ring (their colormap colour is
# near-white at Δ≈0, which would be invisible on the white page / diagonal).
for i in np.where(eu)[0]:
    ax.scatter(hl[i], hg[i], s=32, facecolor='none',
               edgecolor='#1a1a1a', linewidths=0.7, zorder=3)

# Diagonal y = x
ax_max = max(float(hl.max()), float(hg.max())) + 0.05
ax.plot([0, ax_max], [0, ax_max], color='#888888', lw=0.8, ls='--', zorder=1,
        label='$H_{\\mathrm{global}} = H_{\\mathrm{local}}$  (no contamination)')

# Colorbar
cb = plt.colorbar(sc, ax=ax, fraction=0.038, pad=0.025)
cb.set_label('Contamination drift  $\\Delta = H_{\\mathrm{global}} - H_{\\mathrm{local}}$',
             fontsize=10.0, fontfamily='serif')
cb.ax.tick_params(labelsize=9.0)

# ── Annotations ───────────────────────────────────────────────────────────────
# Highest-delta substantive act
subst_mask = hl > 0.01
top_i = int(np.where(subst_mask)[0][np.argmax(delta[subst_mask])])
ax.annotate(
    f'{ids[top_i]}\n($\\Delta$ = {delta[top_i]:+.3f})',
    xy=(hl[top_i], hg[top_i]),
    xytext=(hl[top_i], hg[top_i] + 0.12),
    fontsize=8.3, fontfamily='serif', color='#111111', ha='center',
    arrowprops=dict(arrowstyle='->', color='#555555', lw=0.7),
)

# dlgs_59_2010 (main case study — place above cluster to avoid overlap)
if 'dlgs_59_2010' in ids:
    i59 = ids.index('dlgs_59_2010')
    ax.annotate(
        f'dlgs_59_2010\n($\\Delta$ = {delta[i59]:+.3f})',
        xy=(hl[i59], hg[i59]),
        xytext=(hl[i59] - 0.08, ax_max - 0.04),
        fontsize=8.3, fontfamily='serif', color='#111111', ha='right',
        arrowprops=dict(arrowstyle='->', color='#555555', lw=0.7),
    )

# Zero-H_local nodes with non-zero H_global (contaminated empty shells)
zero_ids = [(nid, hg[i]) for i, nid in enumerate(ids)
            if hl[i] < 0.01 and hg[i] > 0.05]
if zero_ids:
    zero_ids_sorted = sorted(zero_ids, key=lambda x: -x[1])
    label_str = ', '.join(nid for nid, _ in zero_ids_sorted)
    xi = 0.0
    yi = float(np.mean([g for _, g in zero_ids_sorted]))
    ax.annotate(
        label_str + '\n($H_{\\mathrm{local}}=0$;  $H_{\\mathrm{global}}>0$)',
        xy=(xi, yi),
        xytext=(xi + 0.12, yi - 0.13),
        fontsize=8.2, fontfamily='serif', color='#111111', ha='left',
        arrowprops=dict(arrowstyle='->', color='#555555', lw=0.7),
    )

# ── Axes ──────────────────────────────────────────────────────────────────────
ax.set_xlabel('Local hybridity $H_{\\mathrm{local}}$',  fontsize=10, fontfamily='serif')
ax.set_ylabel('Global hybridity $H_{\\mathrm{global}}$', fontsize=10, fontfamily='serif')
ax.set_xlim(-0.03, ax_max)
ax.set_ylim(-0.03, ax_max)
ax.tick_params(labelsize=8.8)
for sp in ['top', 'right']:
    ax.spines[sp].set_visible(False)
for sp in ['left', 'bottom']:
    ax.spines[sp].set_color('#aaaaaa')
    ax.spines[sp].set_linewidth(0.8)

ax.legend(loc='lower right', fontsize=9, frameon=False)

fig.tight_layout()

# ── Save ──────────────────────────────────────────────────────────────────────
for ext in ('pdf', 'png'):
    path = os.path.join(SCRIPT_DIR, f'fig_4_3_hlocal_vs_hglobal.{ext}')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    print(f'Saved: {path}')
plt.close(fig)
