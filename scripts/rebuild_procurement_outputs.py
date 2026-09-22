"""Remove the repealed act and rebuild final procurement artefacts from cache.

No classification or split-validation API is called.  Existing accepted split
decisions and titles are retained.  Edges that the historical notebook routed
to the first block solely because article information was absent are moved to a
separate unresolved-edge audit instead of being assigned arbitrarily.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from analysis_core import LEVEL_COLUMNS, LEVELS, diffuse


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "output" / "appalti_it"
EXCLUDED_ACTS = {"dm_154_2017"}


def base_act(node_id: object) -> str:
    return str(node_id).split("__", 1)[0]


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def filter_csv(path: Path, columns: tuple[str, ...]) -> int:
    if not path.exists():
        return 0
    frame = pd.read_csv(path)
    keep = pd.Series(True, index=frame.index)
    for column in columns:
        if column in frame.columns:
            keep &= ~frame[column].astype(str).map(base_act).isin(EXCLUDED_ACTS)
    removed = int((~keep).sum())
    frame.loc[keep].to_csv(path, index=False)
    return removed


def filter_derived_tables() -> dict[str, int]:
    rules = {
        "nodes_it.csv": ("Id", "id", "celex"),
        "nodes_texts_it.csv": ("Id", "id", "celex"),
        "nodes_hybridity.csv": ("celex", "Id"),
        "nodes_lamfalussy.csv": ("celex", "node_id"),
        "segments_lamfalussy.csv": ("celex", "node_id"),
        "segments_lamfalussy_checkpoint.csv": ("celex", "node_id"),
        "edges_it.csv": ("src_slug", "dst_slug"),
        "edges_it_internal.csv": ("src_slug", "dst_slug"),
    }
    removed = {
        name: filter_csv(OUTPUT / name, columns) for name, columns in rules.items()
    }

    validation = OUTPUT / "validation_report.csv"
    if validation.exists():
        frame = pd.read_csv(validation)
        mask = ~frame.get("label", pd.Series("", index=frame.index)).astype(
            str
        ).str.contains(r"154\s*/\s*2017", regex=True)
        removed[validation.name] = int((~mask).sum())
        frame.loc[mask].to_csv(validation, index=False)
    return removed


def filter_heatmaps() -> dict[str, object]:
    path = OUTPUT / "heatmaps.json"
    heatmaps = json.loads(path.read_text(encoding="utf-8"))
    for act in EXCLUDED_ACTS:
        heatmaps.pop(act, None)
    write_json(path, heatmaps)
    write_json(ROOT / "heatmaps.json", heatmaps)
    return heatmaps


def rebuild_pre_split_diffusion() -> pd.DataFrame:
    """Recompute diffusion on the actual 31-node, 88-edge final network."""
    hybridity = pd.read_csv(OUTPUT / "nodes_hybridity.csv", dtype={"celex": str})
    hybridity = hybridity.loc[hybridity["n_articles"].gt(0)].copy()
    edges = pd.concat(
        [
            pd.read_csv(OUTPUT / "edges_it_internal.csv"),
            pd.read_csv(OUTPUT / "edges_eu_it.csv"),
        ],
        ignore_index=True,
    )
    diffusion, _ = diffuse(
        hybridity[["celex", *LEVEL_COLUMNS]],
        edges,
        restart_weight=0.5,
        weighted=True,
    )
    for column in ("H_local", "H_global", "H_delta"):
        diffusion[column] = diffusion[column].round(4)
    for level in LEVELS:
        diffusion[f"lamf_glob_{level}"] = diffusion[
            f"lamf_glob_{level}"
        ].round(2)
    diffusion.to_csv(OUTPUT / "nodes_diffusion.csv", index=False)
    return diffusion


def original_unresolved(edge: dict[str, object]) -> dict[str, object]:
    return {
        "source_act": base_act(edge.get("source", "")),
        "target_act": base_act(edge.get("target", "")),
        "type": edge.get("type", "CITES"),
        "family": edge.get("family", "ref"),
        "w": edge.get("w", 1),
        "resolution_status": "unresolved_no_article_reference",
        "reason": (
            "The stored act-level relation does not identify a source article; "
            "no split block is assigned without additional legal review."
        ),
    }


def rebuild_splits(heatmaps: dict[str, object]) -> dict[str, object]:
    path = OUTPUT / "splits.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    splits = {
        act: value
        for act, value in payload.get("splits", {}).items()
        if act not in EXCLUDED_ACTS
    }

    resolved: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []
    for edge in payload.get("edges_after", []):
        if base_act(edge.get("source", "")) in EXCLUDED_ACTS or base_act(
            edge.get("target", "")
        ) in EXCLUDED_ACTS:
            continue
        if edge.get("resolved_by") == "no_art_info":
            unresolved.append(original_unresolved(edge))
        else:
            resolved.append(edge)

    # Preserve the audit on idempotent reruns.
    for edge in payload.get("unresolved_edges", []):
        if edge.get("source_act") not in EXCLUDED_ACTS and edge.get(
            "target_act"
        ) not in EXCLUDED_ACTS:
            unresolved.append(edge)
    unique_unresolved = {
        (
            edge["source_act"],
            edge["target_act"],
            edge["type"],
            edge["family"],
        ): edge
        for edge in unresolved
    }
    unresolved = list(unique_unresolved.values())

    hybridity = pd.read_csv(OUTPUT / "nodes_hybridity.csv")
    hybridity = hybridity.loc[hybridity["n_articles"].gt(0)].copy()
    hybridity["celex"] = hybridity["celex"].astype(str)

    post_rows: list[dict[str, object]] = []
    for row in hybridity.itertuples(index=False):
        celex = str(row.celex)
        if celex in splits:
            continue
        post_rows.append(
            {"celex": celex, **{column: getattr(row, column) for column in LEVEL_COLUMNS}}
        )
    for celex, split in splits.items():
        for block in split["blocks"]:
            post_rows.append(
                {
                    "celex": block["block_id"],
                    **{
                        f"lamf_{level}": float(block.get("lamf_avg", {}).get(level, 0))
                        for level in LEVELS
                    },
                }
            )
    post_local = pd.DataFrame(post_rows)
    edge_frame = pd.DataFrame(
        [
            {
                "src_slug": edge["source"],
                "dst_slug": edge["target"],
                "family": edge.get("family", "ref"),
                "w": edge.get("w", 1),
            }
            for edge in resolved
        ]
    )
    post_diffusion, _ = diffuse(post_local, edge_frame, restart_weight=0.5)
    post_diffusion = post_diffusion.set_index("celex")

    for split in splits.values():
        for block in split["blocks"]:
            row = post_diffusion.loc[block["block_id"]]
            block["H_global"] = round(float(row["H_global"]), 4)
            block["lamf_glob"] = {
                level: round(float(row[f"lamf_glob_{level}"]), 1)
                for level in LEVELS
            }
            block["heatmap"] = [
                article
                for article in heatmaps.get(split["celex"], [])
                if str(article.get("id", ""))
                in {str(value) for value in block.get("article_ids", [])}
            ]

    paired_local_after: list[float] = []
    paired_global_after: list[float] = []
    for row in hybridity.itertuples(index=False):
        celex = str(row.celex)
        if celex not in splits:
            paired_local_after.append(float(row.hybridity_score))
            paired_global_after.append(float(post_diffusion.loc[celex, "H_global"]))
            continue
        blocks = splits[celex]["blocks"]
        total_articles = sum(int(block["n_articles"]) for block in blocks)
        paired_local_after.append(
            sum(
                int(block["n_articles"]) * float(block["H_block"])
                for block in blocks
            )
            / total_articles
        )
        paired_global_after.append(
            sum(
                int(block["n_articles"])
                * float(post_diffusion.loc[block["block_id"], "H_global"])
                for block in blocks
            )
            / total_articles
        )

    diffusion_before = pd.read_csv(OUTPUT / "nodes_diffusion.csv")
    local_before = float(hybridity["hybridity_score"].mean())
    local_after = float(pd.Series(paired_local_after).mean())
    global_before = float(diffusion_before["H_global"].mean())
    global_after = float(pd.Series(paired_global_after).mean())
    block_count = sum(int(split["n_blocks"]) for split in splits.values())

    meta = payload.get("meta", {})
    meta.update(
        {
            "H_local_before": round(local_before, 4),
            "H_local_after": round(local_after, 4),
            "H_local_improvement": round(
                (local_before - local_after) / local_before, 4
            ),
            "H_global_before": round(global_before, 4),
            "H_global_after": round(global_after, 4),
            "H_global_improvement": round(
                (global_before - global_after) / global_before, 4
            ),
            "n_acts_before": int(len(hybridity)),
            "n_acts_after": int(len(hybridity) - len(splits) + block_count),
            "n_scored_acts_before": int(len(hybridity)),
            "n_scored_units_after": int(
                len(hybridity) - len(splits) + block_count
            ),
            "n_split": int(len(splits)),
            "n_edges_before": 88,
            "n_edges_after_resolved": int(len(resolved)),
            "n_unresolved_edges": int(len(unresolved)),
            "unresolved_edge_policy": (
                "Retained in unresolved_edges and excluded from block-level "
                "diffusion; no first-block fallback is used."
            ),
        }
    )
    rebuilt = {
        "meta": meta,
        "splits": splits,
        "edges_after": resolved,
        "unresolved_edges": unresolved,
    }
    write_json(path, rebuilt)
    write_json(ROOT / "splits.json", rebuilt)
    pd.DataFrame(unresolved).to_csv(OUTPUT / "unresolved_edges.csv", index=False)
    return rebuilt


def rebuild_html() -> tuple[int, int]:
    html_path = ROOT / "appalti_it_network.html"
    html = html_path.read_text(encoding="utf-8")

    node_match = re.search(r"const NODES\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not node_match:
        raise ValueError("Embedded NODES array not found")
    nodes = [
        node
        for node in json.loads(node_match.group(1))
        if base_act(node.get("id", "")) not in EXCLUDED_ACTS
    ]
    diffusion = pd.read_csv(OUTPUT / "nodes_diffusion.csv").set_index("celex")
    for node in nodes:
        node_id = str(node["id"])
        if node_id not in diffusion.index:
            continue
        row = diffusion.loc[node_id]
        node["H"] = round(float(row["H_local"]), 3)
        node["H_local"] = round(float(row["H_local"]), 3)
        node["H_global"] = round(float(row["H_global"]), 3)
        node["H_delta"] = round(float(row["H_delta"]), 3)
        node["lamf_glob"] = {
            level: round(float(row[f"lamf_glob_{level}"]), 1) for level in LEVELS
        }

    edge_frames = [
        pd.read_csv(OUTPUT / "edges_it_internal.csv"),
        pd.read_csv(OUTPUT / "edges_eu_it.csv"),
    ]
    edges = []
    for row in pd.concat(edge_frames, ignore_index=True).itertuples(index=False):
        edges.append(
            {
                "s": str(row.src_slug),
                "t": str(row.dst_slug),
                "family": str(row.family),
                "w": float(row.w),
            }
        )

    html = html[: node_match.start(1)] + json.dumps(
        nodes, ensure_ascii=False
    ) + html[node_match.end(1) :]
    edge_match = re.search(r"const EDGES\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not edge_match:
        raise ValueError("Embedded EDGES array not found")
    html = html[: edge_match.start(1)] + json.dumps(
        edges, ensure_ascii=False
    ) + html[edge_match.end(1) :]
    html_path.write_text(html, encoding="utf-8")
    return len(nodes), len(edges)


def main() -> None:
    removed = filter_derived_tables()
    heatmaps = filter_heatmaps()
    diffusion = rebuild_pre_split_diffusion()
    splits = rebuild_splits(heatmaps)
    node_count, edge_count = rebuild_html()
    print("Removed rows:")
    for name, count in removed.items():
        print(f"  {name}: {count}")
    print(
        f"Final procurement network: {node_count} nodes, {edge_count} edges; "
        f"{splits['meta']['n_acts_after']} post-split units, "
        f"{splits['meta']['n_unresolved_edges']} unresolved post-split edges."
    )
    print(f"Mean pre-split H_global: {diffusion['H_global'].mean():.4f}")


if __name__ == "__main__":
    main()
