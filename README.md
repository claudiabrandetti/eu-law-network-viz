# LCGraph-EURlex

## Mapping the Legislative Complexity of the European Union

This project applies the **LCGraph** (Layout-Clustered Graph) methodology to the EUR-Lex corpus, transforming over 88,000 interconnected EU legal documents into a navigable, thematic landscape. By addressing the visual and analytical challenges posed by dense citation networks, LCGraph-EURlex enables policymakers, researchers, and legal practitioners to identify functional communities and cross-domain regulatory patterns that remain hidden in traditional bureaucratic categorizations.

---

## The Problem: Cluster Blindness

The EU legal framework is characterized by an exceptionally high density of cross-references among regulations, directives, and decisions. While this interconnectedness reflects the integrated nature of EU governance, it creates a significant visualization challenge: **cluster blindness**.

When rendered using conventional force-directed layouts, the citation network collapses into a dense, visually indistinguishable mass—an "hairball" where thematic niches and domain boundaries are obscured. For legislators and policy analysts, this visual clutter masks the true structural organization of the legal system, making it difficult to:

- Identify which regulations are functionally related beyond formal categories
- Detect cross-domain legislative themes (e.g., dual-use technologies spanning Defense, Health, and ICT)
- Navigate the regulatory landscape efficiently

The result is a paradox: the more comprehensive the legal network, the less interpretable it becomes through standard visualization techniques.

---

## Methodology: LCGraph

LCGraph addresses cluster blindness through a three-stage approach that prioritizes **functional communities**, **visual clarity**, and **hierarchical exploration**.

### 1. Louvain Clustering

We apply the Louvain community detection algorithm to partition the citation network based on the density of actual legal references, rather than relying solely on predefined administrative categories (e.g., EUR-Lex subject codes). This reveals:

- **Functional communities**: Groups of regulations that cite each other frequently, indicating operational interdependence
- **Thematic coherence**: Clusters that may span multiple formal categories but share underlying regulatory objectives
- **Cross-domain bridges**: Acts that serve as connectors between otherwise separate policy areas

### 2. Grid Layout and Tabu Search Optimization

To eliminate visual overlap and reduce edge crossings, we employ a **grid-based layout** combined with **tabu search optimization**:

- **Grid Constraint**: Each node is assigned to a discrete cell in a 2D grid, ensuring zero geometric overlap ($M_{go} = 0$)
- **Tabu Search**: An iterative optimization procedure minimizes edge crossings by exploring alternative node placements while avoiding recently visited configurations
- **Cluster Preservation**: The spatial arrangement respects community boundaries, placing nodes from the same cluster in proximity

This approach transforms the "hairball" into a structured map where visual position encodes thematic membership.

### 3. Levels of Detail (LOD)

LCGraph supports hierarchical navigation through multiple zoom levels:

- **Macro-level**: Overview of major thematic areas (e.g., Internal Market, Environment, Justice)
- **Meso-level**: Individual clusters and their interconnections
- **Micro-level**: Specific regulations and their direct citation relationships

Users can interactively drill down from broad policy domains to individual legal acts, maintaining context at each scale.

---

## Case Study: Golden Power

The initial deployment of LCGraph-EURlex focuses on the **Golden Power** framework, specifically analyzing the network surrounding **Regulation (EU) 2019/452** on the screening of foreign direct investments (FDI).

### Why Golden Power?

Golden Power provisions enable EU member states to review and potentially block foreign investments in critical sectors. This regulatory area is inherently **cross-domain**, touching:

- **Defense and Security**: Dual-use technologies, critical infrastructure
- **Public Health**: Pharmaceutical supply chains, medical equipment
- **Energy**: Grid security, renewable energy technologies
- **ICT and Digital Infrastructure**: Telecommunications, data centers, semiconductors

### The Perfect Test Case

This thematic breadth makes Golden Power an ideal proving ground for LCGraph. Traditional categorizations would scatter these regulations across multiple administrative silos, obscuring their functional relationships. By contrast, LCGraph's community detection reveals how FDI screening logic permeates diverse policy domains—uncovering "hidden" themes that are invisible in standard EUR-Lex browsing interfaces.

The analysis demonstrates that critical regulatory patterns emerge not from top-down classification schemes, but from the organic structure of legislative citations themselves.

---

## Repository Structure

```
lcgraph-eurlex/
│
├── data/
│   ├── raw/                 # Original EUR-Lex XML/JSON files
│   ├── processed/           # Cleaned citation networks (CSV, GraphML)
│   └── clusters/            # Louvain community assignments
│
├── src/
│   ├── clustering/          # Louvain implementation and metrics
│   ├── optimization/        # Grid layout and tabu search algorithms
│   ├── viz/                 # Interactive visualization (D3.js, Plotly)
│   └── utils/               # Data parsing, validation, export functions
│
├── notebooks/
│   ├── 01_data_extraction.ipynb
│   ├── 02_network_analysis.ipynb
│   ├── 03_clustering.ipynb
│   ├── 04_layout_optimization.ipynb
│   └── 05_golden_power_case_study.ipynb
│
├── results/
│   ├── figures/             # Generated visualizations
│   └── reports/             # Analysis summaries and metrics
│
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- NetworkX, scikit-learn, pandas, numpy
- Visualization: D3.js (for web interface), matplotlib/plotly (for static exports)

### Installation

```bash
git clone https://github.com/claudiabrandetti/lcgraph-eurlex.git
cd lcgraph-eurlex
pip install -r requirements.txt
```

### Quick Start

```python
from src.clustering import louvain_partition
from src.optimization import grid_layout_optimize
from src.viz import render_interactive_map

# Load EUR-Lex citation network
G = load_eurlex_graph('data/processed/eurlex_citations.graphml')

# Detect communities
communities = louvain_partition(G)

# Optimize layout
layout = grid_layout_optimize(G, communities)

# Visualize
render_interactive_map(G, layout, communities)
```

---

## Citation

If you use LCGraph-EURlex in your research, please cite:

```bibtex
@software{lcgraph_eurlex,
  author = {Claudia Brandetti},
  title = {LCGraph-EURlex: Mapping EU Legislative Complexity},
  year = {2026},
  url = {https://github.com/claudiabrandetti/lcgraph-eurlex}
}
```
---

## Acknowledgments

EUR-Lex data is provided by the Publications Office of the European Union under the [EU Open Data Portal](https://data.europa.eu/) terms of use.