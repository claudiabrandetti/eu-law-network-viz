from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCUREMENT = ROOT / "data" / "output" / "appalti_it"
FDI = ROOT / "data" / "output" / "fdi_screening"


class ReproducibilityTests(unittest.TestCase):
    def test_procurement_canonical_counts(self) -> None:
        hybridity = pd.read_csv(PROCUREMENT / "nodes_hybridity.csv")
        articles = pd.read_csv(PROCUREMENT / "nodes_lamfalussy.csv")
        internal = pd.read_csv(PROCUREMENT / "edges_it_internal.csv")
        eu_edges = pd.read_csv(PROCUREMENT / "edges_eu_it.csv")
        self.assertEqual(len(hybridity), 31)
        self.assertEqual(int(articles["llm_status"].eq("ok").sum()), 1236)
        self.assertEqual(len(internal) + len(eu_edges), 88)
        self.assertAlmostEqual(float(hybridity["hybridity_score"].mean()), 0.4513, places=4)
        self.assertFalse(
            hybridity["celex"].astype(str).str.contains("dm_154_2017").any()
        )

    def test_procurement_diffusion_and_splitting(self) -> None:
        diffusion = pd.read_csv(PROCUREMENT / "nodes_diffusion.csv")
        splits = json.loads((PROCUREMENT / "splits.json").read_text(encoding="utf-8"))
        self.assertEqual(len(diffusion), 31)
        self.assertAlmostEqual(float(diffusion["H_global"].mean()), 0.5195, places=4)
        self.assertEqual(len(splits["splits"]), 13)
        self.assertEqual(
            sum(value["n_blocks"] for value in splits["splits"].values()), 32
        )
        self.assertEqual(splits["meta"]["n_acts_after"], 50)
        self.assertAlmostEqual(splits["meta"]["H_local_after"], 0.3334, places=4)
        self.assertAlmostEqual(
            splits["meta"]["H_local_improvement"], 0.2611, places=4
        )
        self.assertEqual(splits["meta"]["n_unresolved_edges"], 19)
        self.assertFalse(
            any(
                edge.get("resolved_by") == "no_art_info"
                for edge in splits["edges_after"]
            )
        )

    def test_embedded_procurement_graph(self) -> None:
        html = (ROOT / "appalti_it_network.html").read_text(encoding="utf-8")
        nodes = json.loads(
            re.search(r"const NODES\s*=\s*(\[.*?\]);", html, re.DOTALL).group(1)
        )
        edges = json.loads(
            re.search(r"const EDGES\s*=\s*(\[.*?\]);", html, re.DOTALL).group(1)
        )
        self.assertEqual(len(nodes), 31)
        self.assertEqual(len(edges), 88)
        self.assertNotIn("dm_154_2017", html)

    def test_fdi_reaggregation(self) -> None:
        base = FDI / "reaggregated"
        articles = pd.read_csv(base / "nodes_lamfalussy_byarticle.csv")
        acts = pd.read_csv(base / "nodes_hybridity_byarticle.csv")
        splits = pd.read_csv(base / "splitting_byarticle.csv")
        audit = pd.read_csv(base / "reaggregation_audit.csv").iloc[0]
        edges = pd.read_csv(FDI / "edges_focal.csv")
        self.assertEqual(len(articles), 162)
        self.assertEqual(len(acts), 19)
        self.assertEqual(len(edges), 22)
        self.assertEqual(int(splits["outcome"].eq("accepted").sum()), 4)
        self.assertAlmostEqual(float(audit["paired_relative_reduction"]), 0.1447, places=4)
        self.assertAlmostEqual(float(audit["legacy_relative_reduction"]), 0.0506, places=4)

    def test_provenance_manifest(self) -> None:
        manifest_path = ROOT / "data" / "provenance" / "source_manifest_sha256.csv"
        self.assertTrue(manifest_path.exists())
        manifest = pd.read_csv(manifest_path)
        self.assertEqual(int(manifest["source"].eq("EUR-Lex").sum()), 3)
        self.assertTrue(manifest["declared_retrieval_month"].eq("2026-04").all())
        self.assertTrue(manifest["sha256"].str.fullmatch(r"[0-9a-f]{64}").all())


if __name__ == "__main__":
    unittest.main()
