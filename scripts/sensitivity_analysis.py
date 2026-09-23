"""Run API-free robustness checks for diffusion and splitting parameters."""

from __future__ import annotations

import itertools
from pathlib import Path

import pandas as pd

from analysis_core import LEVEL_COLUMNS, deterministic_partition, diffuse, load_edges


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "data" / "output"
ROBUSTNESS_DIR = OUTPUT_ROOT / "robustness"
DOMAINS = ("appalti_it", "fdi_screening")


def domain_data(domain: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output = OUTPUT_ROOT / domain
    if domain == "fdi_screening":
        articles = pd.read_csv(
            output / "reaggregated" / "nodes_lamfalussy_byarticle.csv",
            dtype={"celex": str, "articolo_id": str},
        )
        acts = pd.read_csv(
            output / "reaggregated" / "nodes_hybridity_byarticle.csv",
            dtype={"celex": str},
        )
    else:
        articles = pd.read_csv(
            output / "nodes_lamfalussy.csv",
            dtype={"celex": str, "articolo_id": str},
        )
        articles = articles.loc[articles["llm_status"].eq("ok")].copy()
        acts = pd.read_csv(output / "nodes_hybridity.csv", dtype={"celex": str})
        acts = acts.loc[acts["n_articles"].gt(0)].copy()
    return articles, acts, load_edges(output)


def diffusion_sensitivity() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for domain in DOMAINS:
        _, acts, edges = domain_data(domain)
        for restart_weight, weighted in itertools.product(
            (0.25, 0.50, 0.75), (False, True)
        ):
            result, transition = diffuse(
                acts[["celex", *LEVEL_COLUMNS]],
                edges,
                restart_weight=restart_weight,
                weighted=weighted,
            )
            rows.append(
                {
                    "domain": domain,
                    "lambda": restart_weight,
                    "edge_weighting": "stored_weights" if weighted else "unweighted",
                    "n_acts": int(len(acts)),
                    "n_edges": int(len(edges)),
                    "n_rows_with_outgoing_edges": int(
                        (transition.sum(axis=1) > 0).sum()
                    ),
                    "mean_H_local": float(result["H_local"].mean()),
                    "mean_H_global": float(result["H_global"].mean()),
                    "mean_H_delta": float(
                        (result["H_global"] - result["H_local"]).mean()
                    ),
                    "canonical_setting": bool(
                        restart_weight == 0.50 and weighted
                    ),
                }
            )
    return pd.DataFrame(rows)


def splitting_sensitivity() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for domain in DOMAINS:
        articles, acts, _ = domain_data(domain)
        baseline_mean = float(acts["hybridity_score"].mean())
        for h_threshold, min_articles, min_block, min_improvement in itertools.product(
            (0.30, 0.35, 0.40),
            (6, 8, 10),
            (3, 4, 5),
            (0.25, 0.30, 0.35),
        ):
            accepted: dict[str, float] = {}
            candidate_count = 0
            for act in acts.itertuples(index=False):
                celex = str(act.celex)
                if (
                    float(act.hybridity_score) < h_threshold
                    or int(act.n_articles) < min_articles
                ):
                    continue
                candidate_count += 1
                proposal = deterministic_partition(
                    articles.loc[articles["celex"].astype(str).eq(celex)],
                    min_block=min_block,
                    min_improvement=min_improvement,
                )
                if proposal is not None:
                    accepted[celex] = float(proposal["H_after"])

            paired_after = [
                accepted.get(str(act.celex), float(act.hybridity_score))
                for act in acts.itertuples(index=False)
            ]
            after_mean = float(pd.Series(paired_after).mean())
            rows.append(
                {
                    "domain": domain,
                    "hybridity_threshold": h_threshold,
                    "min_articles": min_articles,
                    "min_block": min_block,
                    "min_improvement": min_improvement,
                    "n_candidates": candidate_count,
                    "n_accepted_pre_validation": len(accepted),
                    "H_before_paired": baseline_mean,
                    "H_after_paired": after_mean,
                    "relative_reduction": (
                        (baseline_mean - after_mean) / baseline_mean
                        if baseline_mean
                        else 0.0
                    ),
                    "canonical_thresholds": bool(
                        h_threshold == 0.35
                        and min_articles == 8
                        and min_block == 4
                        and min_improvement == 0.30
                    ),
                    "stage": "deterministic_pre_validation",
                }
            )
    return pd.DataFrame(rows)


def write_summary(diffusion: pd.DataFrame, splitting: pd.DataFrame) -> None:
    lines = [
        "# Sensitivity analysis",
        "",
        "All calculations use cached classifications and make no API calls.",
        "Diffusion varies the restart weight and whether stored relation weights are used.",
        "Splitting varies the four deterministic proposal thresholds; it does not rerun the historical LLM validation stage.",
        "",
    ]
    for domain in DOMAINS:
        d_domain = diffusion.loc[diffusion["domain"].eq(domain)]
        s_domain = splitting.loc[splitting["domain"].eq(domain)]
        canonical_d = d_domain.loc[d_domain["canonical_setting"]].iloc[0]
        canonical_s = s_domain.loc[s_domain["canonical_thresholds"]].iloc[0]
        lines.extend(
            [
                f"## {domain}",
                "",
                f"- Canonical diffusion: mean H_global = {canonical_d['mean_H_global']:.4f} at lambda = 0.50 with stored weights.",
                f"- Across diffusion settings: mean H_global = {d_domain['mean_H_global'].min():.4f}–{d_domain['mean_H_global'].max():.4f}.",
                f"- Canonical deterministic thresholds: {int(canonical_s['n_accepted_pre_validation'])} proposals, paired reduction = {canonical_s['relative_reduction']:.1%}.",
                f"- Across threshold settings: {int(s_domain['n_accepted_pre_validation'].min())}–{int(s_domain['n_accepted_pre_validation'].max())} proposals; paired reduction = {s_domain['relative_reduction'].min():.1%}–{s_domain['relative_reduction'].max():.1%}.",
                "",
            ]
        )
    (ROBUSTNESS_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ROBUSTNESS_DIR.mkdir(parents=True, exist_ok=True)
    diffusion = diffusion_sensitivity()
    splitting = splitting_sensitivity()
    diffusion.to_csv(ROBUSTNESS_DIR / "diffusion_sensitivity.csv", index=False)
    splitting.to_csv(ROBUSTNESS_DIR / "splitting_sensitivity.csv", index=False)
    write_summary(diffusion, splitting)
    print(
        f"Wrote {len(diffusion)} diffusion scenarios and "
        f"{len(splitting)} splitting scenarios to {ROBUSTNESS_DIR}."
    )


if __name__ == "__main__":
    main()

