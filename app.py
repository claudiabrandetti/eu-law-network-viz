"""
app.py — Visualizzazione Reti Normative UE: Golden Power / FDI Screening
=========================================================================
Avvio:  python app.py  →  http://localhost:8050

Dipendenze:
    pip install dash dash-cytoscape plotly pandas numpy scikit-learn
"""

import os
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

import dash
from dash import Input, Output, State, dcc, html, ctx
import dash_cytoscape as cyto
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────────────────────
# 1. DATI
# ─────────────────────────────────────────────────────────────────────────────

NODES_FILE = os.path.join("data","output","golden_power","nodes_focal_layers.csv")
EDGES_FILE = os.path.join("data","output","golden_power","edges_focal.csv")
if not os.path.exists(NODES_FILE):
    NODES_FILE = os.path.join("data","output","golden_power","gephi_nodes_exported.csv")

nodes = pd.read_csv(NODES_FILE, low_memory=False)
edges = pd.read_csv(EDGES_FILE, low_memory=False)
nodes.columns = [c.strip() for c in nodes.columns]
edges.columns = [c.strip() for c in edges.columns]

def col(df, opts, default=None):
    for o in opts:
        if o in df.columns: return o
    return default

C_ID    = col(nodes, ["Id","celex_id","id"])
C_TITLE = col(nodes, ["title","work_title","Title"])
C_TEXT  = col(nodes, ["preamble","full_text_excerpt","text"])
C_LAYER = col(nodes, ["layer","Layer"])
C_CONF  = col(nodes, ["layer_confidence","purity","confidence"])
C_ENT   = col(nodes, ["layer_entropy","entropy"])
C_YEAR  = col(nodes, ["year","Year"])
C_TYPE  = col(nodes, ["legaltype","LegalType","legal_type"])
C_MOTIV = col(nodes, ["motivation","author"])
C_IND   = col(nodes, ["indegree","in_degree"])
C_OUT   = col(nodes, ["outdegree","out_degree"])
C_BW    = col(nodes, ["betweenesscentrality","betweenness"])
C_ERA   = col(nodes, ["era","Era"])

# Membership columns
MEM_COLS = sorted([c for c in nodes.columns if c.startswith("membership_L")],
                  key=lambda c: int(c.replace("membership_L","")))
if not MEM_COLS:
    MEM_COLS = [c for c in ["g1","g2","g3","g4","g5"] if c in nodes.columns]
LAYERS = ([c.replace("membership_","") for c in MEM_COLS]
          if MEM_COLS and MEM_COLS[0].startswith("membership_")
          else sorted(nodes[C_LAYER].dropna().unique()) if C_LAYER else [])

# Scala membership a 0-1 se era 0-100
for mc in MEM_COLS:
    if nodes[mc].max() > 1.5:
        nodes[mc] = nodes[mc] / 100.0

# Flag ibrido
if "is_hybrid" not in nodes.columns:
    nodes["is_hybrid"] = (nodes[C_CONF] < 0.70).astype(int) if C_CONF else 0

# Coordinate scatter
HAS_UMAP = "umap_x" in nodes.columns
if not HAS_UMAP:
    Xm  = nodes[MEM_COLS].fillna(0).values.astype(float)
    bw  = MinMaxScaler().fit_transform(np.log1p(nodes[C_BW].fillna(0).values.reshape(-1,1))).ravel() if C_BW else np.zeros(len(nodes))
    ind = MinMaxScaler().fit_transform(np.log1p(nodes[C_IND].fillna(0).values.reshape(-1,1))).ravel() if C_IND else np.zeros(len(nodes))
    yr  = MinMaxScaler().fit_transform(nodes[C_YEAR].fillna(2010).values.reshape(-1,1)).ravel() if C_YEAR else np.zeros(len(nodes))
    coords = PCA(n_components=2, random_state=42).fit_transform(np.column_stack([Xm, bw*0.5, ind*0.3, yr*0.2]))
    nodes["pca_x"], nodes["pca_y"] = coords[:,0].round(4), coords[:,1].round(4)
    SX, SY = "pca_x", "pca_y"
    SLABEL = "Proiezione PCA — vicinanza funzionale tra atti"
else:
    SX, SY, SLABEL = "umap_x", "umap_y", "Proiezione UMAP — spazio funzionale/strutturale"

E_SRC  = col(edges, ["Source","source"])
E_TGT  = col(edges, ["Target","target"])
E_TYPE = col(edges, ["Type","type","edge_type"])

NODE_MAP = nodes.set_index(C_ID).to_dict("index") if C_ID else {}

# ─────────────────────────────────────────────────────────────────────────────
# 2. PALETTE
# ─────────────────────────────────────────────────────────────────────────────

_PAL  = ["#34d399","#60a5fa","#fbbf24","#e879f9","#f87171","#38bdf8","#a3e635","#fb923c"]
LC    = {l: _PAL[i % len(_PAL)] for i, l in enumerate(LAYERS)}
LC["noise"] = "#475569"
DARK, PANEL, BORDER = "#0b0f1a", "#0f1520", "#1a2035"
FONT = "'Fira Code', 'Courier New', monospace"

PLOTLY_BASE = dict(paper_bgcolor=DARK, plot_bgcolor=DARK,
                   font=dict(family=FONT, color="#94a3b8", size=11),
                   xaxis=dict(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER),
                   yaxis=dict(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER),
                   margin=dict(l=50,r=30,t=45,b=50))

def empty_fig(h=300): 
    f = go.Figure()
    f.update_layout(**PLOTLY_BASE, height=h)
    return f

CYTO_STYLE = [
    {"selector":"node","style":{"background-color":"data(color)","border-color":"data(bc)",
     "border-width":"data(bw)","border-style":"data(bs)",
     "width":"data(sz)","height":"data(sz)","opacity":0.9,
     "label":"data(label)","color":"#94a3b8","font-size":"7px",
     "text-valign":"bottom","text-margin-y":"3px","font-family":FONT}},
    {"selector":"node:selected","style":{"border-color":"#fff","border-width":3,"opacity":1}},
    {"selector":"edge","style":{"line-color":"#1e2a45","width":1,"opacity":0.4,"curve-style":"bezier"}},
    {"selector":"node[layer = 'center']","style":{"border-color":"#ffffff","border-width":3}},
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. FIGURE BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def fig_sankey():
    if not (E_SRC and E_TGT and C_LAYER and C_ID):
        return empty_fig(340)
    lmap = dict(zip(nodes[C_ID], nodes[C_LAYER]))
    e = edges.copy()
    e["sl"] = e[E_SRC].map(lmap)
    e["tl"] = e[E_TGT].map(lmap)
    e = e.dropna(subset=["sl","tl"])
    e = e[(e["sl"]!="noise")&(e["tl"]!="noise")&(e["sl"]!=e["tl"])]
    flows = e.groupby(["sl","tl"]).size().reset_index(name="n")
    if flows.empty: return empty_fig(340)
    all_l = sorted(set(flows["sl"])|set(flows["tl"]),
                   key=lambda x: LAYERS.index(x) if x in LAYERS else 99)
    idx = {l:i for i,l in enumerate(all_l)}
    def rgba(hx, a=0.35):
        r,g,b=int(hx[1:3],16),int(hx[3:5],16),int(hx[5:7],16)
        return f"rgba({r},{g},{b},{a})"
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=all_l, color=[LC.get(l,"#888") for l in all_l],
                  pad=18, thickness=16, line=dict(color=DARK,width=0.5)),
        link=dict(
            source=[idx[r.sl] for _,r in flows.iterrows()],
            target=[idx[r.tl] for _,r in flows.iterrows()],
            value=flows["n"].tolist(),
            color=[rgba(LC.get(r.sl,"#888")) for _,r in flows.iterrows()],
        ),
    ))
    fig.update_layout(**{**PLOTLY_BASE, "margin": dict(l=20,r=20,t=50,b=20)},
                      height=340,
                      title_text="Flusso citazioni tra livelli normativi",
                      title_font=dict(size=12,color="#64748b"))
    return fig

def fig_purity_box():
    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE, height=280,
                      title_text="Purezza per layer",
                      title_font=dict(size=12,color="#64748b"),
                      yaxis_title="Purezza", showlegend=False)
    for l in LAYERS+["noise"]:
        sub = nodes[nodes[C_LAYER]==l][C_CONF].dropna() if C_CONF and C_LAYER else pd.Series(dtype=float)
        if sub.empty: continue
        hx = LC.get(l,"#888")
        fig.add_trace(go.Box(y=sub, name=l, marker_color=hx,
                             fillcolor=hex_rgba(hx,0.19), line_width=1.5, boxmean="sd"))
    fig.add_hline(y=0.70, line_dash="dot", line_color="#f87171", line_width=1,
                  annotation_text="soglia 0.70", annotation_font=dict(color="#f87171",size=9))
    return fig

def fig_entropy_hist():
    fig = go.Figure()
    fig.update_layout(**PLOTLY_BASE, height=260, barmode="overlay",
                      title_text="Distribuzione entropia H(layer)",
                      title_font=dict(size=12,color="#64748b"),
                      xaxis_title="Entropia", yaxis_title="%",
                      legend=dict(x=0.65,y=0.95,font=dict(size=9)))
    if not C_ENT: return fig
    healthy = nodes[nodes["is_hybrid"]==0][C_ENT].dropna()
    pathol  = nodes[nodes["is_hybrid"]==1][C_ENT].dropna()
    fig.add_trace(go.Histogram(x=healthy, name="Sani", marker_color="#34d399",
                               opacity=0.65, nbinsx=40, histnorm="percent"))
    if not pathol.empty:
        fig.add_trace(go.Histogram(x=pathol, name="Ibridi (<0.70)", marker_color="#f87171",
                                   opacity=0.65, nbinsx=40, histnorm="percent"))
    return fig

def fig_scatter(layer_filter=None, purity_min=0, highlight_hyb=False,
                year_range=None, ltype_filter=None):
    df = nodes.copy()
    if layer_filter and C_LAYER:  df = df[df[C_LAYER].isin(layer_filter)]
    if purity_min and C_CONF:     df = df[df[C_CONF] >= purity_min]
    if year_range and C_YEAR:
        df = df[(df[C_YEAR]>=year_range[0])&(df[C_YEAR]<=year_range[1])]
    if ltype_filter and C_TYPE:   df = df[df[C_TYPE].isin(ltype_filter)]

    fig = go.Figure()
    fig.update_layout(**{**PLOTLY_BASE,
                         "xaxis": dict(showticklabels=False,title="",gridcolor=BORDER,zerolinecolor=BORDER),
                         "yaxis": dict(showticklabels=False,title="",gridcolor=BORDER,zerolinecolor=BORDER)},
                      height=560,
                      title_text=SLABEL, title_font=dict(size=12,color="#64748b"),
                      hovermode="closest",
                      legend=dict(itemsizing="constant",font=dict(size=10)))

    for l in LAYERS+["noise"]:
        sub = df[df[C_LAYER]==l] if C_LAYER else df
        if sub.empty: continue
        conf_v = sub[C_CONF].fillna(0.5) if C_CONF else pd.Series([0.5]*len(sub),index=sub.index)
        is_h   = sub["is_hybrid"].fillna(0).astype(bool)
        hover  = sub.apply(lambda r: (
            f"<b>{r.get(C_ID,'?')}</b><br>"
            f"{str(r.get(C_TITLE,''))[:70]}<br>"
            f"Layer: <b>{r.get(C_LAYER,'?')}</b> | Purezza: <b>{r.get(C_CONF,0):.2f}</b><br>"
            f"Anno: {int(r[C_YEAR]) if C_YEAR and pd.notna(r.get(C_YEAR)) else '?'} | "
            f"Tipo: {r.get(C_TYPE,'?')}"
        ), axis=1)
        fig.add_trace(go.Scatter(
            x=sub[SX], y=sub[SY], mode="markers", name=l,
            marker=dict(
                color=LC.get(l,"#888"),
                size=(conf_v*16).clip(4,18),
                opacity=0.72,
                line=dict(
                    color=["#f59e0b" if (highlight_hyb and h) else "rgba(0,0,0,0)" for h in is_h],
                    width=[1.8 if (highlight_hyb and h) else 0 for h in is_h],
                ),
            ),
            text=hover, hovertemplate="%{text}<extra></extra>",
            customdata=sub[C_ID].tolist() if C_ID else sub.index.tolist(),
        ))
    return fig

def hex_rgba(hx, alpha):
    """Convert 6-digit hex color + float alpha to rgba() string for Plotly."""
    r,g,b = int(hx[1:3],16),int(hx[3:5],16),int(hx[5:7],16)
    return f"rgba({r},{g},{b},{alpha})"

def fig_radar(node_id):
    """Radar chart del fingerprint normativo — grande e leggibile."""
    if not node_id or not MEM_COLS:
        return empty_fig(380)
    r = NODE_MAP.get(node_id, {})
    if not r: return empty_fig(380)
    vals = [float(r.get(mc, 0)) for mc in MEM_COLS]
    vals_c = vals + [vals[0]]
    labs_c = LAYERS + [LAYERS[0]]

    # Layer dominante
    dominant_idx = int(np.argmax(vals))
    dominant     = LAYERS[dominant_idx] if LAYERS else "?"
    dom_color    = LC.get(dominant, "#60a5fa")

    fig = go.Figure()
    # Area di sfondo per il layer dominante
    fig.add_trace(go.Scatterpolar(
        r=[1]*len(labs_c), theta=labs_c, fill="toself",
        fillcolor=hex_rgba(dom_color,0.03), line=dict(color=hex_rgba(dom_color,0.13), width=0),
        showlegend=False, hoverinfo="skip",
    ))
    # Fingerprint dell'atto
    fig.add_trace(go.Scatterpolar(
        r=vals_c, theta=labs_c, fill="toself",
        fillcolor=hex_rgba(dom_color,0.16),
        line=dict(color=dom_color, width=2.5),
        marker=dict(size=8, color=dom_color, line=dict(color="#fff",width=1)),
        name="Distribuzione layer", showlegend=False,
        hovertemplate="<b>%{theta}</b><br>Peso: %{r:.0%}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(family=FONT, color="#94a3b8", size=11),
        height=340,
        margin=dict(l=30,r=30,t=30,b=20),
        showlegend=False,
        polar=dict(
            bgcolor="#080c14",
            radialaxis=dict(
                visible=True, range=[0,1],
                gridcolor="#1e2a45", tickfont=dict(size=9, color="#475569"),
                tickformat=".0%",
            ),
            angularaxis=dict(
                gridcolor="#1e2a45", linecolor="#1e2a45",
                tickfont=dict(size=12, color="#e2e8f0", family=FONT),
            ),
        ),
    )
    return fig

def cyto_elements(node_id, max_nb=50):
    if not node_id or not C_ID: return []
    out_nb = set(edges[edges[E_SRC]==node_id][E_TGT].tolist()) if E_SRC else set()
    in_nb  = set(edges[edges[E_TGT]==node_id][E_SRC].tolist()) if E_TGT else set()
    all_nb = list(out_nb | in_nb)[:max_nb]

    elems = []
    def make_node(nid, center=False):
        nr    = NODE_MAP.get(nid, {})
        layer = nr.get(C_LAYER,"noise") if C_LAYER else "noise"
        conf  = float(nr.get(C_CONF,0.5)) if C_CONF else 0.5
        color = LC.get(layer, "#475569")
        return {"data":{
            "id":nid, "label":nid[:10]+"…" if len(nid)>10 else nid,
            "color":color,
            "bc":"#ffffff" if center else ("#f59e0b" if conf<0.70 else color),
            "bw":3 if center else (1.5 if conf<0.70 else 0.8),
            "bs":"solid",
            "sz":38 if center else max(12, conf*24),
            "layer":"center" if center else layer,
        }}

    elems.append(make_node(node_id, center=True))
    for nb in all_nb:
        if nb in NODE_MAP: elems.append(make_node(nb))

    nb_set = set(all_nb)
    e_sub = edges[
        ((edges[E_SRC]==node_id)&(edges[E_TGT].isin(nb_set)))|
        ((edges[E_TGT]==node_id)&(edges[E_SRC].isin(nb_set)))
    ] if E_SRC else pd.DataFrame()
    for _,row in e_sub.iterrows():
        elems.append({"data":{"source":row[E_SRC],"target":row[E_TGT]}})
    return elems

# ─────────────────────────────────────────────────────────────────────────────
# 4. STATISTICHE GLOBALI
# ─────────────────────────────────────────────────────────────────────────────

N_NODES   = len(nodes)
N_EDGES   = len(edges)
N_LAYERS  = len(LAYERS)
PCT_HYB   = nodes["is_hybrid"].mean()*100
AVG_CONF  = nodes[C_CONF].mean() if C_CONF else 0
AVG_ENT   = nodes[C_ENT].mean() if C_ENT else 0
YR_MIN    = int(nodes[C_YEAR].min()) if C_YEAR else 1990
YR_MAX    = int(nodes[C_YEAR].max()) if C_YEAR else 2024
LT_OPTS   = [{"label":t,"value":t} for t in sorted(nodes[C_TYPE].dropna().unique())] if C_TYPE else []

# Top ibridi per shortlist
TOP_HYB = (nodes[nodes["is_hybrid"]==1].nlargest(8, C_ENT)[C_ID].tolist()
           if C_ENT and C_ID else nodes[C_ID].head(8).tolist() if C_ID else [])

# ─────────────────────────────────────────────────────────────────────────────
# 5. HELPERS UI
# ─────────────────────────────────────────────────────────────────────────────

TAB_S   = {"backgroundColor":DARK,"border":"none","borderBottom":f"2px solid {BORDER}",
           "color":"#475569","fontFamily":FONT,"fontSize":"11px","padding":"10px 22px"}
TAB_SEL = {**TAB_S,"color":"#e2e8f0","borderBottom":"2px solid #60a5fa","backgroundColor":DARK}

def card(children, style=None):
    s = {"background":PANEL,"border":f"1px solid {BORDER}","borderRadius":"8px","padding":"16px"}
    if style: s.update(style)
    return html.Div(children, style=s)

def lbl(text):
    return html.Div(text, style={"color":"#334155","fontSize":"8px","letterSpacing":"0.15em",
                                  "textTransform":"uppercase","marginBottom":"6px","fontFamily":FONT})

def stat_box(val, sublabel, color="#e2e8f0"):
    return html.Div([
        html.Div(str(val),style={"fontSize":"19px","fontWeight":"700","color":color,
                                  "lineHeight":"1.1","fontFamily":FONT}),
        html.Div(sublabel,style={"fontSize":"8px","color":"#475569","marginTop":"3px",
                                  "letterSpacing":"0.08em","textTransform":"uppercase"}),
    ], style={"background":"#111827","border":f"1px solid {BORDER}","borderRadius":"6px",
              "padding":"10px 14px","flex":"1","minWidth":"88px"})

def kv(k, v, vc="#94a3b8"):
    return html.Div([
        html.Span(k+": ",style={"color":"#475569","fontSize":"9px"}),
        html.Span(str(v),style={"color":vc,"fontSize":"9px"}),
    ], style={"marginBottom":"4px"})

def clean_text(raw):
    """Pulisce il testo del preambolo per la lettura: virgole → a capo dove sensato."""
    if not raw or str(raw).strip() in ("nan","None",""):
        return "Testo non disponibile per questo atto."
    t = str(raw)
    # Sostituisce ,Having / ,Whereas / ,Acting con a capo
    import re
    t = re.sub(r",\s*(Having|Whereas|Acting|The|Noting|Recalling|Recognising|Considering)", r"\n\n\1", t)
    t = re.sub(r",?\s*\((\d+)\)\s*", r"\n\n(\1) ", t)  # numerazione paragrafi
    return t.strip()

def pathology_label(conf, entropy):
    """Traduce i valori tecnici in un'etichetta leggibile per il giurista."""
    if conf is None: return "Non classificato", "#64748b"
    c = float(conf)
    e = float(entropy) if entropy else 0
    if c >= 0.85:
        return "Atto focalizzato — ruolo normativo chiaro", "#34d399"
    elif c >= 0.70:
        return "Atto prevalentemente focalizzato — lieve ambiguità di ruolo", "#60a5fa"
    elif c >= 0.55:
        return "Atto ibrido — svolge funzioni di più livelli contemporaneamente", "#f59e0b"
    else:
        return "Atto fortemente ibrido — ruolo normativo contraddittorio", "#f87171"

def layer_description(layer):
    """Descrizione in linguaggio legale del layer."""
    desc = {
        "G1": "Trattati fondativi — diritto primario dell'UE",
        "G2": "Legislazione quadro — regolamenti e direttive del Parlamento Europeo e Consiglio",
        "G3": "Legislazione secondaria — atti del Consiglio e regolamenti di attuazione",
        "G4": "Atti tecnici delegati — regolamenti delegati e di esecuzione della Commissione",
        "G5": "Controllo e giurisprudenza — decisioni, sentenze, atti sanzionatori",
        "L1": "Legge quadro — norma di principio e obiettivo",
        "L2": "Base giuridica — fondamento nei Trattati",
        "L3": "Legislazione secondaria — attuazione e specificazione",
        "L4": "Atti tecnici terminali — implementazione operativa",
        "noise": "Atto strutturalmente anomalo — non classificabile nei livelli rilevati",
    }
    return desc.get(layer, f"Livello {layer}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. APP
# ─────────────────────────────────────────────────────────────────────────────

cyto.load_extra_layouts()
app = dash.Dash(__name__, suppress_callback_exceptions=True,
    external_stylesheets=["https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&display=swap"])
app.title = "Reti Normative UE — Golden Power"

app.layout = html.Div(style={"backgroundColor":DARK,"color":"#e2e8f0",
                               "fontFamily":FONT,"minHeight":"100vh","fontSize":"12px"}, children=[
    # HEADER
    html.Div(style={"display":"flex","alignItems":"center","padding":"14px 24px 12px",
                    "borderBottom":f"1px solid {BORDER}","gap":"18px"}, children=[
        html.Div([
            html.Div("EU NORMATIVE NETWORK",style={"color":"#334155","fontSize":"8px","letterSpacing":"0.2em","marginBottom":"2px"}),
            html.Div("Golden Power / FDI Screening",style={"color":"#60a5fa","fontSize":"16px","fontWeight":"700"}),
        ]),
        html.Div(style={"display":"flex","gap":"7px","marginLeft":"auto"}, children=[
            stat_box(f"{N_NODES:,}","atti"),
            stat_box(f"{N_EDGES:,}","citazioni"),
            stat_box(N_LAYERS,"layer"),
            stat_box(f"{PCT_HYB:.1f}%","ibridi",color="#f59e0b"),
            stat_box(f"{AVG_CONF:.3f}","purezza media"),
        ]),
    ]),
    dcc.Tabs(id="tabs", value="v1",
             style={"backgroundColor":DARK,"borderBottom":"none"}, children=[
        dcc.Tab(label="① Piramide normativa", value="v1", style=TAB_S, selected_style=TAB_SEL),
        dcc.Tab(label="② Spazio normativo",   value="v2", style=TAB_S, selected_style=TAB_SEL),
        dcc.Tab(label="③ Analisi atto",       value="v3", style=TAB_S, selected_style=TAB_SEL),
    ]),
    html.Div(id="tab-content"),
    dcc.Store(id="store-celex"),
])

# ─────────────────────────────────────────────────────────────────────────────
# 7. CALLBACK TABS
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(Output("tab-content","children"), Input("tabs","value"),
              State("store-celex","data"))
def render_tab(tab, pending_celex=None):

    # ══════ VISTA 1 ══════
    if tab == "v1":
        rows = []
        for l in LAYERS+["noise"]:
            sub = nodes[nodes[C_LAYER]==l] if C_LAYER else pd.DataFrame()
            if sub.empty: continue
            n   = len(sub)
            ap  = sub[C_CONF].mean() if C_CONF else 0
            ph  = sub["is_hybrid"].mean()*100
            ae  = sub[C_ENT].mean() if C_ENT else 0
            rows.append(html.Tr([
                html.Td(html.Span(l,style={"color":LC.get(l,"#888"),"fontWeight":"600"})),
                html.Td(layer_description(l)[:40],style={"color":"#64748b","fontSize":"8px"}),
                html.Td(f"{n:,}",style={"textAlign":"right"}),
                html.Td(f"{ap:.2f}",style={"textAlign":"right"}),
                html.Td(f"{ph:.1f}%",style={"color":"#f59e0b" if ph>20 else "#94a3b8","textAlign":"right"}),
                html.Td(f"{ae:.3f}",style={"textAlign":"right"}),
            ], style={"borderBottom":f"1px solid {BORDER}"}))

        pyramid = [html.Div(style={"marginTop":"18px"})]
        for i,l in enumerate(LAYERS):
            n_l = int((nodes[C_LAYER]==l).sum()) if C_LAYER else 0
            pyramid.append(html.Div(style={
                "background":LC.get(l,"#888")+"18","border":f"1px solid {LC.get(l,'#888')}44",
                "borderRadius":"4px","padding":"7px 12px","marginBottom":"4px",
                "width":f"{100-i*10}%","margin":"0 auto 5px",
                "display":"flex","justifyContent":"space-between","alignItems":"center",
            }, children=[
                html.Span(l,style={"color":LC.get(l,"#888"),"fontWeight":"700","fontSize":"11px"}),
                html.Span(layer_description(l)[:32],style={"color":"#475569","fontSize":"8px"}),
                html.Span(f"{n_l:,} atti",style={"color":"#334155","fontSize":"8px"}),
            ]))

        return html.Div([
            html.Div(style={"display":"flex","gap":"12px","padding":"14px 18px 8px"}, children=[
                card([lbl("Flusso di citazioni tra livelli"),
                      dcc.Graph(figure=fig_sankey(), config={"displayModeBar":False})],
                     {"flex":"1.6"}),
                card([
                    lbl("Composizione per livello"),
                    html.Table([
                        html.Thead(html.Tr([html.Th(h,style={"color":"#334155","fontSize":"8px",
                            "textAlign":"right" if i>1 else "left","paddingBottom":"7px"})
                            for i,h in enumerate(["Livello","Descrizione","Atti","Purezza","% Ibridi","Entropia"])])),
                        html.Tbody(rows),
                    ], style={"width":"100%","borderCollapse":"collapse","fontSize":"10px","color":"#94a3b8"}),
                    *pyramid,
                ], {"flex":"1"}),
            ]),
            html.Div(style={"display":"flex","gap":"12px","padding":"0 18px 14px"}, children=[
                card([dcc.Graph(figure=fig_purity_box(), config={"displayModeBar":False})],{"flex":"1"}),
                card([dcc.Graph(figure=fig_entropy_hist(), config={"displayModeBar":False})],{"flex":"1"}),
                card([
                    lbl("Sintesi"),
                    html.Div([
                        html.Span(f"{int(PCT_HYB/100*N_NODES):,}",
                                  style={"fontSize":"26px","fontWeight":"700","color":"#f87171"}),
                        html.Span(" atti con ruolo normativo ambiguo",
                                  style={"color":"#475569","fontSize":"10px","marginLeft":"6px"}),
                    ], style={"marginBottom":"10px"}),
                    html.Hr(style={"borderColor":BORDER,"margin":"10px 0"}),
                    kv("Atti ibridi (<0.70)", f"{PCT_HYB:.1f}%","#f59e0b"),
                    kv("Entropia media", f"{AVG_ENT:.3f}","#60a5fa"),
                    kv("Purezza media", f"{AVG_CONF:.3f}","#34d399"),
                    kv("Layer inferiti", N_LAYERS),
                ], {"flex":"0.6"}),
            ]),
        ])

    # ══════ VISTA 2 ══════
    elif tab == "v2":
        sidebar = card([
            lbl("Layer"),
            dcc.Checklist(id="f-layers",
                options=[{"label":html.Span(l,style={"color":LC[l],"fontFamily":FONT,"fontSize":"10px"}),"value":l}
                         for l in LAYERS+["noise"]],
                value=LAYERS+["noise"],
                labelStyle={"display":"flex","alignItems":"center","gap":"6px","marginBottom":"5px"},
                inputStyle={"accentColor":"#60a5fa"}),
            html.Hr(style={"borderColor":BORDER,"margin":"10px 0"}),
            lbl("Purezza minima"),
            dcc.Slider(id="f-purity", min=0, max=0.95, step=0.05, value=0,
                       marks={0:"0",0.5:"0.5",0.7:"0.7"},
                       tooltip={"placement":"bottom","always_visible":False}),
            html.Div(id="f-count",style={"color":"#475569","fontSize":"8px","marginTop":"5px"}),
            html.Hr(style={"borderColor":BORDER,"margin":"10px 0"}),
            lbl("Anno"),
            dcc.RangeSlider(id="f-year", min=YR_MIN, max=YR_MAX, step=1, value=[YR_MIN,YR_MAX],
                            marks={YR_MIN:str(YR_MIN),YR_MAX:str(YR_MAX)},
                            tooltip={"placement":"bottom"}),
            html.Hr(style={"borderColor":BORDER,"margin":"10px 0"}),
            dcc.Checklist(id="f-hyb",
                options=[{"label":html.Span("Evidenzia ibridi",style={"color":"#f59e0b","fontSize":"10px"}),"value":"yes"}],
                value=[], inputStyle={"accentColor":"#f59e0b"}),
            html.Hr(style={"borderColor":BORDER,"margin":"10px 0"}),
            lbl("Tipo legale"),
            dcc.Dropdown(id="f-type",options=LT_OPTS,value=None,multi=True,
                         placeholder="Tutti i tipi...",
                         style={"fontSize":"9px","backgroundColor":"#111827","color":"#e2e8f0"}),
        ], {"width":"195px","flexShrink":"0","overflowY":"auto","maxHeight":"calc(100vh - 145px)"})

        detail_panel = card([
            lbl("Atto selezionato"),
            html.Div(id="detail",children=html.Div(
                "Clicca un punto nello scatter per ispezionare l'atto",
                style={"color":"#334155","fontSize":"9px","marginTop":"20px","textAlign":"center","lineHeight":"1.6"})),
            html.Div(id="detail-hr",style={"borderTop":f"1px solid {BORDER}","margin":"12px 0","display":"none"}),
            html.Button("→ Analisi completa", id="btn-goto-v3",
                        style={"display":"none","backgroundColor":"#1a2a45","color":"#60a5fa",
                               "border":"1px solid #253555","borderRadius":"5px","padding":"8px 12px",
                               "fontSize":"9px","cursor":"pointer","width":"100%","fontFamily":FONT}),
        ], {"width":"235px","flexShrink":"0","overflowY":"auto","maxHeight":"calc(100vh - 145px)"})

        return html.Div([
            html.Div(style={"display":"flex","gap":"12px","padding":"14px 18px",
                            "height":"calc(100vh - 145px)"}, children=[
                sidebar,
                card([dcc.Graph(id="scatter", figure=fig_scatter(),
                                config={"displayModeBar":True,"modeBarButtonsToRemove":["lasso2d","select2d"]},
                                style={"height":"100%"}, clear_on_unhover=True)],
                     {"flex":"1","padding":"8px"}),
                detail_panel,
            ]),
        ])

    # ══════ VISTA 3 — DRILL-DOWN RIPROGETTATO ══════
    elif tab == "v3":
        shortlist = [
            html.Div(c, id={"type":"sl","index":c},
                     n_clicks=0,
                     style={"padding":"5px 9px","marginBottom":"3px","borderRadius":"4px",
                            "cursor":"pointer","fontSize":"9px","color":"#f59e0b",
                            "background":"rgba(245,158,11,0.07)","border":"1px solid rgba(245,158,11,0.18)",
                            "overflow":"hidden","textOverflow":"ellipsis","whiteSpace":"nowrap"})
            for c in TOP_HYB
        ]

        # ── Colonna sinistra: ricerca + shortlist ────────────────────────────
        left = card([
            lbl("Cerca atto"),
            dcc.Dropdown(id="dd-select", placeholder="CELEX ID...",
                options=[{"label":f"{r[C_ID]}", "value":r[C_ID]}
                         for _,r in nodes[[C_ID]].dropna().iterrows()] if C_ID else [],
                value=pending_celex,
                style={"fontSize":"9px","backgroundColor":"#111827"},
                optionHeight=28,
            ),
            html.Hr(style={"borderColor":BORDER,"margin":"12px 0"}),
            lbl("Atti con ibridità più elevata"),
            html.Div(id="shortlist", children=shortlist),
            html.Hr(style={"borderColor":BORDER,"margin":"12px 0"}),

            # Legenda layer compatta
            lbl("Livelli normativi"),
            *[html.Div(style={"display":"flex","alignItems":"flex-start","gap":"7px","marginBottom":"6px"},
                        children=[
                html.Div(style={"width":"8px","height":"8px","borderRadius":"50%",
                                "backgroundColor":LC.get(l,"#888"),"flexShrink":"0","marginTop":"2px"}),
                html.Div([
                    html.Span(l+"  ",style={"color":LC.get(l,"#888"),"fontWeight":"600","fontSize":"9px"}),
                    html.Span(layer_description(l),style={"color":"#334155","fontSize":"8px"}),
                ]),
            ]) for l in LAYERS],
        ], {"width":"220px","flexShrink":"0","overflowY":"auto","maxHeight":"calc(100vh - 145px)"})

        # ── Colonna centro: alert + metadati + testo ─────────────────────────
        center = card([
            # Alert card — la prima cosa che vede il giurista
            html.Div(id="alert-card"),
            html.Hr(style={"borderColor":BORDER,"margin":"14px 0"}),

            # Metadati in due colonne
            html.Div(id="dd-meta"),
            html.Hr(style={"borderColor":BORDER,"margin":"14px 0"}),

            # Testo legale
            lbl("Testo estratto dall'atto"),
            html.Div(id="dd-text",
                     style={"fontSize":"10px","color":"#94a3b8","lineHeight":"1.9",
                            "whiteSpace":"pre-wrap","fontFamily":"Georgia, serif",
                            "background":"#080c14","border":f"1px solid {BORDER}",
                            "borderRadius":"5px","padding":"16px",
                            "overflowY":"auto","maxHeight":"calc(100vh - 420px)"}),
        ], {"flex":"1","overflowY":"auto","maxHeight":"calc(100vh - 145px)"})

        # ── Colonna destra: radar + ego ──────────────────────────────────────
        right = card([
            # Radar — protagonista visivo
            lbl("Fingerprint normativo"),
            html.Div(id="radar-title",
                     style={"color":"#64748b","fontSize":"9px","marginBottom":"8px","lineHeight":"1.5"}),
            dcc.Graph(id="radar", figure=empty_fig(340),
                      config={"displayModeBar":False}, style={"marginBottom":"8px"}),
            html.Div(id="mem-bars"),

            html.Hr(style={"borderColor":BORDER,"margin":"14px 0"}),

            # Rete ego
            lbl("Rete di citazioni dirette"),
            html.Div(id="ego-info",style={"color":"#475569","fontSize":"8px","marginBottom":"8px"}),
            cyto.Cytoscape(id="ego", elements=[], stylesheet=CYTO_STYLE,
                layout={"name":"cose","idealEdgeLength":100,"nodeRepulsion":5000,
                        "gravity":0.2,"animate":True,"animationDuration":600},
                style={"height":"320px","width":"100%","backgroundColor":"#080c14","borderRadius":"6px"},
                zoomingEnabled=True, panningEnabled=True),
            # Legenda colori rete
            html.Div(style={"display":"flex","flexWrap":"wrap","gap":"8px","marginTop":"8px"}, children=[
                html.Div(style={"display":"flex","alignItems":"center","gap":"4px"}, children=[
                    html.Div(style={"width":"8px","height":"8px","borderRadius":"50%","background":LC.get(l,"#888")}),
                    html.Span(l,style={"color":"#475569","fontSize":"8px"}),
                ]) for l in LAYERS
            ]),
        ], {"width":"320px","flexShrink":"0","overflowY":"auto","maxHeight":"calc(100vh - 145px)"})

        return html.Div([
            html.Div(style={"display":"flex","gap":"12px","padding":"14px 18px",
                            "height":"calc(100vh - 145px)"}, children=[left, center, right]),
        ])

    return html.Div()


# ─────────────────────────────────────────────────────────────────────────────
# 8. CALLBACKS VISTA 2
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("scatter","figure"), Output("f-count","children"),
    Input("f-layers","value"), Input("f-purity","value"),
    Input("f-hyb","value"), Input("f-year","value"), Input("f-type","value"),
)
def update_scatter(layers, purity, hyb, year, ltype):
    highlight = "yes" in (hyb or [])
    fig = fig_scatter(layer_filter=layers, purity_min=purity or 0,
                      highlight_hyb=highlight, year_range=year, ltype_filter=ltype)
    df = nodes.copy()
    if layers and C_LAYER:  df = df[df[C_LAYER].isin(layers)]
    if purity and C_CONF:   df = df[df[C_CONF] >= purity]
    if year and C_YEAR:     df = df[(df[C_YEAR]>=year[0])&(df[C_YEAR]<=year[1])]
    if ltype and C_TYPE:    df = df[df[C_TYPE].isin(ltype)]
    return fig, f"{len(df):,} atti visibili"


@app.callback(
    Output("detail","children"), Output("store-celex","data"),
    Output("btn-goto-v3","style"), Output("detail-hr","style"),
    Input("scatter","clickData"), prevent_initial_call=True,
)
def show_detail(click):
    _btn_hidden  = {"display":"none"}
    _btn_visible = {"display":"block","backgroundColor":"#1a2a45","color":"#60a5fa",
                    "border":"1px solid #253555","borderRadius":"5px","padding":"8px 12px",
                    "fontSize":"9px","cursor":"pointer","width":"100%","fontFamily":FONT}
    _hr_hidden  = {"borderTop":f"1px solid {BORDER}","margin":"12px 0","display":"none"}
    _hr_visible = {"borderTop":f"1px solid {BORDER}","margin":"12px 0"}

    if not click or not click.get("points"):
        return (html.Div("Clicca un punto",style={"color":"#334155","fontSize":"9px",
                "textAlign":"center","marginTop":"20px"}), None, _btn_hidden, _hr_hidden)

    nid = click["points"][0].get("customdata")
    if not nid or nid not in NODE_MAP:
        return html.Div("Non trovato",style={"color":"#f87171","fontSize":"9px"}), None, _btn_hidden, _hr_hidden

    r     = NODE_MAP[nid]
    layer = r.get(C_LAYER,"?") if C_LAYER else "?"
    conf  = float(r.get(C_CONF,0)) if C_CONF else 0
    ent   = float(r.get(C_ENT,0)) if C_ENT else 0
    year  = r.get(C_YEAR,None) if C_YEAR else None
    alert_text, alert_color = pathology_label(conf, ent)

    mem_bars = []
    for mc,l in zip(MEM_COLS,LAYERS):
        v = float(r.get(mc,0))
        mem_bars.append(html.Div([
            html.Span(l,style={"color":LC[l],"fontSize":"8px","width":"22px","display":"inline-block"}),
            html.Div(style={"display":"inline-block","height":"5px","verticalAlign":"middle",
                            "width":f"{v*100:.0f}%","background":LC[l],"borderRadius":"2px",
                            "marginLeft":"5px","opacity":"0.85"}),
            html.Span(f"{v:.0%}",style={"fontSize":"7px","color":"#475569","marginLeft":"4px"}),
        ], style={"marginBottom":"3px"}))

    return (html.Div([
        html.Div(alert_text,style={"color":alert_color,"fontSize":"9px","fontWeight":"600","marginBottom":"7px"}),
        html.Div(nid,style={"color":"#64748b","fontSize":"8px","marginBottom":"4px","wordBreak":"break-all"}),
        html.Div(str(r.get(C_TITLE,""))[:85],
                 style={"color":"#94a3b8","fontSize":"9px","lineHeight":"1.5","marginBottom":"8px"}),
        kv("Anno",   int(year) if year and pd.notna(year) else "—"),
        kv("Livello",layer_description(layer)),
        kv("Tipo",   r.get(C_TYPE,"?") if C_TYPE else "—"),
        kv("Purezza", f"{conf:.2f}", "#f59e0b" if conf<0.70 else "#34d399"),
        html.Hr(style={"borderColor":BORDER,"margin":"7px 0"}),
        *mem_bars,
    ]), nid, _btn_visible, _hr_visible)


@app.callback(
    Output("tabs","value"),
    Input("btn-goto-v3","n_clicks"),
    prevent_initial_call=True,
)
def goto_v3(n):
    if n: return "v3"
    return dash.no_update


# ─────────────────────────────────────────────────────────────────────────────
# 9. CALLBACKS VISTA 3
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("alert-card","children"),
    Output("dd-meta","children"),
    Output("dd-text","children"),
    Output("radar","figure"),
    Output("radar-title","children"),
    Output("mem-bars","children"),
    Output("ego","elements"),
    Output("ego-info","children"),
    Input("dd-select","value"),
    prevent_initial_call=True,
)
def update_drilldown(nid):
    placeholder = (
        html.Div(),
        html.Div("Seleziona un atto dal menu o dalla lista degli atti ibridi",
                 style={"color":"#334155","fontSize":"9px","textAlign":"center","marginTop":"30px"}),
        "", empty_fig(340), "", html.Div(), [], ""
    )
    if not nid or nid not in NODE_MAP:
        return placeholder

    r     = NODE_MAP[nid]
    layer = r.get(C_LAYER,"?") if C_LAYER else "?"
    conf  = float(r.get(C_CONF, 0)) if C_CONF else 0
    ent   = float(r.get(C_ENT, 0)) if C_ENT else 0
    year  = r.get(C_YEAR, None) if C_YEAR else None
    ltype = r.get(C_TYPE, "—") if C_TYPE else "—"
    motiv = r.get(C_MOTIV, "") if C_MOTIV else ""
    title = str(r.get(C_TITLE, "")) if C_TITLE else ""
    ind   = r.get(C_IND, "—") if C_IND else "—"
    out   = r.get(C_OUT, "—") if C_OUT else "—"

    alert_text, alert_color = pathology_label(conf, ent)

    # ─ Alert card
    alert_card = html.Div(style={
        "background": alert_color+"12",
        "border": f"1px solid {alert_color}40",
        "borderRadius": "8px", "padding": "14px 16px",
        "borderLeft": f"4px solid {alert_color}",
    }, children=[
        html.Div(style={"display":"flex","alignItems":"center","gap":"10px","marginBottom":"6px"}, children=[
            html.Div(style={"width":"10px","height":"10px","borderRadius":"50%",
                            "background":alert_color,"flexShrink":"0"}),
            html.Div(alert_text, style={"color":alert_color,"fontWeight":"700","fontSize":"11px"}),
        ]),
        html.Div(nid, style={"color":"#64748b","fontSize":"8px","marginBottom":"6px"}),
        html.Div(title[:110] if title else "—",
                 style={"color":"#e2e8f0","fontSize":"13px","fontWeight":"600","lineHeight":"1.4"}),
    ])

    # ─ Metadati in griglia
    year_str = str(int(year)) if year and pd.notna(year) else "—"
    meta = html.Div([
        html.Div(style={"display":"grid","gridTemplateColumns":"1fr 1fr","gap":"4px 24px"}, children=[
            kv("Livello assegnato",  f"{layer} — {layer_description(layer)[:35]}"),
            kv("Tipo legale",        ltype),
            kv("Anno",               year_str),
            kv("Citato da",          f"{ind} atti"),
            kv("Cita",               f"{out} atti"),
            kv("Purezza classificazione",
               f"{conf:.0%}",
               "#f59e0b" if conf<0.70 else "#34d399"),
        ]),
        html.Div(str(motiv) if motiv and str(motiv) not in ("nan","None","") else "",
                 style={"color":"#475569","fontSize":"9px","fontStyle":"italic",
                        "marginTop":"8px","lineHeight":"1.6"})
        if motiv and str(motiv) not in ("nan","None","") else html.Div(),
    ])

    # ─ Testo pulito
    raw_text = r.get(C_TEXT, "") if C_TEXT else ""
    text_clean = clean_text(raw_text)

    # ─ Radar
    vals = [float(r.get(mc,0)) for mc in MEM_COLS]
    dominant_idx = int(np.argmax(vals))
    dominant = LAYERS[dominant_idx] if LAYERS else "?"
    pure_pct = max(vals) if vals else 0

    radar_title = (
        f"L'atto è classificato principalmente come {dominant} "
        f"({pure_pct:.0%} del peso totale). "
        + ("La distribuzione su più livelli indica un ruolo normativo ibrido."
           if conf < 0.70 else "La classificazione è netta e coerente.")
    )

    # ─ Membership bars
    mb = []
    for mc, l in zip(MEM_COLS, LAYERS):
        v = float(r.get(mc, 0))
        is_dom = (l == dominant)
        mb.append(html.Div(style={"marginBottom":"7px"}, children=[
            html.Div(style={"display":"flex","justifyContent":"space-between","marginBottom":"3px"}, children=[
                html.Span(f"{l} — {layer_description(l)[:28]}",
                          style={"color":LC[l] if is_dom else "#64748b",
                                 "fontSize":"8px","fontWeight":"600" if is_dom else "400"}),
                html.Span(f"{v:.0%}", style={"color":LC[l],"fontSize":"8px","fontWeight":"700" if is_dom else "400"}),
            ]),
            html.Div(style={"height":"6px","background":BORDER,"borderRadius":"3px","overflow":"hidden"}, children=[
                html.Div(style={"height":"100%","width":f"{v*100:.1f}%",
                                "background":LC[l],"borderRadius":"3px",
                                "opacity":"1" if is_dom else "0.5",
                                "transition":"width 0.4s ease"}),
            ]),
        ]))

    # ─ Ego
    elems    = cyto_elements(nid)
    nb_count = max(0, len(elems) - 1)
    ego_info = (f"{nb_count} atti collegati direttamente — "
                "bordo arancione = atti con ruolo ibrido")

    return (alert_card, meta, text_clean, fig_radar(nid),
            radar_title, html.Div(mb), elems, ego_info)


@app.callback(
    Output("dd-select","value", allow_duplicate=True),
    Input({"type":"sl","index":dash.ALL},"n_clicks"),
    State({"type":"sl","index":dash.ALL},"id"),
    prevent_initial_call=True,
)
def shortlist_click(clicks, ids):
    if not any(clicks): return dash.no_update
    i = next((i for i,n in enumerate(clicks) if n), None)
    return ids[i]["index"] if i is not None else dash.no_update


# ─────────────────────────────────────────────────────────────────────────────
# 10. RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'='*54}")
    print(f"  Reti Normative UE — Golden Power / FDI Screening")
    print(f"  Nodi: {N_NODES:,} | Archi: {N_EDGES:,} | Layer: {LAYERS}")
    print(f"  Ibridi: {PCT_HYB:.1f}% | Purezza media: {AVG_CONF:.3f}")
    print(f"  → http://localhost:8050")
    print(f"{'='*54}\n")
    app.run(debug=True, port=8050)