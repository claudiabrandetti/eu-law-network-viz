# Model provenance

The cached classifications identify the model alias `gpt-4.1-mini`. The
notebooks record temperature 0, a maximum output length of 2,000 tokens for
classification, three retries, five classification workers, and a maximum
document-context length of 40,000 characters. Splitting validation used the
same alias with a maximum output length of 3,000 tokens.

The exact dated model snapshot, response identifiers, and
`system_fingerprint` were not stored. A search of the repository and its
notebook history did not recover them. Consequently, the repository does not
claim retrospectively that a particular dated snapshot was used.

The prompt is preserved in `notebooks/prompt.txt`; span labels, evidence, and
parsed provisions are preserved in the domain output CSV files. The scripts in
`scripts/` use those cached records and do not call a model API. A fresh API run
should be treated as a new experiment rather than as a bit-for-bit reproduction
of the original classifications.
