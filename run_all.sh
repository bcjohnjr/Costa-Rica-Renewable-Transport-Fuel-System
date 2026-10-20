#!/usr/bin/env bash
# Reproduce every number, figure and Source Data workbook in the manuscript (about one minute).
set -euo pipefail
cd "$(dirname "$0")"
NE="${NATURAL_EARTH_DIR:-data/naturalearth}"
if [[ -f "$NE/10m_physical/ne_10m_land.shp" ]]; then
  python3 spatial.py > /dev/null          # marine GIS -> outputs/marine_space.json, outputs/_layers.pkl
else
  echo "Natural Earth not found: using the committed outputs/marine_space.json (run fetch_natural_earth.py to draw Figure 1)"
fi
python3 farm.py
python3 biorefinery.py > /dev/null
python3 preprocess.py > /dev/null
python3 harvester_turns.py                 # turn losses (Figure 3c,d)
python3 harvester_slurry.py > /dev/null    # kelp reference: conventional/grid energy ratio 2.68
python3 harvester_sargassum.py             # Sargassum harvesting energy (Figure 3e, harvester sensitivities)
python3 transition_scenarios.py            # the three headline cases
python3 analyses.py                        # results, bridge build-up, levers, stress tests, E85, Monte Carlo
python3 figures.py                         # Figures 1-7 and Supplementary Figures S1-S3 (Figure 1 needs Natural Earth)
python3 export_transition.py             # staged electrification, CST land and conditional Panama/Nicaragua trade
python3 export_figures.py                # Figures 8-9 and Supplementary Figure S4, with Source Data JSON
if python3 -c 'import artifact_tool' >/dev/null 2>&1; then
  python3 source_data.py                  # editable Source Data XLSX (artifact_tool, optional)
else
  echo 'artifact_tool not installed: XLSX regeneration skipped; JSON, CSV and committed XLSX remain available.'
fi
