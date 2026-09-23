"""Deterministic helpers used by the cached-output reproduction scripts.

The functions in this module never call a language-model API.  They operate on
the classifications and split decisions already stored in the repository.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


LEVELS = ("L1", "L2", "L3", "L4")
LEVEL_COLUMNS = tuple(f"lamf_{level}" for level in LEVELS)
LEVEL_NAMES = {
    "L1": "Level 1 — Framework principles",
    "L2": "Level 2 — Operational rules",
    "L3": "Level 3 — Supervisory convergence",
    "L4": "Level 4 — Enforcement",
}


def normalized_entropy(values: Iterable[float]) -> float:
    """Return Shannon entropy normalized to [0, 1] for four levels."""
    probabilities = np.asarray(list(values), dtype=float)
    probabilities = np.clip(probabilities, 0.0, None)
    total = float(probabilities.sum())
    if total <= 0:
        return 0.0
    probabilities /= total
    # Keep the same epsilon convention used by the original notebooks so that
    # cached and regenerated CSVs agree down to their stored floating values.
    epsilon = 1e-9
    entropy = -float(
        np.sum(probabilities * np.log2(probabilities + epsilon))
    )
    result = float(
        np.clip(entropy / math.log2(len(probabilities)), 0.0, 1.0)
    )
    return 0.0 if abs(result) < 1e-15 else result


def article_base_id(identifier: object) -> str:
    """Collapse FDI fragments such as ``12_p3`` back to article ``12``."""
    return re.sub(r"_p\d+$", "", str(identifier))


def provision_token_counts(raw: object) -> Counter[str]:
    """Count labelled whitespace tokens from a stored ``provisions_raw`` cell."""
    counts: Counter[str] = Counter()
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return counts
    try:
        provisions = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return counts
    for provision in provisions:
        label = str(provision.get("label", ""))
        level = label.replace("level_", "L")
        if level not in LEVELS:
            continue
        try:
            start = int(provision.get("start", 1))
            end = int(provision.get("end", 0))
        except (TypeError, ValueError):
            continue
        counts[level] += max(0, end - start + 1)
    return counts


def reaggregate_fragments(segments: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct one row per article from cached fragment classifications."""
    required = {"celex", "identificatore", "llm_status", "provisions_raw"}
    missing = required.difference(segments.columns)
    if missing:
        raise ValueError(f"Missing segment columns: {sorted(missing)}")

    frame = segments.loc[segments["llm_status"].eq("ok")].copy()
    frame["celex"] = frame["celex"].astype(str)
    frame["articolo_id"] = frame["identificatore"].map(article_base_id)

    rows: list[dict[str, object]] = []
    for (celex, article_id), group in frame.groupby(
        ["celex", "articolo_id"], sort=True
    ):
        counts: Counter[str] = Counter()
        for raw in group["provisions_raw"]:
            counts.update(provision_token_counts(raw))
        total = sum(counts[level] for level in LEVELS)
        percentages = {
            f"lamf_{level}": (100.0 * counts[level] / total if total else 0.0)
            for level in LEVELS
        }
        entropy = normalized_entropy(percentages.values())
        dominant = max(LEVELS, key=lambda level: percentages[f"lamf_{level}"])
        rows.append(
            {
                "celex": celex,
                "articolo_id": article_id,
                **percentages,
                "n_tokens_labeled": total,
                "n_fragments": len(group),
                "entropy": entropy,
                "dominant_lamf": dominant,
            }
        )
    return pd.DataFrame(rows)


def aggregate_acts(
    articles: pd.DataFrame,
    titles: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Aggregate article distributions and entropy to act level."""
    titles = titles or {}
    rows: list[dict[str, object]] = []
    for celex, group in articles.groupby("celex", sort=True):
        means = {column: float(group[column].mean()) for column in LEVEL_COLUMNS}
        score = normalized_entropy(means.values())
        dominant_counts = group["dominant_lamf"].value_counts()
        dominant_level = max(
            LEVELS, key=lambda level: int(dominant_counts.get(level, 0))
        )
        dominant_share = 100.0 * float(
            dominant_counts.get(dominant_level, 0) / len(group)
        )
        most_hybrid = str(group.loc[group["entropy"].idxmax(), "articolo_id"])
        rows.append(
            {
                "celex": str(celex),
                "hybridity_score": score,
                "hybridity_std": float(group["entropy"].std()),
                "hybridity_max": float(group["entropy"].max()),
                "n_articles": int(len(group)),
                "dominant_lamf": dominant_level,
                "dom": LEVEL_NAMES[dominant_level],
                "dominant_lamf_pct": dominant_share,
                "most_hybrid_article": most_hybrid,
                **means,
                "title": titles.get(str(celex), str(celex)),
            }
        )
    return pd.DataFrame(rows).sort_values("hybridity_score", ascending=False)


def load_edges(output_dir: Path) -> pd.DataFrame:
    """Load a domain's act-level edges in the common notebook schema."""
    frames: list[pd.DataFrame] = []
    for name in ("edges_it_internal.csv", "edges_eu_it.csv"):
        path = output_dir / name
        if path.exists() and path.stat().st_size:
            frame = pd.read_csv(path)
            if {"src_slug", "dst_slug"}.issubset(frame.columns):
                frames.append(frame[["src_slug", "dst_slug", "family", "w"]])

    focal_path = output_dir / "edges_focal.csv"
    if focal_path.exists() and focal_path.stat().st_size:
        frame = pd.read_csv(focal_path)
        if {"Source", "Target"}.issubset(frame.columns):
            focal = pd.DataFrame(
                {
                    "src_slug": frame["Source"].astype(str),
                    "dst_slug": frame["Target"].astype(str),
                    "family": "ref",
                    "w": 1.0,
                }
            )
            frames.append(focal)

    if not frames:
        return pd.DataFrame(columns=["src_slug", "dst_slug", "family", "w"])
    return pd.concat(frames, ignore_index=True)


def diffuse(
    local_distributions: pd.DataFrame,
    edges: pd.DataFrame,
    restart_weight: float = 0.5,
    weighted: bool = True,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Diffuse L1–L4 distributions through the citation network.

    Rows with outgoing links are normalized to one.  Rows without outgoing
    links remain zero; the transition matrix is therefore row-substochastic.
    Reception edges are reversed, matching notebooks 04 and 05.
    """
    nodes = local_distributions["celex"].astype(str).tolist()
    index = {node: position for position, node in enumerate(nodes)}
    local = local_distributions.loc[:, LEVEL_COLUMNS].to_numpy(dtype=float)
    totals = local.sum(axis=1, keepdims=True)
    totals[totals == 0] = 1.0
    local = local / totals

    transition = np.zeros((len(nodes), len(nodes)), dtype=float)
    for row in edges.itertuples(index=False):
        source = str(row.src_slug)
        target = str(row.dst_slug)
        family = str(getattr(row, "family", "ref"))
        if family == "recep":
            source, target = target, source
        if source not in index or target not in index:
            continue
        weight = float(getattr(row, "w", 1.0)) if weighted else 1.0
        transition[index[source], index[target]] += weight

    row_sums = transition.sum(axis=1, keepdims=True)
    nonzero_rows = row_sums[:, 0] > 0
    transition[nonzero_rows] /= row_sums[nonzero_rows]

    identity = np.eye(len(nodes))
    global_distribution = (1.0 - restart_weight) * np.linalg.solve(
        identity - restart_weight * transition, local
    )
    global_totals = global_distribution.sum(axis=1, keepdims=True)
    global_totals[global_totals == 0] = 1.0
    global_distribution /= global_totals

    rows = []
    for position, celex in enumerate(nodes):
        p_local = local[position]
        p_global = global_distribution[position]
        h_local = normalized_entropy(p_local)
        h_global = normalized_entropy(p_global)
        rows.append(
            {
                "celex": celex,
                "H_local": h_local,
                "H_global": h_global,
                "H_delta": h_global - h_local,
                **{
                    f"lamf_glob_{level}": 100.0 * p_global[offset]
                    for offset, level in enumerate(LEVELS)
                },
            }
        )
    return pd.DataFrame(rows), transition


def block_hybridity(articles: pd.DataFrame) -> float:
    if articles.empty:
        return 0.0
    return normalized_entropy(articles.loc[:, LEVEL_COLUMNS].sum(axis=0))


def deterministic_partition(
    articles: pd.DataFrame,
    min_block: int = 4,
    min_improvement: float = 0.30,
) -> dict[str, object] | None:
    """Run the deterministic pre-validation splitting rule from notebook 05."""
    if articles.empty:
        return None
    frame = articles.loc[(articles.loc[:, LEVEL_COLUMNS] != 0).any(axis=1)].copy()
    if frame.empty:
        return None
    frame["dom"] = frame.loc[:, LEVEL_COLUMNS].idxmax(axis=1).str.replace(
        "lamf_", "", regex=False
    )
    before = block_hybridity(frame)

    l1 = frame.loc[frame["dom"].eq("L1")]
    l23 = frame.loc[frame["dom"].isin(["L2", "L3"])]
    l4 = frame.loc[frame["dom"].eq("L4")]
    if len(l4) >= min_block and len(l23) >= min_block:
        raw_blocks = [("L1", l1), ("L23", l23), ("L4", l4)]
    else:
        raw_blocks = [("L1", l1), ("L234", pd.concat([l23, l4]))]

    blocks: list[tuple[str, pd.DataFrame]] = []
    pending: tuple[str, pd.DataFrame] | None = None
    for label, block in raw_blocks:
        if block.empty:
            continue
        if pending is not None:
            pending_label, pending_frame = pending
            block = pd.concat([pending_frame, block])
            label = pending_label
            pending = None
        if len(block) < min_block:
            if blocks:
                previous_label, previous_frame = blocks[-1]
                blocks[-1] = (previous_label, pd.concat([previous_frame, block]))
            else:
                pending = (label, block)
        else:
            blocks.append((label, block))
    if pending is not None:
        if blocks:
            previous_label, previous_frame = blocks[-1]
            blocks[-1] = (previous_label, pd.concat([previous_frame, pending[1]]))
        else:
            blocks.append(pending)
    if len(blocks) <= 1:
        return None

    total = sum(len(block) for _, block in blocks)
    after = sum(
        len(block) * block_hybridity(block) / total for _, block in blocks
    )
    improvement = (before - after) / before if before > 0 else 0.0
    if improvement < min_improvement:
        return None
    return {
        "H_before": before,
        "H_after": after,
        "delta_H": before - after,
        "H_improvement": improvement,
        "n_blocks": len(blocks),
        "block_entropies": [block_hybridity(block) for _, block in blocks],
    }
