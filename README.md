# Costa Rica: transport-energy self-sufficiency, concentrated solar thermal (CST), and conditional regional exports

Revised research software and source data accompanying *Costa Rica transport-energy self-sufficiency using concentrated solar thermal seaweed biorefineries: electrification and conditional exports to Panama and Nicaragua*.

## Central conclusions and IMPORTANT qualifications

- The domestic 2025-equivalent oil-replacement energy balance totals **29.97 TWh/year** under the specified demands. Taxable gasoline of **1,425 million L** and diesel of **1,332 million L** are observed in the 2025 Ministry of Finance table. The diesel breakdown is **1,132 million L road + 200 million L nonroad**, an assumed allocation *within*, not additional to, 1,332. **369.8 million L jet** is a regulatory forecast rather than confirmed 2025 consumption, and **45 million L marine fuel** is an assumed value. This is not a formally audited complete transport-energy balance.
- The *domestic drop-in fuel* case uses **US$3.423 billion/year**, **14.126 TWh/year** new electricity, **2,473.906 km²** hypothetical offshore farms, **1.275 TWh/year** of dedicated CST process heat, and screening lifecycle reduction ~91.7%.
- The *maximum electrification* case uses **US$2.706 billion/year**, **11.889 TWh/year** new electricity, **1,502.666 km²** offshore farms, **0.743 TWh/year** dedicated CST heat; screening lifecycle reduction ~93.3%.
- The *fleet-compatible bridge* uses **US$4.988 billion/year**, **19.104 TWh/year** new electricity, **3,874.636 km²** farms, **2.391 TWh/year** thermal CST heat, plus **0.436 GW** separate CST-electric capacity.
- The 2025 **price comparator is selected-observation proxy**, not a verified annual average: **US$2.408 billion** versus **US$3.752 billion** at October 2026 shock prices. Under 1,000 Monte Carlo draws, **138/1,000** liquid-heavy drop-in cases beat the October 2026 bill; none beats the lower 2025 proxy. Maximum-electrification beats the October 2026 bill in 1000/1000 draws but never the 2025 proxy.
- **No 100% seaweed-based aviation fuel is asserted to be presently certified**. A suitable fully formulated 100% synthetic fuel is a prospective certification goal, subject to chemistry and engine/fuel approval under ASTM D4054/D7566/D1655 procedures. Seaweed feedstock is not intrinsically a categorical ban, but cost has not been demonstrated to be the exclusive historic barrier.
- A **frozen 2035 hydrocarbon production envelope** of **8.84 TWh/year** combined with staged heavy/off-road vehicle electrification releases **0/1.39/2.58/3.44 TWh/year** in **2035/2040/2045/2050** respectively. This is physical export potential *if existing domestic demand and production assumptions hold*, not a dynamic optimum or verified trade contracts.
- At 2050, **$100/MWh** assumed diesel sales, **$70/MWh** imputed variable production cost and **$14/MWh Panama; $18/MWh Nicaragua** transport cost, gross sales reach **~$0.344 billion** and incremental margin **~$0.049 billion** before sunk capital, taxes, new terminals and route-specific qualification. At **$115/MWh** variable production cost, the central case earns **no viable export sales**. Assumed offtake caps are *not* actual importer procurement figures.
- Land screen for high-temperature CST uses **DNI 1000–2000 kWh/m²/year, 42% net field-to-process efficiency and 42% solar aperture packing** and yields **7.23–3.61 km²** solar-field land for baseline thermal duty. **No identified or available land parcel** and no local DNI survey are provided. Offshore is speculative and carries unvalidated marine costs.

## Reproduction

Python 3.13 plus `pip install -r requirements-lock.txt` (scientific core). Then:

```bash
./run_all.sh
```

The complete run can take several minutes owing to three 1,000-draw uncertainty analyses. If marine Natural Earth layers are installed with `python3 fetch_natural_earth.py`, the marina geospatial Figure 1 can be rebuilt; otherwise the supplied Figure 1 corresponds to unchanged marine space and the model uses stored candidate-area data. Figure 1 is a screening map, not a lease parcel.

For **Excel Source Data** regeneration, the script `source_data.py` uses OpenAI's optional `artifact_tool` runtime library. If unavailable, numerical Source Data `*.json` and the already bundled editable `*.xlsx` files remain in `outputs/source_data/`. All central scientific computations, export spreadsheets in `*.csv`, and plotted PNG/PDF figures do not require this optional spreadsheet helper.

## Source map and code layout

- `optimise.py`: annual demand and multi-energy resource optimization (corrected road fuel baseline).
- `transition_scenarios.py`: independent headline solves (all refinery process heat assigned CST in learning cases).
- `export_transition.py`: *new* fixed-output 2035-2050 fleet electrification, CST solar-field land sensitivity and hypothetical Panama/Nicaragua exports; **all scenario parameters editable** in `ASSUMPTIONS`.
- `export_figures.py`: *new* Figures 8 and 9 and Supplementary Figure S4 and their Source Data.
- `analyses.py`, `lifecycle.py`, `scenarios.py`, `figures.py`, `figstyle.py`, `source_data.py`: uncertainty, emissions, sensitivity and model figures.
- `farm.py`, `spatial.py`, `biorefinery.py`, `preprocess.py`, `harvester_*.py`, `data/`, `illustrations/`: previously developed and preserved seaweed GIS, nutrient, wet biorefining and Grid Harvester models.
- `outputs/`: central cases, 1,000-run Monte Carlo CSVs and summary JSON, CST land screen, 2035-2050 export stages, sensitivity trade cases and original marine outputs.
- `paper_figures/`: 9 main paper figures and 4 supplementary figures as editable PNG/PDF plots.

## Source URLs

- 2025 actual *taxed* gasoline/diesel values: <https://www.hacienda.go.cr/docs/MH-DGPN-DG-INF-0005-2026_YER.pdf> Table 6.
- ARESEP national volumes: <https://aresep.go.cr/noticias/aresep-realizo-663-inspecciones-para-garantizar-calidad-de-combustibles/>
- Aviation fuel ASTM: <https://store.astm.org/d7566-25a.html> and <https://www.caafi.org/fuel-qualifications>
- Aviation fuel qualification / 100% SAF research: <https://www.easa.europa.eu/en/domains/environment/eaer/sustainable-aviation-fuels/what-are-sustainable-aviation-fuels>
- Solar potential *metadata*, not parcel-specific DNI: <https://datacatalog.worldbank.org/search/dataset/0042068/costa-rica-solar-irradiation-and-pv-power-potential-map>
- High-temperature CSP R&D: <https://research-hub.nlr.gov/en/publications/re-designing-the-csp-thermal-energy-storage-system-to-enable-high/>

**Study limitations:** Not hourly dispatch; uncertain offshore biology and marine impacts; no engineering FEED for CST; tax restoration and regional fuel demand not measured; no aviation 100% certification; excludes some lifecycle processes; static 2025-equivalent service demand rather than realistic fleet stock turnover dynamics. Scenario results are conditional, not feasibility certification or investment advice.

**Licence:** scientific code MIT; paper plots/source data CC BY 4.0; original licensed datasets remain subject to their respective licences.
