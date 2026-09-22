"""Prepare, but do not claim, an independent expert-annotation sample."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "output" / "appalti_it"
DESTINATION = ROOT / "data" / "review"


def main() -> None:
    articles = pd.read_csv(OUTPUT / "nodes_lamfalussy.csv", dtype={"celex": str})
    articles = articles.loc[articles["llm_status"].eq("ok")].copy()
    heatmaps = json.loads((OUTPUT / "heatmaps.json").read_text(encoding="utf-8"))
    texts = {
        (str(celex), str(article.get("id", ""))): str(article.get("txt", ""))
        for celex, values in heatmaps.items()
        for article in values
    }

    selected_indices: list[int] = []
    for level in ("L1", "L2", "L3", "L4"):
        group = articles.loc[articles["dominant_lamf"].eq(level)]
        selected_indices.extend(group.nlargest(5, "entropy").index.tolist())
        selected_indices.extend(group.nsmallest(5, "entropy").index.tolist())
    sample = articles.loc[sorted(set(selected_indices))].copy()
    sample["article_text"] = [
        texts.get((str(row.celex), str(row.articolo_id)), "")
        for row in sample.itertuples(index=False)
    ]
    sample["expert_1_label"] = ""
    sample["expert_1_comment"] = ""
    sample["expert_2_label"] = ""
    sample["expert_2_comment"] = ""
    sample["adjudicated_label"] = ""
    sample["adjudication_comment"] = ""

    columns = [
        "celex",
        "articolo_id",
        "article_text",
        "lamf_L1",
        "lamf_L2",
        "lamf_L3",
        "lamf_L4",
        "entropy",
        "dominant_lamf",
        "expert_1_label",
        "expert_1_comment",
        "expert_2_label",
        "expert_2_comment",
        "adjudicated_label",
        "adjudication_comment",
    ]
    DESTINATION.mkdir(parents=True, exist_ok=True)
    sample.loc[:, columns].to_csv(
        DESTINATION / "independent_annotation_sample.csv", index=False
    )
    print(f"Prepared {len(sample)} records for future independent annotation.")


if __name__ == "__main__":
    main()

