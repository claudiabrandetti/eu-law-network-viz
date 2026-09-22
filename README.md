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
calculation is 0.3482 to 0.2978 (a 14.5% reduction). The previously stored 5.1%
figure compared 19 acts before splitting with 24 units after splitting; it is
retained in `reaggregation_audit.csv` only to make that earlier calculation
traceable.

## Reproduce the reported analyses without an API

The repository stores the model classifications and split-validation decisions
used for the study. The final results can therefore be rebuilt without access
to GPT-4.1-mini and without an OpenAI API key.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/reproduce_cached.py
```

The cached reproduction path:

1. reconstructs the FDI article-level data from cached fragment labels;
2. removes the excluded procurement act from all final derived artefacts;
3. rebuilds the procurement visualization and post-split graph;
4. runs diffusion and splitting sensitivity analyses;
5. creates the future independent-review sample;
6. creates source snapshots and SHA-256 manifests;
7. runs the automated verification suite.

No script under `scripts/` imports the OpenAI client or sends model requests.
The original notebooks remain as the historical full pipeline and include API
stages. They are not required to reproduce the reported outputs.

To run only the checks:

```bash
python -m unittest discover -s tests -v
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
`system_fingerprint` were not retained; see `docs/MODEL_PROVENANCE.md`.

## Post-split relations

The historical notebook sent an act-level relation to the first split block
when it could not identify the citing article. This fallback has been removed.
Relations with a cached article match or cached target resolution remain in the
post-split graph. Nineteen remaining relations are stored in
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

## Validation scope

Legal expertise informed the functional schema and prompt design. The
repository also contains construct-validation outputs and a qualitative audit
trail. It does not contain a completed, independently annotated multi-expert
gold standard. `data/review/independent_annotation_sample.csv` is an unfilled
template for such future work and must not be cited as completed validation.
See `docs/VALIDATION_SCOPE.md`.

## Author and acknowledgments

Developed by **Claudia Brandetti** in collaboration with the Applied Research
Unit of **Banca d'Italia** (Eng. Luigi Bellomarini) and under the supervision of
**Prof. Blerina Sinaimeri** (Luiss Guido Carli).
