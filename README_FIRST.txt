COSTA RICA RENEWABLE TRANSPORT AND REGIONAL EXPORTS — REVISED INTEGRATED SUBMISSION PACKAGE
20 October 2026

CONTENTS
 Documents/   — complete revised author manuscript and anonymized manuscript in DOCX and PDF,
                Supplementary Information with 20 tables in DOCX and PDF,
                draft cover letter in DOCX and PDF.
 Figures/     — Figures 1–9 and Supplementary Figures S1–S4 in PNG and PDF.
 Source_Data/ — 1000-draw uncertainty outputs, main scenario JSON, 2035–2050 export CSVs,
                Panama/Nicaragua margin cases, CST land CSV, figure plotting source data XLSX/JSON.
 Software/cr_model/ — full preserved and revised executable Python scientific model, parameters,
                heat and seaweed physics modules, original offshore GIS inputs and outputs.
 Software/RCA_Supplementary_Software_Anonymised.zip — same model with author names scrubbed
                from copyright notice for double-anonymous review, as in original submission.
 RCA_Submission_Checklist_Revised.txt — editorial and experimental author actions still required.
 CHANGELOG_Major_Revision.txt — major changes and evidence strength.

CENTRAL SCENARIO RESULTS
 Corrected 2025 gasoline 1425 million L and all-taxed diesel 1332 million L, with
 modeled assumed end-use diesel split; jet 369.8 million L PROVISIONAL, marine assumed.
 Modeled 2025-equivalent total: 29.97 TWh/y.
 Maximum vehicle electrification: $2.706bn/y, new electricity 11.889 TWh/y.
 Domestic liquid-fuel reserved / dedicated CST heat: $3.423bn/y, new electricity
 14.126 TWh/y, seaweed farms 2474 km2, CST heat 1.275 TWh/y.
 Fleet-compatible CST-heavy bridge: $4.988bn/y, new electricity 19.104 TWh/y.
 Domestic model is ANNUAL and does not establish refinery/vehicle operation hour by hour.
 Hypothetical 2035/2040/2045/2050 physically available surplus 0/1.39/2.58/3.44 TWh/y.
 Central 2050 export sensitivity: gross revenue ~$0.344bn/year, incremental contribution
 ~$0.049bn/year BEFORE recovery of all sunk capital. Market prices, buyer offtake
 capacity and transport charges are hypothetical, not real quotes.
 CST solar-only field area 3.61–7.23 km2 is SENSITIVITY, not a confirmed project site.
 Offshore CST is not demonstrated technically/financially.
 Seaweed aviation-range hydrocarbons are NOT certified. The 100% seaweed synthetic
 aviation-fuel route is a research hypothesis subject to rigorous ASTM qualification,
 fuel chemistry and engine safety; cost alone is NOT established as the only barrier.

IMPORTANT PRE-SUBMISSION ACTIONS
 The paper is an exploratory scientific study, not an approved commercial project or
 assurance of profitable fuel exports. It still needs each author's verification
 and approval, verified final 2025 aviation/marine/end-use fuel volumes, industrial
 parcels/DNI/offshore permitting study, hourly dispatch engineering, aviation fuel
 certification, and verified Panama/Nicaragua demand/offtake before any unconditional
 claims. See submission checklist. Model software was executed; Figures 1 marine map
 is inherited because local Natural Earth shapefiles must be re-fetched to redraw.

HOW TO REPRODUCE
 Follow Software/cr_model/README.md. The pre-generated spreadsheets are included.
 There is no need to have the optional artifact_tool library to reproduce scientific
 optimization runs, Monte Carlo draws, CSV outputs, and graphs; artifact_tool only
 regenerates the pre-made Excel per-figure files.
