"""
================================================================================
02_extract_subgraph_backend.py
================================================================================

Modulo backend per l'estrazione della sottorete tematica.
Contiene la stessa logica di 02_extract_subgraph.ipynb in forma di funzioni
importabili dal backend FastAPI.

UTILIZZO:
    from notebooks.02_extract_subgraph_backend import (
        load_corpus,
        extract_by_theme,
        extract_by_celex,
        extract_subgraph,
    )

    corpus = load_corpus(proc_path, raw_path)

    # Modalità theme — embedding semantico
    result = extract_subgraph(corpus, theme="foreign direct investment screening")

    # Modalità celex — concetti dai CELEX noti
    result = extract_subgraph(corpus, celex=["32019R0452", "32022L2557"])

RELAZIONE CON IL NOTEBOOK:
    02_extract_subgraph.ipynb  →  sviluppo, esplorazione, debug, tesi
    questo file                →  produzione, importato dal backend FastAPI

Le due implementazioni devono rimanere allineate. Ogni modifica alla logica
va applicata in entrambi i posti.

DIPENDENZE:
    pip install sentence-transformers scikit-learn pandas numpy
================================================================================
"""

from __future__ import annotations

import re
import os
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# Strutture dati
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Corpus:
    """
    Dati di corpus caricati da disco. Passato a tutte le funzioni di estrazione.
    Gli embeddings EuroVoc vengono caricati/calcolati una volta sola all'avvio
    del server e riutilizzati per tutte le query successive.
    """
    nodes:              pd.DataFrame    # nodes_light.csv — colonne: id, celex, ...
    edges:              pd.DataFrame    # edges_enriched.csv
    has_concept:        pd.DataFrame    # has_concept_enriched.csv
    eurovoc:            pd.DataFrame    # eurovoc_concept.csv
    eurovoc_embeddings: Optional[np.ndarray] = None  # shape (n_concepts, 768)
    sentence_model:     Optional[object] = None       # SentenceTransformer in memoria
    proc_path:          str = ""        # path a data/processed/ — per la cache


@dataclass
class ExtractionResult:
    """Risultato di una estrazione. Restituito a FastAPI."""
    focal_nodes: pd.DataFrame
    focal_edges: pd.DataFrame
    meta: dict = field(default_factory=dict)
    # meta keys comuni:
    #   mode, materia_name, min_seed_concepts,
    #   n_concepts, n_nodes_l1, n_nodes_l2, n_nodes_total, n_edges,
    #   concepts_sample (lista dei primi 10 nomi EuroVoc usati)
    # meta keys aggiuntivi per mode='theme':
    #   query, top_k, min_similarity


# ──────────────────────────────────────────────────────────────────────────────
# Caricamento corpus ed embeddings
# ──────────────────────────────────────────────────────────────────────────────

def load_corpus(proc_path: str, raw_path: str) -> Corpus:
    """
    Carica i file di corpus e gli embeddings EuroVoc (con cache su disco).

    Gli embeddings vengono calcolati con all-mpnet-base-v2 alla prima chiamata
    (~1-2 minuti) e salvati in data/processed/eurovoc_embeddings.npy.
    Ogni chiamata successiva li carica in ~1 secondo.

    Parametri
    ---------
    proc_path : str
        Percorso a data/processed/ (output di 01_data_cleaning.ipynb)
    raw_path : str
        Percorso a data/raw/ (file originali EUR-Lex)
    """
    nodes       = pd.read_csv(os.path.join(proc_path, 'nodes_light.csv'))
    edges       = pd.read_csv(os.path.join(proc_path, 'edges_enriched.csv'))
    has_concept = pd.read_csv(os.path.join(proc_path, 'has_concept_enriched.csv'))
    eurovoc     = pd.read_csv(os.path.join(raw_path,  'eurovoc_concept.csv'))

    embeddings, model = _load_or_compute_embeddings(eurovoc, proc_path)

    return Corpus(
        nodes=nodes,
        edges=edges,
        has_concept=has_concept,
        eurovoc=eurovoc,
        eurovoc_embeddings=embeddings,
        sentence_model=model,
        proc_path=proc_path,
    )


def _load_or_compute_embeddings(
    eurovoc: pd.DataFrame,
    proc_path: str,
) -> tuple[np.ndarray, object]:
    """
    Carica gli embeddings EuroVoc dalla cache (o li calcola se non esistono)
    e restituisce anche il modello caricato in memoria.

    Restituisce (embeddings, model) — entrambi vengono tenuti nel Corpus
    così non servono ricalcoli né ricaricamenti per query successive.

    Cache: data/processed/eurovoc_embeddings.npy
    I nomi EuroVoc sono fissi — la cache è sempre valida finché
    eurovoc_concept.csv non viene aggiornato con una nuova versione del tesauro.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "Il pacchetto 'sentence-transformers' non è installato. "
            "Esegui: pip install sentence-transformers"
        )

    model      = SentenceTransformer('all-mpnet-base-v2')
    cache_path = os.path.join(proc_path, 'eurovoc_embeddings.npy')

    if os.path.exists(cache_path):
        embeddings = np.load(cache_path)
        return embeddings, model

    # Prima esecuzione: calcola e salva
    print("Calcolo embeddings EuroVoc (prima esecuzione, ~1-2 min)...")
    names      = eurovoc['name'].fillna('').tolist()
    embeddings = model.encode(names, show_progress_bar=True, batch_size=256)
    np.save(cache_path, embeddings)
    print(f"Embeddings salvati in {cache_path}")

    return embeddings, model


# ──────────────────────────────────────────────────────────────────────────────
# Funzioni interne condivise
# ──────────────────────────────────────────────────────────────────────────────

def _acts_from_concepts(
    seed_concepts_filtered: pd.DataFrame,
    corpus: Corpus,
    min_seed_concepts: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Data una lista di concetti EuroVoc, recupera gli atti collegati.

    Parametri
    ---------
    min_seed_concepts : int
        Numero minimo di concetti seed che un atto deve avere per essere incluso.
        1 = qualsiasi atto con almeno 1 concetto seed (sottorete ampia).
        2+ = solo atti con affinità tematica forte (sottorete stringente).

    Restituisce (seed_works_by_concept, has_concept_seed).
    """
    seed_concept_ids = set(seed_concepts_filtered['id:ID'])
    has_concept_seed = corpus.has_concept[
        corpus.has_concept[':END_ID'].isin(seed_concept_ids)
    ]

    if min_seed_concepts > 1:
        concept_count = has_concept_seed.groupby(':START_ID').size()
        seed_work_ids = set(concept_count[concept_count >= min_seed_concepts].index)
    else:
        seed_work_ids = set(has_concept_seed[':START_ID'])

    seed_works_by_concept = corpus.nodes[corpus.nodes['id'].isin(seed_work_ids)].copy()

    return seed_works_by_concept, has_concept_seed


def _build_focal_graph(
    seed_nodes_known: pd.DataFrame,
    seed_works_by_concept: pd.DataFrame,
    corpus: Corpus,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Unisce L1 e L2, assegna pipeline_level, estrae archi interni.

    Restituisce (focal_nodes, focal_edges).
    """
    all_seed_works = pd.concat([
        seed_nodes_known,
        seed_works_by_concept,
    ]).drop_duplicates(subset=['id'])

    seed_l1_ids = set(seed_nodes_known['id'])

    focal_nodes = all_seed_works.copy()
    focal_nodes['pipeline_level'] = focal_nodes['id'].apply(
        lambda x: 'L1_seed_manual' if x in seed_l1_ids else 'L2_seed_eurovoc'
    )

    focal_ids     = set(focal_nodes['id'])
    focal_celexes = set(focal_nodes['celex'].dropna())
    celex_to_id   = focal_nodes.set_index('celex')['id'].to_dict()

    def strip_corrigendum(val):
        if pd.isna(val):
            return val
        return re.sub(r'R\(\d+\)$', '', str(val))

    focal_edges = corpus.edges[
        (corpus.edges[':START_ID'].isin(focal_ids) | corpus.edges[':START_ID'].isin(focal_celexes)) &
        (corpus.edges[':END_ID'].isin(focal_ids)   | corpus.edges[':END_ID'].isin(focal_celexes))
    ].copy()

    focal_edges[':START_ID'] = focal_edges[':START_ID'].apply(lambda x: celex_to_id.get(x, x))
    focal_edges[':END_ID']   = focal_edges[':END_ID'].apply(lambda x: celex_to_id.get(x, x))
    focal_edges[':START_ID'] = focal_edges[':START_ID'].apply(strip_corrigendum)
    focal_edges[':END_ID']   = focal_edges[':END_ID'].apply(strip_corrigendum)

    return focal_nodes, focal_edges


# ──────────────────────────────────────────────────────────────────────────────
# API pubblica
# ──────────────────────────────────────────────────────────────────────────────

def extract_by_theme(
    query: str,
    corpus: Corpus,
    materia_name: str = "custom_theme",
    top_k: int = 20,
    min_similarity: float = 0.25,
    min_seed_concepts: int = 1,
) -> ExtractionResult:
    """
    Estrae la sottorete tramite embedding semantico della query.

    La query viene confrontata con tutti i 7.613 nomi EuroVoc nello spazio
    vettoriale di all-mpnet-base-v2. I top_k concetti con similarità coseno
    più alta (sopra min_similarity) definiscono il perimetro tematico.

    Funziona per qualsiasi query in inglese, inclusi termini tecnici che non
    compaiono letteralmente nel tesauro EuroVoc (es. "FDI screening",
    "Lamfalussy framework", "golden share").

    Parametri
    ---------
    query : str
        Descrizione della materia in inglese. Più è specifica e tecnica,
        migliore è la selezione EuroVoc.
        Es: "foreign direct investment screening",
            "data protection personal data privacy",
            "public procurement contracts".
    corpus : Corpus
        Dati di corpus caricati con load_corpus(). Gli embeddings EuroVoc
        devono essere già calcolati (vengono caricati automaticamente da
        load_corpus).
    materia_name : str
        Nome usato per metadati e cartelle output.
    top_k : int
        Numero massimo di concetti EuroVoc da includere (default 20).
        10-25 per materie specifiche, 25-40 per materie ampie.
    min_similarity : float
        Soglia minima di similarità coseno (0-1, default 0.25).
        Aumentare per una selezione più stringente.
    min_seed_concepts : int
        Numero minimo di concetti seed per includere un atto in L2 (default 1).
        Alzare a 2 per una sottorete più coesa.
    """
    if corpus.eurovoc_embeddings is None or corpus.sentence_model is None:
        raise ValueError(
            "Embeddings o modello non disponibili nel Corpus. "
            "Carica il corpus con load_corpus() — li calcola automaticamente."
        )

    try:
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        raise ImportError("Esegui: pip install scikit-learn")

    # Embedding query — usa il modello già in memoria, nessun ricaricamento
    query_emb = corpus.sentence_model.encode([query], show_progress_bar=False)
    sims      = cosine_similarity(query_emb, corpus.eurovoc_embeddings)[0]

    eurovoc_scored = corpus.eurovoc.copy()
    eurovoc_scored['similarity'] = sims

    # Filtra per soglia e prende top-k
    above = eurovoc_scored[eurovoc_scored['similarity'] >= min_similarity]
    seed_concepts_filtered = above.nlargest(top_k, 'similarity').copy()

    if seed_concepts_filtered.empty:
        raise ValueError(
            f"Nessun concetto EuroVoc trovato per '{query}' "
            f"con similarità >= {min_similarity}. "
            "Prova ad abbassare min_similarity o usa una query più specifica in inglese."
        )

    # Recupero atti e costruzione grafo
    seed_works_by_concept, has_concept_seed = _acts_from_concepts(
        seed_concepts_filtered, corpus, min_seed_concepts
    )
    empty_l1 = corpus.nodes.iloc[0:0].copy()
    focal_nodes, focal_edges = _build_focal_graph(
        empty_l1, seed_works_by_concept, corpus
    )

    # Similarity media dei concetti seed per nodo (utile per ranking UI)
    concept_sim  = seed_concepts_filtered.set_index('id:ID')['similarity'].to_dict()
    concept_count = has_concept_seed.groupby(':START_ID').size()

    def avg_sim(node_id):
        cids = has_concept_seed[has_concept_seed[':START_ID'] == node_id][':END_ID'].tolist()
        vals = [concept_sim[c] for c in cids if c in concept_sim]
        return round(float(np.mean(vals)), 4) if vals else 0.0

    focal_nodes['avg_concept_similarity'] = focal_nodes['id'].apply(avg_sim)
    focal_nodes['seed_concept_count']     = focal_nodes['id'].apply(
        lambda x: int(concept_count.get(x, 0))
    )

    meta = {
        'mode':               'theme',
        'query':              query,
        'materia_name':       materia_name,
        'top_k':              top_k,
        'min_similarity':     min_similarity,
        'min_seed_concepts':  min_seed_concepts,
        'n_concepts':         len(seed_concepts_filtered),
        'similarity_range':   [
            round(float(seed_concepts_filtered['similarity'].min()), 3),
            round(float(seed_concepts_filtered['similarity'].max()), 3),
        ],
        'n_nodes_l1':         0,
        'n_nodes_l2':         len(seed_works_by_concept),
        'n_nodes_total':      len(focal_nodes),
        'n_edges':            len(focal_edges),
        'concepts_sample':    seed_concepts_filtered.nlargest(10, 'similarity')[['name', 'similarity']].values.tolist(),
    }

    return ExtractionResult(
        focal_nodes=focal_nodes,
        focal_edges=focal_edges,
        meta=meta,
    )


def extract_by_celex(
    celex_list: list[str],
    corpus: Corpus,
    materia_name: str = "custom_celex",
    min_seed_concepts: int = 1,
) -> ExtractionResult:
    """
    Estrae la sottorete a partire da uno o più codici CELEX noti.

    I concetti EuroVoc già associati agli atti seed nel corpus vengono usati
    come perimetro tematico per L2. Non richiede embeddings né configurazione
    manuale — usa direttamente la classificazione ufficiale EUR-Lex.

    Parametri
    ---------
    celex_list : list[str]
        Uno o più codici CELEX (es. ["32019R0452", "32022L2557"]).
    corpus : Corpus
        Dati di corpus caricati con load_corpus().
    materia_name : str
        Nome usato per metadati e cartelle output.
    min_seed_concepts : int
        Numero minimo di concetti seed per includere un atto in L2 (default 1).
    """
    seed_nodes_known = corpus.nodes[corpus.nodes['celex'].isin(celex_list)].copy()

    found   = set(seed_nodes_known['celex'])
    missing = [c for c in celex_list if c not in found]

    if seed_nodes_known.empty:
        raise ValueError(
            f"Nessuno dei CELEX forniti trovato nel corpus: {celex_list}. "
            "Verifica i codici e che il corpus sia aggiornato."
        )

    seed_node_ids          = set(seed_nodes_known['id'])
    concept_ids_from_seeds = set(
        corpus.has_concept[corpus.has_concept[':START_ID'].isin(seed_node_ids)][':END_ID']
    )
    seed_concepts_filtered = corpus.eurovoc[
        corpus.eurovoc['id:ID'].isin(concept_ids_from_seeds)
    ].copy()

    seed_works_by_concept, has_concept_seed = _acts_from_concepts(
        seed_concepts_filtered, corpus, min_seed_concepts
    )
    focal_nodes, focal_edges = _build_focal_graph(
        seed_nodes_known, seed_works_by_concept, corpus
    )

    concept_count = has_concept_seed.groupby(':START_ID').size()
    focal_nodes['seed_concept_count'] = focal_nodes['id'].apply(
        lambda x: int(concept_count.get(x, 0))
    )

    meta = {
        'mode':               'celex',
        'celex_input':        celex_list,
        'celex_found':        list(found),
        'celex_missing':      missing,
        'materia_name':       materia_name,
        'min_seed_concepts':  min_seed_concepts,
        'n_concepts':         len(seed_concepts_filtered),
        'n_nodes_l1':         len(seed_nodes_known),
        'n_nodes_l2':         len(seed_works_by_concept),
        'n_nodes_total':      len(focal_nodes),
        'n_edges':            len(focal_edges),
        'concepts_sample':    seed_concepts_filtered['name'].head(10).tolist(),
    }

    return ExtractionResult(
        focal_nodes=focal_nodes,
        focal_edges=focal_edges,
        meta=meta,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher — entry point per FastAPI
# ──────────────────────────────────────────────────────────────────────────────

def extract_subgraph(
    corpus: Corpus,
    *,
    theme: Optional[str] = None,
    celex: Optional[list[str]] = None,
    **kwargs,
) -> ExtractionResult:
    """
    Entry point unico per FastAPI. Esattamente uno tra theme e celex
    deve essere non-None. Tutti gli altri parametri vengono passati via
    **kwargs alla funzione specializzata.

    Esempi
    ------
    # Dalla UI — utente scrive la materia in inglese
    result = extract_subgraph(corpus, theme="foreign direct investment screening")
    result = extract_subgraph(corpus, theme="data protection privacy", top_k=25)

    # Dalla UI — utente fornisce CELEX noti
    result = extract_subgraph(corpus, celex=["32019R0452", "32022L2557"])

    # Con soglia stringente
    result = extract_subgraph(
        corpus,
        theme="public procurement",
        min_similarity=0.35,
        min_seed_concepts=2,
    )
    """
    provided = sum([theme is not None, celex is not None])
    if provided != 1:
        raise ValueError(
            "Esattamente uno tra 'theme' e 'celex' deve essere fornito. "
            f"Ricevuti: theme={theme!r}, celex={celex!r}"
        )

    if theme is not None:
        return extract_by_theme(theme, corpus, **kwargs)
    if celex is not None:
        return extract_by_celex(celex, corpus, **kwargs)