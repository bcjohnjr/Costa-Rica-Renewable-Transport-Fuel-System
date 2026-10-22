# Reproduction — Costa Rica renewable transport model

This file maps every table and figure of the manuscript (Spanish and English editions) to the
code and outputs that produce it, and gives a single command that checks the manuscript's
numbers against a fresh run.

## 1. Run the model

Python 3.13, with the pinned versions in `requirements-lock.txt`:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt
bash run_all.sh            # about two minutes; ends by running verify_manuscript.py
```

`run_all.sh` creates `outputs/`, runs the model and both figure sets, and finishes with
`verify_manuscript.py`, which makes two independent checks and exits with an error listing any
mismatch:

1. **Registered values** — 273 model-derived numbers from Tables 1–6, Figures 3 and 6–11 and the
   offshore-wind, PVT, hourly-CST and fertilizer results of Sections 3.9–3.11, transcribed in the
   script, against `outputs/`.
2. **Submitted documents** — with `--docx`, the script opens each manuscript file (English or
   Spanish edition), reads every number printed in Tables 1–6 (178 per file) and checks it against
   `outputs/` at the precision printed. `run_all.sh` passes any `.docx` placed in `manuscript/`.
   That folder is listed in `.gitignore` and stays local: the article itself is distributed only
   after publication.

Every check is written to `outputs/verification_report.txt` with the Python and package versions
and a SHA-256 fingerprint of each manuscript file read. A clean run on Python 3.13.16 with the
pinned packages prints `All values match.`, and every regenerated file in `outputs/` is
numerically identical to the committed copy (relative tolerance 10⁻⁶).

## 2. Units convention

| Quantity | Field in `biorefinery.py` | Unit |
|:--|:--|:--|
| Hydrocarbon liquids (diesel and jet range) | `hc_gj` | GJ per dry tonne |
| Jet-range fraction | `jet_gj` | GJ per dry tonne |
| Ethanol | `ethanol_gj` | GJ per dry tonne |
| Biomethane | `ch4_gj` | GJ per dry tonne |
| Refinery electricity | `el_mwh` | MWh per dry tonne, consumed |
| Refinery process heat | `heat_mwh_th` | MWh thermal per dry tonne, consumed |

`optimise.py` converts fuel fields with `GJ2TWH = 1 / 3.6e6`. Fuel terms enter the balance
constraints with a negative coefficient (supply) and `el_mwh` with a positive coefficient
(demand): refinery electricity is a load on the national system, not a co-product.

## 3. Main tables

| Table | Content | Source | Checked by `verify_manuscript.py` |
|:--|:--|:--|:--|
| 1 | Vehicle premium per MWh replaced, 7% and 4% | `optimise.vehicle_premium_per_mwh` | yes (18 values) |
| 2 | Refinery routes per dry tonne | `outputs/biorefinery_per_dry_tonne.json` | yes (30 values) |
| 3 | Principal cases | `outputs/results.json` | yes (20 values) |
| 4 | Capital by component | `outputs/results.json` → `build.capex_busd` | yes (39 values) |
| 5 | Monte Carlo, 1,000 draws | `outputs/monte_carlo_summary.json` | yes (51 values) |
| 6 | Offshore wind, PVT and CST supply options | `hybrid_offshore_pvt.py` → `outputs/hybrid_offshore_pvt.json` | yes (20 values) |

## 4. Main figures

| Figure | Content | Produced by | Data |
|:--|:--|:--|:--|
| 1 | Marine zoning and cultivation allocation | `figures.py` → `fig1` (needs Natural Earth: `python3 fetch_natural_earth.py`, then `spatial.py`) | `outputs/marine_space.json` |
| 2 | Grid Harvester schematics, turn geometry and harvesting energy | `manuscript_figures/figure2_bilingual.py` (artwork by P. Valdés Bacallao in `illustrations/`; Spanish edition sets Spanish labels over the English ones) | `outputs/harvester_turns.json`, `outputs/harvester_sargassum.json` |
| 3 | Harvesting energy and conventional/grid ratio | `manuscript_figures/bilingual_figures.py` | `outputs/harvester_sargassum.json`, `outputs/harvester_slurry.json` |
| 4 | Conceptual architecture (not data) | `manuscript_figures/figure4_concept.py` | — |
| 5 | Electricity supply and use, fuel portfolio, displaced demand | `figures.py` → `fig4` | `outputs/results.json` |
| 6 | Learning-lever decomposition | `manuscript_figures/bilingual_figures.py` | `outputs/levers.json` |
| 7 | Cost sensitivities | `manuscript_figures/bilingual_figures.py` | `outputs/robustness.json` |
| 8 | Monte Carlo cost, break-even and abatement | `manuscript_figures/bilingual_figures.py` | `outputs/monte_carlo_summary.json` |
| 9 | Unserved process heat, synthetic 8,760-hour test | `manuscript_figures/hybrid_figures.py` | `outputs/hourly_cst.json`, `outputs/hybrid_offshore_pvt.json` |
| 10 | Recovered N, P, K and deliverable quantities | `manuscript_figures/hybrid_figures.py` | `outputs/hybrid_offshore_pvt.json` → `nutrients` |
| 11 | Liquid-fuel surplus freed by electrification | `manuscript_figures/bilingual_figures.py` | `outputs/export_transition.json` |

The scripts in `manuscript_figures/` write English and Spanish versions of each figure
(`Figure_NN_EN.png`, `Figure_NN_ES.png`) at 400 dpi to `manuscript_figures/out/`. Plotted
values are transcribed from the outputs listed above, and `verify_manuscript.py` checks them.

## 5. Supplementary figures

| Figure | Content | Produced by |
|:--|:--|:--|
| S1 | Generation and marine-area sensitivity | `figures.py` → `s2` |
| S2 | Fossil break-even prices and Monte Carlo outcomes | `figures.py` → `s3` |
| S3 | Grid Harvester design and harvesting paths | `figures.py` → `s1` (needs `illustrations/`) |
| S4 | Export operating-contribution sensitivity | `export_figures.py` |
| S5 | First ten days of synthetic solar, wind and charging profiles | `manuscript_figures/hybrid_figures.py` |
| S6 | Unserved process heat under CST and storage choices | `manuscript_figures/hybrid_figures.py` |
| S7 | Co-location area bounds in a 540 MW wind array | geometric bound, Supplementary Note 19 |
| S8 | Solar-irradiance screen for the 2.25× collector field | `manuscript_figures/hybrid_figures.py` |

## 6. Offshore wind, PVT and hourly CST

Concentrated solar heat and offshore wind are treated as supply options for the refineries, not as
requirements. Two scripts, both called by `run_all.sh`, produce Table 6, Figures 9 and 10,
Supplementary Tables S26, S28, S29 and S31–S34 and Supplementary Figures S5, S6 and S8. Every assumption is
stated in the script and copied into its JSON output.

**`hybrid_offshore_pvt.py`** (Supplementary Notes 20 and 22) solves the drop-in case of
`transition_scenarios.py` with the FAO 2020 cap on domestically sold potassium (44,700 t K₂O,
37,107 t K) and two optional hooks in `optimise.solve`, which are inactive in every national case:

| Option | Assumption |
|:--|:--|
| Offshore wind | 540 MW stage; 2.986 TWh/year expected, 90% delivered when imposed; US$79/MWh (IRENA 2024 global weighted average) plus the onshore-wind integration adders; up to 20% of refinery heat through an electric heater; swept at US$40–135/MWh |
| PVT preheat | 0.20 km²; 1,850 kWh/m² global irradiance; 14% electrical and 19% thermal yield; US$300/m², 4% over 20 years, 1.5% O&M; at most 15% of refinery heat |
| Fertilizer chain | 1.4% N and 0.22% P in dry mass; recovered N, P and K from the linear program; FAO 2020 caps; 40, 15 and 8 GJ/t avoided manufacturing energy |

Modes: `base` (uncapped drop-in), `base_fao`, `wind`, `pvt`, `hybrid` (offshore wind and PVT
imposed) and `hybrid_optional` (both offered to the optimizer).

**`hourly_cst.py`** (Supplementary Notes 18 and 23) holds high-temperature refinery heat demand
(drop-in case for Table S26, hybrid case otherwise) constant at its annual mean and serves it hour by hour from a CST field and hot store, then from a share of
offshore wind through the heater. The weather year is constructed, not measured: seed 20261021,
clear-sky direct irradiance at 10.6° N, a two-state Markov sequence of clear and cloudy days scaled
to 1,400 kWh/m² expected annual direct irradiance (155 clear days and 1,501 kWh/m² realized),
cloudy days at 35% of clear sky, and offshore wind with Papagayo-jet seasonality. The hourly
irradiance profile is divided by its annual mean, so a field sized on annual energy collects exactly
the annual heat duty; the realized 1,501 kWh/m² sets only the timing, and field areas use the
nominal 1,400 kWh/m². The firming
upgrade (2.25× field, 96 h store) is costed at US$222.6/m² of collector and US$15, 30 or 60/kWh
of storage.

## 7. Repository layout

Scripts read and write `outputs/`. `illustrations/` holds the Grid Harvester artwork:
`Figure_2_composite_EN.png` feeds manuscript Figure 2, and the separate drawings read by
`figures.py` feed Figure 3 and Supplementary Figure S1 of the repository's own figure set. Keeping
`outputs/`, `illustrations/` and `data/` as folders, rather than flattening them into the root,
lets `run_all.sh` run unchanged.

## 8. Module roles

`spatial.py` marine GIS; `farm.py` zones, yields, nutrient supply and biomass cost;
`biorefinery.py` wet refinery routes per dry tonne; `preprocess.py` offshore pressing and
drying; `harvester_turns.py` turn losses; `harvester_slurry.py` hose and slurry energy;
`harvester_sargassum.py` harvesting energy at a *Sargassum* standing crop; `optimise.py`
demand, prices, end uses, vehicle premia and the linear program; `scenarios.py` cost and
finance levers; `transition_scenarios.py` headline cases; `lifecycle.py` screening lifecycle
layer; `analyses.py` results, levers, stress tests, Monte Carlo and exposure;
`export_transition.py` staged electrification, CST land and conditional exports;
`hybrid_offshore_pvt.py` offshore wind and PVT options and fertilizer chain; `hourly_cst.py`
synthetic 8,760-hour CST test;
`figures.py`, `export_figures.py`, `figstyle.py` repository figures; `manuscript_figures/`
bilingual manuscript figures; `source_data.py` Source Data workbooks;
`verify_manuscript.py` manuscript-versus-model check.
