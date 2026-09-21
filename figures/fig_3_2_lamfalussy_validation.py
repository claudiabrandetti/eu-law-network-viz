#!/usr/bin/env python
"""Figure 3.2 — manual validation of the Lamfalussy classifier.

Recreates the thesis figure with the same reported values and visual structure,
using larger, darker typography for reliable print readability.
"""

import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

plt.rcParams.update({
    'font.family': 'serif',
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

ACTS = ['MiFID II', 'MiFIR', 'Delegated Regulation\n(EU) 2017/565']
SHARES = np.array([
    [43.9, 34.0, 1.1, 21.0],
    [42.8, 37.6, 0.8, 18.8],
    [35.8, 57.9, 0.5, 5.8],
])
ENTROPY = [0.797, 0.783, 0.632]
DECLARED = ['L1', 'L1', 'L2']
PREDICTED = ['L1', 'L1', 'L2']

TIER_NAMES = ['L1', 'L2', 'L3', 'L4']
TIER_COLORS = ['#4f8ef7', '#b090e0', '#3a9c6e', '#c85c3a']

fig, ax = plt.subplots(figsize=(9.2, 5.3))
x = np.arange(len(ACTS))
width = 0.18

# Very light group bands retain the original grouping without reducing contrast.
for i in range(len(ACTS)):
    ax.axvspan(i - 0.43, i + 0.43, color='#f5f5f5', zorder=0)

for tier_i, (tier, color) in enumerate(zip(TIER_NAMES, TIER_COLORS)):
    xpos = x + (tier_i - 1.5) * width
    bars = ax.bar(xpos, SHARES[:, tier_i], width=width, color=color,
                  edgecolor='white', linewidth=0.7, zorder=2)
    for bar, value in zip(bars, SHARES[:, tier_i]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.2,
                f'{value:.1f}%', ha='center', va='bottom', fontsize=10.5,
                color='#111111', fontweight='normal', clip_on=False)

for i, (entropy, declared, predicted) in enumerate(zip(ENTROPY, DECLARED, PREDICTED)):
    ax.text(i, 95.0, f'Declared: {declared}\nPredicted: {predicted}',
            ha='center', va='center', fontsize=11.0, color='#111111',
            fontweight='normal', linespacing=1.25)
    ax.text(i, 84.5, f'$H_{{\\mathrm{{loc}}}}$ = {entropy:.3f}',
            ha='center', va='center', fontsize=11.0, color='#2b2b2b')

ax.set_xlim(-0.55, len(ACTS) - 0.45)
ax.set_ylim(0, 100)
ax.set_ylabel('Token share', fontsize=13, color='#111111')
ax.set_xticks(x)
ax.set_xticklabels(ACTS, fontsize=12.5, color='#111111')
ax.set_yticks([0, 20, 40, 60, 80, 100])
ax.set_yticklabels([f'{v}%' for v in [0, 20, 40, 60, 80, 100]],
                   fontsize=11, color='#222222')
ax.grid(axis='y', color='#d5d5d5', linewidth=0.7, zorder=1)
ax.tick_params(axis='x', length=0, pad=8)
ax.tick_params(axis='y', colors='#222222')
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)
for spine in ['left', 'bottom']:
    ax.spines[spine].set_color('#777777')

handles = [mpatches.Patch(color=c, label=t) for t, c in zip(TIER_NAMES, TIER_COLORS)]
ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.18),
          ncol=4, frameon=False, fontsize=11.5, columnspacing=2.2)

fig.subplots_adjust(left=0.09, right=0.985, top=0.97, bottom=0.25)

out_dir = os.path.dirname(os.path.abspath(__file__))
fig.savefig(os.path.join(out_dir, 'fig_3_2_lamfalussy_validation.png'),
            dpi=300, facecolor='white')
fig.savefig(os.path.join(out_dir, 'fig_3_2_lamfalussy_validation.pdf'),
            dpi=300, bbox_inches='tight', facecolor='white')
plt.close(fig)
