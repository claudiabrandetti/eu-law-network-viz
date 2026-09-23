# EU law network: functional hybridity and citation diffusion

This repository contains the data-processing notebooks, cached Lamfalussy
classifications, deterministic analyses, and interactive visualization used to
study functional hybridity in public-procurement legislation. A second corpus
on foreign-direct-investment (FDI) screening tests whether the pipeline can be
transferred to another regulatory domain.

## Final analytical corpus

The final procurement network contains:

- 31 acts: 28 Italian acts and three EU directives;
- 88 act-level relations;
- 1,236 retained articles with a valid cached classification;
- 13 accepted splitting proposals producing 32 blocks and 50 post-split units;
- mean local hybridity of 0.4513 and mean diffused hybridity of 0.5195;
- paired post-split local hybridity of 0.3334, a 26.1% reduction.

`dm_154_2017` is not part of the final corpus. Its downloaded source files are
kept only for provenance and are marked as excluded in the source manifest.

The FDI corpus contains 19 acts, 22 relations and 162 reaggregated articles.
Four deterministic splits are accepted. The comparable paired act-level
calculation is 0.3482 to 0.2978 (a 14.5% reduction). The article- and act-level
results are stored under `data/output/fdi_screening/reaggregated/`.
The top-level `segments_lamfalussy*.csv` and `nodes_lamfalussy.csv` files are
cached fragment-level inputs to that reaggregation, not final FDI statistics.
Obsolete fragment-weighted summaries and split files have been removed.

## Pipeline and cached results

The repository already contains the classifications and analytical outputs
used in the paper. The notebook sequence is the authoritative pipeline:

1. notebooks 00--03 construct and enrich the corpus;
2. notebook 04 classifies the provisions and calculates article-, act-, and
   network-level hybridity;
3. for FDI, the reaggregation cell at the end of notebook 04 reconstructs the
   162 legal articles from the cached paragraph fragments;
4. notebook 05 reads those reaggregated FDI outputs before applying splitting.

The reaggregation and subsequent calculations are deterministic and make no
model call. Re-running the original classification and validation cells does
require API access and constitutes a new experiment. The reusable mathematical
functions used by the deterministic cells are in `scripts/analysis_core.py`.

The supplementary deterministic outputs can be refreshed with:

```bash
python scripts/sensitivity_analysis.py
python scripts/build_provenance_manifest.py
```

## Original notebooks

- `00_normattiva.ipynb`: retrieve and parse Italian acts from Normattiva;
- `01_data_cleaning.ipynb`: clean the EU legislative graph;
- `02_extract_subgraph.ipynb`: construct a thematic citation sub-network;
- `03_enrich_texts.ipynb`: retrieve and segment texts;
- `04_layer_inference.ipynb`: classify spans and calculate hybridity/diffusion;
- `05_law_splitting.ipynb`: generate and validate splitting proposals;
- `06_ground_truth.ipynb`: construct validation with formally assigned
  Lamfalussy instruments;
- `0X_fdi_executed.ipynb`: executed FDI transfer-case notebooks.

Running the model stages again is a new experiment and may not reproduce the
cached classifications exactly. The exact model snapshot and
`system_fingerprint` were not retained. The stored records identify the model
alias `gpt-4.1-mini`, temperature zero, prompt, schema and cached responses.

## Post-split relations

The historical notebook sent an act-level relation to the first split block
when it could not identify the citing article. This fallback has been removed.
Relations with a cached article match or cached target resolution remain in the
post-split graph. Five previously flagged relations connect unsplit acts and
therefore remain unchanged. Four more identify their destination article
explicitly and are routed deterministically. The ten genuinely act-level or
otherwise non-attributable relations are stored in
`data/output/appalti_it/unresolved_edges.csv` and excluded from block-level
diffusion until they can be reviewed. This does not affect the pre-split
network or the paired local splitting result.

## Robustness outputs

`data/output/robustness/` contains diffusion results for lambda values 0.25,
0.50 and 0.75; weighted and unweighted relation variants; and a grid over the
four deterministic splitting thresholds. The splitting grid concerns the
deterministic pre-validation stage and does not rerun model validation.

## Data sources and provenance

- [InfoAppalti](https://www.infoappalti.it/normativa/index.htm) was used to
  identify the three relevant EU procurement directives.
- [BibLus](https://biblus.acca.it/nuovo-codice-appalti-2023/) was used as a
  starting compendium for delimiting the Italian procurement legislation.
- [Normattiva](https://www.normattiva.it) supplied the Italian legal texts.
- [EUR-Lex](https://eur-lex.europa.eu) supplied the EU legal texts and the
  EuroVoc/citation data used for the FDI transfer case.

The first two sources delimit the corpus; they are not the authoritative text
sources. The text snapshots are declared as retrieved in April 2026. File
hashes and available identifiers are recorded in
`data/provenance/source_manifest_sha256.csv`. The repository prepares the data
for archival deposit, but no DOI has been assigned yet.

## Interactive visualization

- `appalti_it_network.html` is the populated procurement visualization.
- `network_template.html` is the reusable template.
- `heatmaps.json` and `splits.json` are loaded next to the HTML file.

The pre-split view contains 31 acts and 88 relations. The post-split banner also
reports unresolved block-level relations instead of hiding them behind an
arbitrary fallback.

### Static website

The production visualization is available at
[eu-law-network-viz-a5nc.vercel.app](https://eu-law-network-viz-a5nc.vercel.app/).

The `public/` directory contains only the files needed to display the
procurement visualization: `index.html`, `heatmaps.json`, and `splits.json`.
Refresh it whenever the source visualization or either JSON file changes:

```bash
python scripts/build_public.py
```

In the Vercel project's **Settings > Build and Deployment**, set **Root
Directory** to `public`, **Framework Preset** to **Other**, and override the
**Build Command** with an empty value. Leave the **Output Directory** at its
default (do not set it to `public` again, because `public` is now the project
root). This keeps Vercel from treating the repository-level `requirements.txt`
as a Python application. The root-level `vercel.json` alone did not prevent
Python detection in this project. The production deployment tracks `main`;
other branches can be used for previews. The deployed site serves cached
results; classification and splitting are performed in the notebooks, not by
the site.

## Validation scope

Legal expertise informed the functional schema and prompt design. The
repository also contains construct-validation outputs and a qualitative audit
trail. It does not contain a completed, independently annotated multi-expert
gold standard and therefore does not claim clause-level precision, recall or
inter-annotator agreement.

## Author and acknowledgments

Developed by **Claudia Brandetti** in collaboration with the Applied Research
Unit of **Banca d'Italia** (Eng. Luigi Bellomarini) and under the supervision of
**Prof. Blerina Sinaimeri** (Luiss Guido Carli).
