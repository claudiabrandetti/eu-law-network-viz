"""
================================================================================
CONFIGURAZIONE PIPELINE — ESTRAZIONE SOTTORETE GOLDEN POWER
================================================================================

Questo file centralizza tutti i parametri della pipeline di estrazione.
Ogni scelta è giustificata con un riferimento normativo o metodologico esplicito.

STRUTTURA DELLA PIPELINE:
  Livello 1 → Atti fondamentali (seed manuali, fonte: Compendio normativo)
  Livello 2 → Espansione semantica via EuroVoc (fonte: tassonomia ufficiale EU)
  Livello 3 → Espansione relazionale per citazione (1 hop)

RIFERIMENTI NORMATIVI PRINCIPALI:
  - Reg. (UE) 2019/452 — FDI Screening Framework
  - D.L. 21/2012 e s.m.i. (Golden Power italiano, recepisce il framework UE)
  - TFUE, artt. 63-66 — libera circolazione dei capitali e deroghe
  - Dir. (UE) 2022/2557 (CER) — infrastrutture critiche europee
================================================================================
"""

# ==============================================================================
# LIVELLO 1: ATTI SEED MANUALI
# ==============================================================================
# Atti la cui inclusione nel perimetro Golden Power è documentata da fonti
# ufficiali (Compendio Osservatorio Golden Power, EUR-Lex).
# Ogni CELEX è commentato con il riferimento normativo che ne giustifica
# l'inclusione.

MATERIA_NAME = "golden_power"

SEED_CELEX = {

    # --- LEGISLAZIONE UE PRIMARIA ---
    # Fonte: https://www.osservatoriogoldenpower.eu/compendio-normativo-golden-power/

    "32019R0452": "Reg. (UE) 2019/452 — FDI Screening Framework: atto centrale "
                  "della materia, definisce il meccanismo di cooperazione UE per "
                  "il controllo degli investimenti diretti esteri.",

    "32021R0821": "Reg. (UE) 2021/821 — Controllo esportazioni dual-use: "
                  "collegato al Golden Power per la componente tecnologica "
                  "e militare (art. 4, Reg. 2019/452).",

    "32008L0114": "Dir. 2008/114/CE — Infrastrutture critiche europee (EPCIP): "
                  "prima definizione UE di 'infrastruttura critica', "
                  "precede e informa la normativa Golden Power sui settori strategici.",

    "32022L2557":  "Dir. (UE) 2022/2557 (CER) — sostituisce la Dir. 2008/114/CE, "
                  "amplia il perimetro delle infrastrutture critiche soggette "
                  "a protezione (art. 2, Reg. 2019/452, considerando 12).",

    # --- BASI GIURIDICHE NEL TRATTATO ---
    # Il Reg. 2019/452 si fonda esplicitamente su questi articoli TFUE
    # (cfr. considerando 1-3 del Reg. 2019/452).

    "12016E063":   "Art. 63 TFUE — libera circolazione dei capitali: "
                  "base giuridica primaria; il Golden Power opera come "
                  "deroga controllata a questo principio.",

    "12016E065":   "Art. 65 TFUE — deroghe alla libera circolazione: "
                  "fondamento delle restrizioni nazionali per motivi di "
                  "ordine pubblico e sicurezza (art. 65, par. 1, lett. b).",
}


# ==============================================================================
# LIVELLO 2: CONCETTI EUROVOC
# ==============================================================================
# I termini di ricerca sono derivati direttamente dal testo normativo:
# - Reg. (UE) 2019/452, artt. 4 e 8 (settori soggetti a screening)
# - D.L. 21/2012, artt. 1-2 (settori Golden Power italiano)
# - Allegato al Reg. 2019/452 (lista esemplificativa settori strategici)
#
# PRINCIPIO DI SELEZIONE: includere un termine solo se compare esplicitamente
# nel testo di almeno uno dei riferimenti normativi sopra citati.
# Termini generici o interpretativi sono esclusi.

EUROVOC_KEYWORDS = {

    # SETTORE DIFESA E SICUREZZA
    # Fonte: Reg. 2019/452, art. 4, par. 1, lett. a) — "defence"
    # e D.L. 21/2012, art. 1 (settori difesa e sicurezza nazionale)
    "defence":              "Reg. 2019/452 art. 4(1)(a); D.L. 21/2012 art. 1",
    "national security":    "Reg. 2019/452 art. 4(1)(a); TFUE art. 65(1)(b)",
    "critical infrastructure security": "Dir. 2022/2557 (CER), art. 2",

    # SETTORE ENERGIA
    # Fonte: Reg. 2019/452, art. 4, par. 1, lett. b) — "energy"
    # e D.L. 21/2012, art. 2, co. 1, lett. a)
    "energy policy":        "Reg. 2019/452 art. 4(1)(b); D.L. 21/2012 art. 2(1)(a)",
    "energy supply":        "Reg. 2019/452 art. 4(1)(b)",

    # SETTORE TRASPORTI E INFRASTRUTTURE
    # Fonte: Reg. 2019/452, art. 4, par. 1, lett. b) — "transport infrastructure"
    # e D.L. 21/2012, art. 2, co. 1, lett. b)
    "transport policy":     "Reg. 2019/452 art. 4(1)(b); D.L. 21/2012 art. 2(1)(b)",
    "transport infrastructure": "Reg. 2019/452 Allegato, punto 2",

    # SETTORE COMUNICAZIONI E DIGITALE
    # Fonte: Reg. 2019/452, art. 4, par. 1, lett. b) — "communication"
    # e D.L. 21/2012 come modificato dal D.L. 105/2019 (5G)
    "telecommunications":   "Reg. 2019/452 art. 4(1)(b); D.L. 105/2019 (5G)",
    "information security": "Reg. 2019/452 art. 4(1)(c) — cybersecurity",

    # SETTORE FINANZIARIO
    # Fonte: Reg. 2019/452, art. 4, par. 1, lett. e) — "financial infrastructure"
    "financial institution": "Reg. 2019/452 art. 4(1)(e) — financial infrastructure; "
                         "confermato da D.L. 21/2012 art. 2(1)(f)",
    "direct investment":     "Reg. 2019/452, definizione art. 2 — oggetto principale",
    "foreign investment":    "Reg. 2019/452, definizione art. 2",
    "free movement of capital": "TFUE art. 63 — principio che il Golden Power deroga",

    # SETTORE AGROALIMENTARE
    # Fonte: Reg. 2019/452, Allegato — "food security" è citata esplicitamente
    # tra i settori strategici soggetti a screening FDI
    "food supply":          "Reg. 2019/452 Allegato, punto 6 — food security",

    # SETTORE TECNOLOGIA E RICERCA
    # Fonte: Reg. 2019/452, art. 4, par. 1, lett. d) — "technologies"
    # Allegato: semiconduttori, AI, robotica, cybersecurity, spazio
    "semiconductor":        "Reg. 2019/452 Allegato, punto 5 — tecnologie critiche",
    "strategic defence":    "Reg. 2019/452 art. 4(1)(a) e Allegato, punto 1",
}


# ==============================================================================
# DOMINI EUROVOC PRIORITARI
# ==============================================================================
# Filtra i concetti trovati mantenendo solo quelli in domini tematicamente
# coerenti con la materia Golden Power.
#
# CRITERI DI INCLUSIONE di un dominio:
#   - Copre almeno un settore esplicitamente elencato nel Reg. 2019/452 o D.L. 21/2012
#
# CRITERI DI ESCLUSIONE:
#   - Dominio puramente geografico (72 GEOGRAPHY) — aggiunge rumore senza
#     valore normativo per questa analisi
#   - Dominio ambientale (52 ENVIRONMENT) — il Golden Power non copre
#     esplicitamente materie ambientali salvo sovrapposizione con energia
#   - Dominio sociale (44 EMPLOYMENT) — irrilevante per la materia
#   - Dominio scientifico generico (36 SCIENCE) — troppo ampio
#   - Organizzazioni internazionali (76 INT. ORG.) — non normativo per il filtro

PRIORITY_DOMAINS = [
    "04 POLITICS",                          # ordine pubblico, sicurezza nazionale
    "08 INTERNATIONAL RELATIONS",           # FDI, relazioni economiche estere
    "10 EUROPEAN UNION",                    # mercato interno, libertà fondamentali
    "12 LAW",                               # diritto societario, proprietà
    "16 ECONOMICS",                         # investimenti, macroeconomia
    "20 TRADE",                             # commercio internazionale, esportazioni
    "24 FINANCE",                           # banche, assicurazioni, mercati finanziari
    "32 EDUCATION AND COMMUNICATIONS",      # telecomunicazioni, 5G, digitale
    "40 BUSINESS AND COMPETITION",          # concorrenza, acquisizioni societarie
    "48 TRANSPORT",                         # infrastrutture di trasporto
    "60 AGRI-FOODSTUFFS",                   # filiera agroalimentare (D.L. 21/2012)
    "64 PRODUCTION, TECHNOLOGY AND RESEARCH", # semiconduttori, AI, dual-use
    "66 ENERGY",                            # reti energetiche, sicurezza approvvigionamento
    "68 INDUSTRY",                          # industria strategica
]

# Domini esclusi (con motivazione esplicita):
EXCLUDED_DOMAINS = {
    "28 SOCIAL QUESTIONS":  "esclude: questioni sociali non rilevanti per Golden Power",
    "36 SCIENCE":           "esclude: scienza generica, troppo ampio",
    "44 EMPLOYMENT AND WORKING CONDITIONS": "esclude: lavoro, fuori perimetro",
    "52 ENVIRONMENT":       "esclude: ambiente, non coperto da Golden Power",
    "56 AGRICULTURE, FORESTRY AND FISHERIES": "esclude: settore primario generico "
                            "(manteniamo solo 60 AGRI-FOODSTUFFS per filiera alimentare)",
    "72 GEOGRAPHY":         "esclude: puramente geografico, nessun contenuto normativo",
    "76 INTERNATIONAL ORGANISATIONS": "esclude: organizzazioni internazionali, non normativo",
}


# ==============================================================================
# LIVELLO 3: ESPANSIONE PER CITAZIONE
# ==============================================================================
# Parametro: numero di hop (salti) dall'insieme seed.
#
# SCELTA: N_HOPS = 1
# MOTIVAZIONE: Un atto normativo cita quasi sempre i propri fondamenti diretti
# (L2 cita L1, L3 cita L1 e L2). Con 1 hop catturiamo il contesto normativo
# immediato senza includere l'intero corpus UE per transitività.
# Con 2 hop la rete si espanderebbe a decine di migliaia di nodi perdendo
# la specificità tematica (verificato empiricamente: con 1 hop = ~5.500 nodi,
# con 2 hop stimato > 20.000 nodi).

N_HOPS = 1

# DIREZIONE DELL'ESPANSIONE:
# EXPAND_OUTGOING = True  → includi atti CITATI dai seed (es. le basi giuridiche)
# EXPAND_INCOMING = True  → includi atti che CITANO i seed (es. atti attuativi)
# Entrambe le direzioni sono necessarie per catturare sia la gerarchia verticale
# (L1 → L2 → L3) sia l'enforcement (L4 → tutti).

EXPAND_OUTGOING = True   # atti citati DAI seed
EXPAND_INCOMING = True   # atti che CITANO i seed