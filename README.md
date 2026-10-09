# The hierarchical organization of urban social overlap

Code for the figures and tables of

> B. Poudyal, M. Macedo, R. Menezes and G. Ghoshal,
> *The hierarchical organization of urban social overlap: How shared social spaces diverge from physical mobility*,
> [arXiv:2609.12888](https://arxiv.org/abs/2609.12888) (2026).

## Contents

| File | Purpose |
|---|---|
| `reproduce_figure_code.ipynb` | Figs. 3–6, Tables I–II and Supplementary Figs. 5–8, from the co-presence overlap networks |
| `mobility_hierarchy.py` | Hierarchy Φ of the mobility network of each city, from the raw call detail records (input of Fig. 5) |

Figs. 1 and 2 are schematics. Supplementary Fig. 3 is section 3 of the notebook run on the
15- and 45-minute data.

## Setup

Python 3.9 or later.

```bash
pip install -r requirements.txt
jupyter notebook reproduce_figure_code.ipynb
```

## Data

The notebook reads from `Data/` (set `DATA_DIR` in its first cell); the folder is not tracked by git.
The call detail records and the files derived from them are not distributed with this
repository. The population raster is the WorldPop UN-adjusted population count for Brazil,
2016, available from [worldpop.org](https://www.worldpop.org).

| File | Content | Used for |
|---|---|---|
| `3_unified_social_metrics_<City>.csv` | `metric_type, antenna1, lat1, long1, antenna2, lat2, long2, value` | everything |
| `Mobility_hotspots/hotspots_loubar_<City>.csv` | `antenna, activity_volume` | mobility centres (Table I, Supplementary Figs. 6–7) |
| `Mobility_hierarchy/hierarchical_flow_<City>.txt` | Φ of the mobility network, written by `mobility_hierarchy.py` | Fig. 5 |
| `bra-ppp-2016-UNadj.tif` | WorldPop population counts, UN-adjusted | residential centres and η (Table II, Fig. 6) |

In `3_unified_social_metrics_<City>.csv`, rows with `metric_type = colocation` hold the
colocation of `antenna1` in `value` (one row per antenna); rows with
`metric_type = co-connectedness` hold the co-connectedness of the pair (`antenna1`, `antenna2`).

The cities are Belem, Belo_Horizonte, Brasilia, Campinas, Fortaleza, Goiania, Guarulhos,
Maceio, Manaus, Recife, Salvador, Sao_Luis and Sao_Paulo. File names are matched regardless
of case, accents and separators (`Sao_Luis`, `Sao Luis`, `SãoLuís`).

The mobility hierarchy needs the raw call detail records:

```bash
python mobility_hierarchy.py --cdr-dir /path/to/CDRs --out-dir Data/Mobility_hierarchy
```

The maps use the CARTO Positron basemap, which requires a free API key
([carto.com/basemaps/apikey](https://carto.com/basemaps/apikey)). Set it before starting Jupyter:

```bash
export CARTO_API_KEY=your-key
```

Without a key the maps are drawn on the Esri light-gray basemap.

## Implementation notes

- **Activity levels.** Iterated LouBar on colocation (on outgoing trips for mobility). Equal
  values are ranked by antenna id, so a cut inside a group of ties always splits it the same way.
- **Interaction matrix.** Co-connectedness is summed between activity levels into a symmetric
  matrix; mobility trips are summed into a directed one.
- **Null models.** Node Shuffling permutes colocation across antennas and recomputes the levels.
  Edge Shuffling draws the total overlap from a multinomial distribution over the cells of the
  matrix with the probabilities of Eq. (S1). Both use 100 realisations.
- **Functional centres.** Weighted Gaussian KDE (Scott's rule) of antenna activity in EPSG:3857,
  on a grid with about three points per median antenna spacing. A centre is a local maximum
  whose density exceeds the LouBar threshold computed over all grid values.
- **Residential population.** WorldPop pixels are summed over the Voronoi cells of the antennas
  with positive colocation. Antennas sharing a site are each assigned the population of its cell.
- **Random numbers.** Bootstrap and null models use a fixed seed (`SEED` in the first cell).

## Citation

```bibtex
@article{poudyal2026hierarchical,
  title   = {The hierarchical organization of urban social overlap: How shared social spaces diverge from physical mobility},
  author  = {Poudyal, Bibandhan and Macedo, Mariana and Menezes, Ronaldo and Ghoshal, Gourab},
  journal = {arXiv preprint arXiv:2609.12888},
  year    = {2026}
}
```
