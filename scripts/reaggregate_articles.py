"""Rebuild article- and act-level outputs from cached classifications.

This script is deliberately API-free.  It reconstructs the ``reaggregated``
folders from ``segments_lamfalussy.csv`` and can therefore be run without the
model originally used to classify the fragments.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from analysis_core import (
    LEVEL_COLUMNS,
    aggregate_acts,
    deterministic_partition,
    diffuse,
    load_edges,
    reaggregate_fragments,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "data" / "output"
AVAILABLE_DOMAINS = ("appalti_it", "fdi_screening")
DEFAULT_DOMAINS = ("fdi_screening",)


def title_lookup(output_dir: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    candidates = [
        output_dir / "nodes_hybridity.csv",
        output_dir / "nodes_texts_it.csv",
        *sorted(output_dir.glob("nodes_texts_eu_*.csv")),
    ]
    for path in candidates:
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        identifier = next(
            (column for column in ("celex", "Id", "id") if column in frame.columns),
            None,
        )
        title = next(
            (column for column in ("title", "titolo", "Label") if column in frame.columns),
            None,
        )
        if identifier is None or title is None:
            continue
        for row in frame[[identifier, title]].dropna().itertuples(index=False):
            titles[str(row[0])] = str(row[1])
    return titles


def build_splitting_table(
    articles: pd.DataFrame,
    acts: pd.DataFrame,
    hybridity_threshold: float = 0.35,
    min_articles: int = 8,
    min_block: int = 4,
    min_improvement: float = 0.30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    accepted_after: dict[str, float] = {}
    accepted_block_entropies: dict[str, list[float]] = {}

    for act in acts.itertuples(index=False):
        celex = str(act.celex)
        before = float(act.hybridity_score)
        n_articles = int(act.n_articles)
        eligible = before >= hybridity_threshold and n_articles >= min_articles
        row: dict[str, object] = {
            "celex": celex,
            "hybridity_score_before": round(before, 4),
            "n_articles_reali": n_articles,
            "eligible": eligible,
            "outcome": "not_eligible" if not eligible else "rejected",
            "H_before": round(before, 4),
            "H_after": None,
            "delta_H": None,
            "H_improvement": None,
            "n_blocks": None,
        }
        if eligible:
            partition = deterministic_partition(
                articles.loc[articles["celex"].astype(str).eq(celex)],
                min_block=min_block,
                min_improvement=min_improvement,
            )
            if partition is not None:
                row.update(
                    {
                        "outcome": "accepted",
                        "H_before": round(float(partition["H_before"]), 4),
                        "H_after": round(float(partition["H_after"]), 4),
                        "delta_H": round(float(partition["delta_H"]), 4),
                        "H_improvement": round(
                            float(partition["H_improvement"]), 4
                        ),
                        "n_blocks": float(partition["n_blocks"]),
                    }
                )
                accepted_after[celex] = float(partition["H_after"])
                accepted_block_entropies[celex] = list(
                    partition["block_entropies"]
                )
        rows.append(row)

    before_mean = float(acts["hybridity_score"].mean())
    paired_after = [
        accepted_after.get(str(row.celex), float(row.hybridity_score))
        for row in acts.itertuples(index=False)
    ]
    after_mean = float(pd.Series(paired_after).mean())
    post_unit_values: list[float] = []
    for row in acts.itertuples(index=False):
        celex = str(row.celex)
        if celex in accepted_block_entropies:
            post_unit_values.extend(accepted_block_entropies[celex])
        else:
            post_unit_values.append(float(row.hybridity_score))
    legacy_post_unit_mean = float(pd.Series(post_unit_values).mean())
    rows.append(
        {
            "celex": "__SUMMARY__",
            "hybridity_score_before": round(before_mean, 4),
            "n_articles_reali": int(acts["n_articles"].sum()),
            "eligible": None,
            "outcome": "network_summary",
            "H_before": round(before_mean, 4),
            "H_after": round(after_mean, 4),
            "delta_H": round(before_mean - after_mean, 4),
            "H_improvement": round(
                (before_mean - after_mean) / before_mean if before_mean else 0.0,
                4,
            ),
            "n_blocks": float(len(accepted_after)),
        }
    )
    audit = pd.DataFrame(
        [
            {
                "n_acts_before": int(len(acts)),
                "n_units_after": int(len(post_unit_values)),
                "n_split_acts": int(len(accepted_after)),
                "H_before_act_mean": before_mean,
                "H_after_paired_act_mean": after_mean,
                "paired_relative_reduction": (
                    (before_mean - after_mean) / before_mean if before_mean else 0.0
                ),
                "H_after_unpaired_unit_mean_legacy": legacy_post_unit_mean,
                "legacy_relative_reduction": (
                    (before_mean - legacy_post_unit_mean) / before_mean
                    if before_mean
                    else 0.0
                ),
                "note": (
                    "The paired act-level result is the comparable estimate. "
                    "The legacy estimate averages a different number of units "
                    "before and after splitting and is retained only for audit."
                ),
            }
        ]
    )
    return pd.DataFrame(rows), audit


def rebuild_domain(domain: str) -> dict[str, float | int | str]:
    output_dir = OUTPUT_ROOT / domain
    segments_path = output_dir / "segments_lamfalussy.csv"
    if not segments_path.exists():
        raise FileNotFoundError(segments_path)

    segments = pd.read_csv(segments_path)
    articles = reaggregate_fragments(segments)
    acts = aggregate_acts(articles, title_lookup(output_dir))

    edges = load_edges(output_dir)
    diffusion, _ = diffuse(acts[["celex", *LEVEL_COLUMNS]], edges)
    diffusion = diffusion[["celex", "H_global", "H_local"]].rename(
        columns={"H_local": "H_local_diffusion"}
    )
    diffusion[["H_global", "H_local_diffusion"]] = diffusion[
        ["H_global", "H_local_diffusion"]
    ].round(4)
    acts = acts.merge(diffusion, on="celex", how="left")

    splitting, reaggregation_audit = build_splitting_table(articles, acts)
    destination = output_dir / "reaggregated"
    destination.mkdir(parents=True, exist_ok=True)
    articles.to_csv(destination / "nodes_lamfalussy_byarticle.csv", index=False)
    acts.to_csv(destination / "nodes_hybridity_byarticle.csv", index=False)
    splitting.to_csv(destination / "splitting_byarticle.csv", index=False)
    reaggregation_audit.to_csv(
        destination / "reaggregation_audit.csv", index=False
    )

    summary = splitting.iloc[-1]
    return {
        "domain": domain,
        "articles": int(len(articles)),
        "acts": int(len(acts)),
        "accepted_splits": int(
            splitting["outcome"].eq("accepted").sum()
        ),
        "H_before": float(summary["H_before"]),
        "H_after": float(summary["H_after"]),
        "relative_reduction": float(summary["H_improvement"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "domains",
        nargs="*",
        default=list(DEFAULT_DOMAINS),
        choices=list(AVAILABLE_DOMAINS),
    )
    args = parser.parse_args()
    for domain in args.domains:
        result = rebuild_domain(domain)
        print(
            "{domain}: {acts} acts, {articles} articles, {accepted_splits} splits, "
            "H {H_before:.4f} -> {H_after:.4f} ({relative_reduction:.1%})".format(
                **result
            )
        )


if __name__ == "__main__":
    main()
