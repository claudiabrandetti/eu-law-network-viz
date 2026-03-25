"""
================================================================================
03_enrich_texts_backend.py
================================================================================

Modulo backend per l'arricchimento testi.
Contiene la logica di lookup importabile dal backend FastAPI.

UTILIZZO:
    from notebooks.03_enrich_texts_backend import (
        load_text_cache,
        get_texts_for_nodes,
    )

    text_cache = load_text_cache(proc_path)

    # Dopo aver ottenuto focal_nodes da 02_extract_subgraph_backend:
    nodes_with_texts, missing = get_texts_for_nodes(focal_nodes, text_cache)

RESPONSABILITÀ DI QUESTO MODULO:
    Solo lookup nella cache globale (data/processed/nodes_texts.csv).
    Il modulo NON fa scraping EUR-Lex — quella è un'operazione batch
    offline eseguita dal notebook 03_enrich_texts.ipynb.

    La separazione è intenzionale: EUR-Lex ha rate limit di ~1 richiesta/secondo.
    Mettere scraping in una request HTTP bloccherebbe il server per minuti.

RELAZIONE CON IL NOTEBOOK:
    03_enrich_texts.ipynb  →  batch offline: scraping + costruzione cache
    questo file            →  runtime: lookup veloce dalla cache

FLUSSO TIPICO IN PRODUZIONE:
    1. Utente lancia pipeline da UI → POST /analyze
    2. FastAPI chiama extract_subgraph() dal modulo 02 → focal_nodes
    3. FastAPI chiama get_texts_for_nodes() da questo modulo → testi dalla cache
    4. FastAPI chiama layer inference dal modulo 04 → heatmap

    Se alcuni CELEX non sono in cache, get_texts_for_nodes() li segnala
    nella lista `missing` — il frontend può mostrare un avviso.

DIPENDENZE:
    pip install pandas
================================================================================
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# Strutture dati
# ──────────────────────────────────────────────────────────────────────────────

# Colonne testo presenti nella cache globale
TEXT_COLS = [
    'title', 'preamble', 'articles', 'annexes',
    'full_text', 'segments', 'n_segments',
    'sections_found', 'text_status', 'text_length',
]


@dataclass
class TextCache:
    """
    Cache globale dei testi EUR-Lex caricata in memoria.
    Viene istanziata una volta all'avvio del server e riutilizzata
    per tutte le richieste successive.
    """
    lookup:    pd.DataFrame   # index = CELEX (Label), colonne = TEXT_COLS
    cache_path: str           # percorso del file sorgente (per reload)
    n_entries: int            # numero di CELEX disponibili


@dataclass
class TextEnrichmentResult:
    """
    Risultato dell'arricchimento testi per un insieme di nodi focali.
    Restituito a FastAPI.
    """
    nodes_with_texts: pd.DataFrame    # focal_nodes + colonne testo
    missing_celexes:  list[str]       # CELEX non trovati in cache
    coverage_pct:     float           # % nodi con testo disponibile
    meta: dict = field(default_factory=dict)
    # meta keys:
    #   n_total, n_found, n_missing, cache_size


# ──────────────────────────────────────────────────────────────────────────────
# Caricamento cache
# ──────────────────────────────────────────────────────────────────────────────

def load_text_cache(proc_path: str) -> TextCache:
    """
    Carica la cache globale dei testi da data/processed/nodes_texts.csv.

    Va chiamata una volta all'avvio del server FastAPI e riusata per
    tutte le richieste. Il file viene tenuto in memoria come DataFrame
    indicizzato per CELEX.

    Parametri
    ---------
    proc_path : str
        Percorso a data/processed/ — stessa cartella usata da load_corpus().

    Raises
    ------
    FileNotFoundError
        Se la cache non esiste. Significa che il notebook 03 non è ancora
        stato eseguito. Il messaggio spiega cosa fare.
    ValueError
        Se la cache ha un formato incompatibile (colonna full_text_excerpt
        invece di full_text — versione precedente del notebook).
    """
    cache_path = os.path.join(proc_path, 'nodes_texts.csv')

    if not os.path.exists(cache_path):
        raise FileNotFoundError(
            f"Cache testi non trovata: {cache_path}\n"
            "Esegui prima il notebook 03_enrich_texts.ipynb per costruire la cache."
        )

    df = pd.read_csv(cache_path, low_memory=False)

    # Controllo compatibilità formato
    if 'full_text' not in df.columns:
        if 'full_text_excerpt' in df.columns:
            raise ValueError(
                f"La cache in {cache_path} è nel formato precedente "
                "(colonna 'full_text_excerpt'). "
                "Riesegui il notebook 03_enrich_texts.ipynb per rigenerare la cache."
            )
        raise ValueError(
            f"La cache in {cache_path} non contiene la colonna 'full_text'. "
            f"Colonne trovate: {list(df.columns)}"
        )

    # Mantieni solo le righe con estrazione riuscita
    df_ok = df[df['text_status'] == 'ok'].copy()

    # Costruisci il lookup indicizzato per CELEX
    lookup = df_ok.set_index('Label')[TEXT_COLS]

    return TextCache(
        lookup=lookup,
        cache_path=cache_path,
        n_entries=len(lookup),
    )


def reload_text_cache(cache: TextCache) -> TextCache:
    """
    Ricarica la cache da disco senza riavviare il server.

    Utile dopo una nuova esecuzione del notebook 03 che ha aggiunto
    CELEX alla cache globale.
    """
    proc_path = os.path.dirname(cache.cache_path)
    return load_text_cache(proc_path)


# ──────────────────────────────────────────────────────────────────────────────
# Lookup testi per nodi focali
# ──────────────────────────────────────────────────────────────────────────────

def get_texts_for_nodes(
    focal_nodes: pd.DataFrame,
    text_cache: TextCache,
    celex_col: str = 'celex',
) -> TextEnrichmentResult:
    """
    Arricchisce i nodi focali con i testi dalla cache globale.

    Per ogni nodo in focal_nodes, cerca il CELEX corrispondente nella
    cache e aggiunge le colonne testo (full_text, segments, ecc.).
    I nodi senza testo in cache vengono inclusi con text_status='not_in_cache'.

    Parametri
    ---------
    focal_nodes : pd.DataFrame
        Output di extract_subgraph() dal modulo 02. Deve avere una colonna
        con i codici CELEX (nome configurabile con celex_col).
    text_cache : TextCache
        Cache caricata con load_text_cache().
    celex_col : str
        Nome della colonna CELEX in focal_nodes (default 'celex').
        Usa 'Label' se focal_nodes viene da nodes_focal.csv.

    Restituisce
    -----------
    TextEnrichmentResult con:
        nodes_with_texts  — focal_nodes + colonne testo (TEXT_COLS)
        missing_celexes   — CELEX non trovati in cache
        coverage_pct      — percentuale di nodi con testo
        meta              — statistiche riepilogative
    """
    if celex_col not in focal_nodes.columns:
        raise ValueError(
            f"Colonna CELEX '{celex_col}' non trovata in focal_nodes. "
            f"Colonne disponibili: {list(focal_nodes.columns)}"
        )

    nodes = focal_nodes.copy()

    # Join con la cache
    enriched = nodes.join(text_cache.lookup, on=celex_col, how='left')

    # Nodi senza testo in cache
    mask_missing   = enriched['text_status'].isna()
    missing_celexes = enriched.loc[mask_missing, celex_col].dropna().tolist()

    enriched['text_status'] = enriched['text_status'].fillna('not_in_cache')
    enriched['n_segments']  = enriched['n_segments'].fillna(0).astype(int)
    enriched['text_length'] = enriched['text_length'].fillna(0).astype(int)

    n_total   = len(enriched)
    n_found   = (enriched['text_status'] == 'ok').sum()
    n_missing = len(missing_celexes)
    coverage  = round(n_found / n_total * 100, 1) if n_total > 0 else 0.0

    meta = {
        'n_total':    n_total,
        'n_found':    int(n_found),
        'n_missing':  n_missing,
        'coverage_pct': coverage,
        'cache_size': text_cache.n_entries,
    }

    return TextEnrichmentResult(
        nodes_with_texts=enriched,
        missing_celexes=missing_celexes,
        coverage_pct=coverage,
        meta=meta,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helpers per segmenti (usati dal modulo 04 e dall'endpoint /act/{celex})
# ──────────────────────────────────────────────────────────────────────────────

def parse_segments(segments_json: str | None) -> list[dict]:
    """
    Deserializza la colonna 'segments' da JSON string a lista di dict.

    Restituisce lista vuota se il valore è None o non valido.
    Ogni segmento ha: segment_id, tipo, identificatore, testo.
    """
    if not segments_json or pd.isna(segments_json):
        return []
    try:
        return json.loads(segments_json)
    except (json.JSONDecodeError, TypeError):
        return []


def get_segments_for_celex(
    celex: str,
    text_cache: TextCache,
) -> list[dict]:
    """
    Restituisce i segmenti strutturati per un singolo atto.

    Usato dall'endpoint GET /act/{celex} per costruire la vista
    heatmap nel frontend.

    Restituisce lista vuota se il CELEX non è in cache.
    """
    if celex not in text_cache.lookup.index:
        return []
    row = text_cache.lookup.loc[celex]
    return parse_segments(row.get('segments'))


def get_articles_for_celex(
    celex: str,
    text_cache: TextCache,
) -> list[dict]:
    """
    Restituisce solo i segmenti di tipo 'articolo' per un atto.

    Filtro conveniente per il modulo 04 che opera articolo per articolo
    per produrre la distribuzione percentuale sui layer.
    """
    segments = get_segments_for_celex(celex, text_cache)
    return [s for s in segments if s.get('tipo') == 'articolo']
