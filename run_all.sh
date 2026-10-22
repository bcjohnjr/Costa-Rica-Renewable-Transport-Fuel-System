#!/usr/bin/env bash
# Reproduce every model number and figure in the manuscript, then check them (a few minutes).
# Run with:  bash run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p outputs
[[ -f outputs/marine_space.json ]] || cp marine_space.json outputs/   # stored marine-space areas
NE="${NATURAL_EARTH_DIR:-data/naturalearth}"
if [[ -f "$NE/10m_physical/ne_10m_land.shp" ]]; then
  python3 spatial.py > /dev/null          # marine GIS -> outputs/marine_space.json, outputs/_layers.pkl
else
  echo "Natural Earth not found: using stored outputs/marine_space.json (run fetch_natural_earth.py to draw Figure 1)"
fi
python3 farm.py
python3 biorefinery.py > /dev/null
python3 preprocess.py > /dev/null
python3 harvester_turns.py                 # turn losses
python3 harvester_slurry.py > /dev/null    # kelp reference: conventional/grid energy ratio 2.68
python3 harvester_sargassum.py             # Sargassum harvesting energy
python3 transition_scenarios.py            # the three headline cases
python3 analyses.py                        # results, levers, stress tests, E85, Monte Carlo
python3 export_transition.py               # staged electrification, CST land, conditional exports
python3 hybrid_offshore_pvt.py             # offshore wind and PVT options, fertilizer chain (Table 6, S28, S31)
python3 hourly_cst.py                      # synthetic 8,760-hour CST test (S26, S29, S32-S34)
python3 export_figures.py                  # repository Figures 8-9 and Supplementary Figure S4
# Repository figure set: panels that use the Grid Harvester artwork need illustrations/
python3 - <<'PY'
import figures as F
from pathlib import Path
names = (["fig1"] if (F.OUT / "_layers.pkl").exists() else []) + ["fig2", "fig3", "fig4", "fig5", "fig6", "fig7", "s1", "s2", "s3"]
for n in names:
    try:
        getattr(F, n)(); print("done", n)
    except FileNotFoundError as e:
        print(f"skipped {n}: missing {Path(e.filename).name}")
PY
python3 manuscript_figures/figure2_bilingual.py   # manuscript Figure 2, EN and ES (needs illustrations/)
python3 manuscript_figures/figure4_concept.py      # manuscript Figure 4, EN and ES
python3 manuscript_figures/bilingual_figures.py    # manuscript Figures 3, 6, 7, 8, 11, EN and ES
python3 manuscript_figures/hybrid_figures.py       # manuscript Figures 9, 10 and Supplementary Figures S5, S6, S8
if python3 -c 'import artifact_tool' >/dev/null 2>&1; then
  python3 source_data.py                  # editable Source Data XLSX (optional)
fi
# Manuscript values against outputs/; add the submitted DOCX files in manuscript/ to read their tables.
shopt -s nullglob; DOCX=(manuscript/*.docx)
python3 verify_manuscript.py --report outputs/verification_report.txt ${DOCX[@]+--docx "${DOCX[@]}"}
