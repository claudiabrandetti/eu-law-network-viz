# Data provenance and archival deposit

The public-procurement corpus was delimited using InfoAppalti for the three EU
procurement directives and BibLus for the initial Italian legislative
perimeter. Legal texts were then obtained from Normattiva and EUR-Lex.

The repository declares April 2026 as the extraction month. The provenance
script records each retained Normattiva HTML file with its SHA-256 checksum,
file size, act/article identifier, and any source version, publication date, or
redaction code recoverable from the page. The three EUR-Lex texts are exported
as self-contained JSON snapshots under `data/snapshots/2026-04/eurlex/` and are
also hashed.

`dm_154_2017` was downloaded during corpus construction but is excluded from
the final analytical network. Its raw pages are retained to make that exclusion
auditable and are marked `included_in_final_corpus = false`.

The files in `data/provenance/` prepare the repository for an archival release.
Creating a DOI still requires the author to publish a release through Zenodo or
another repository. Before public deposit, the author should confirm the reuse
terms applicable to the archived source pages and add the resulting DOI to the
paper, release metadata, and citation file.

The FDI corpus can be reconstructed analytically from cached classifications
and network tables, but the original full-text EUR-Lex responses for all 19 FDI
acts were not separately archived. This remains a provenance limitation.
