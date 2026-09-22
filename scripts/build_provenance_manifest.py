"""Build immutable snapshot files and SHA-256 provenance manifests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCUREMENT = ROOT / "data" / "output" / "appalti_it"
PROVENANCE = ROOT / "data" / "provenance"
EU_SNAPSHOTS = ROOT / "data" / "snapshots" / "2026-04" / "eurlex"
DECLARED_RETRIEVAL_MONTH = "2026-04"
EXCLUDED_ACTS = {"dm_154_2017"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else ""


def act_from_filename(path: Path) -> tuple[str, str]:
    stem = path.stem
    if "_art_" in stem:
        act, article = stem.split("_art_", 1)
        return act, article
    return stem, ""


def build_eu_snapshots() -> list[Path]:
    source = pd.read_csv(
        PROCUREMENT / "nodes_texts_eu_appalti.csv", dtype={"celex": str}
    )
    EU_SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for row in source.to_dict("records"):
        celex = str(row["celex"])
        payload = {
            "celex": celex,
            "title": row.get("titolo", ""),
            "source": "EUR-Lex",
            "declared_retrieval_month": DECLARED_RETRIEVAL_MONTH,
            "full_text": row.get("full_text", ""),
            "segments": json.loads(row.get("segments", "[]") or "[]"),
        }
        path = EU_SNAPSHOTS / f"{celex}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths.append(path)
    return paths


def build_manifest() -> pd.DataFrame:
    urn_map: dict[str, str] = {}
    nodes = pd.read_csv(PROCUREMENT / "nodes_it.csv", dtype=str)
    for row in nodes.to_dict("records"):
        urn_map[str(row.get("Id", row.get("id", "")))] = str(row.get("urn", ""))

    rows: list[dict[str, object]] = []
    for path in sorted((PROCUREMENT / "raw").glob("*.html")):
        text = path.read_text(encoding="utf-8", errors="replace")
        act, article = act_from_filename(path)
        rows.append(
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "source": "Normattiva",
                "act_id": act,
                "article_id": article,
                "official_identifier": urn_map.get(act, ""),
                "celex": "",
                "publication_date": first_match(
                    r"dataPubblicazioneGazzetta(?:=|%3D)(\d{4}-\d{2}-\d{2})",
                    text,
                ),
                "redaction_code": first_match(
                    r"codiceRedazionale(?:=|%3D)([A-Z0-9]+)", text
                ),
                "source_version": first_match(r"art\.versione=(\d+)", text),
                "declared_retrieval_month": DECLARED_RETRIEVAL_MONTH,
                "included_in_final_corpus": act not in EXCLUDED_ACTS,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    for path in build_eu_snapshots():
        celex = path.stem
        rows.append(
            {
                "relative_path": path.relative_to(ROOT).as_posix(),
                "source": "EUR-Lex",
                "act_id": celex,
                "article_id": "",
                "official_identifier": celex,
                "celex": celex,
                "publication_date": "",
                "redaction_code": "",
                "source_version": "consolidated text stored in repository",
                "declared_retrieval_month": DECLARED_RETRIEVAL_MONTH,
                "included_in_final_corpus": True,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return pd.DataFrame(rows)


def build_analysis_checksums() -> pd.DataFrame:
    paths = [
        ROOT / "notebooks" / "prompt.txt",
        ROOT / "appalti_it_network.html",
        ROOT / "heatmaps.json",
        ROOT / "splits.json",
        PROCUREMENT / "nodes_hybridity.csv",
        PROCUREMENT / "nodes_diffusion.csv",
        PROCUREMENT / "nodes_lamfalussy.csv",
        PROCUREMENT / "edges_it_internal.csv",
        PROCUREMENT / "edges_eu_it.csv",
        ROOT / "data" / "output" / "fdi_screening" / "reaggregated" / "nodes_hybridity_byarticle.csv",
        ROOT / "data" / "output" / "fdi_screening" / "reaggregated" / "splitting_byarticle.csv",
    ]
    rows = []
    for path in paths:
        if path.exists():
            rows.append(
                {
                    "relative_path": path.relative_to(ROOT).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    PROVENANCE.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    manifest.to_csv(PROVENANCE / "source_manifest_sha256.csv", index=False)
    checksums = build_analysis_checksums()
    checksums.to_csv(PROVENANCE / "analysis_files_sha256.csv", index=False)
    print(
        f"Manifested {len(manifest)} source snapshots and "
        f"{len(checksums)} analysis artefacts."
    )


if __name__ == "__main__":
    main()

