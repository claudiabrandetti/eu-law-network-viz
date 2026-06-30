### Notebooks (run in order)
- `00_normattiva` — collect Italian acts from Normattiva (URN-based retrieval)
- `01_data_cleaning`
- `02_extract_subgraph` — build the thematic citation sub-network
- `03_enrich_texts` — retrieve full texts and segment into articles
- `04_layer_inference` — LLM Lamfalussy classification, entropy hybridity, diffusion
- `05_law_splitting` — splitting simulation
- `06_ground_truth` — external validation (MiFID II/MiFIR, ESA founding regulations)
- `0X_fdi_executed` — the same pipeline applied to FDI screening (generalizability test)

## Interactive visualization

Two self-contained HTML files (open in any modern browser, no server needed; include a
light/dark toggle and a pre-split / post-split view):

- **`appalti_it_network.html`** — the populated instance for the Italian public
  procurement corpus (data embedded).
- **`network_template.html`** — the generic template: same interface, with `__data__`
  placeholders instead of embedded data, used to generate new themed visualizations.

To produce a visualization for a new domain, inject the pipeline outputs
(`heatmaps.json`, `splits.json`, node/edge data) into the `__data__` placeholders of
`network_template.html`.

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set the required API key (e.g. in a local `.env`, not committed) before running the
classification notebooks, then execute the notebooks in the order above.

## Data sources

- **Normattiva** — Italian legislation (`https://www.normattiva.it`)
- **EUR-Lex** — EU legislation, via its open API (`https://eur-lex.europa.eu`)

## Author & acknowledgments

Developed by **Claudia Brandetti** in collaboration with the Applied Research Unit of
**Banca d’Italia** (Eng. Luigi Bellomarini) and under the supervision of
**Prof. Blerina Sinaimeri** (Luiss Guido Carli).
