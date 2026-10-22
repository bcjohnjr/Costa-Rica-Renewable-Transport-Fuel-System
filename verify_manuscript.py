"""Check the manuscript's model-derived numbers against a fresh run of the model.

Two independent checks:
  1. Registered values: every model-derived number in Tables 1-6, Figures 3 and 6-11 and the
     offshore-wind, PVT, hourly-CST and fertilizer results of Sections 3.9-3.11, transcribed below,
     against outputs/.
  2. Submitted documents (--docx): every number printed in Tables 1-6 of each manuscript file
     (English or Spanish edition) is read from the DOCX itself and checked against outputs/ at the
     precision printed.
Exits non-zero on any mismatch. --report writes the full log (environment, inputs, every check).

Usage:  python3 verify_manuscript.py [--outputs DIR] [--docx FILE ...] [--report FILE]
"""
import argparse, json, sys, re, zipfile, platform, datetime, hashlib
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("outputs_dir", nargs="?", default=None)
ap.add_argument("--outputs", default=None)
ap.add_argument("--docx", nargs="*", default=[])
ap.add_argument("--report", default=None)
args = ap.parse_args()
OUT = Path(args.outputs or args.outputs_dir or Path(__file__).resolve().parent / "outputs")
LOG = []
J = lambda f: json.load(open(OUT / f))
R, M = J("results.json"), J("monte_carlo_summary.json")
B = J("biorefinery_per_dry_tonne.json")["routes"]
LV, RB, H = J("levers.json"), J("robustness.json"), J("harvester_sargassum.json")
fails, n = [], 0


def chk(label, stated, model, dp):
    global n
    n += 1
    ok = round(model, dp) == round(stated, dp)
    LOG.append(f"{'ok  ' if ok else 'FAIL'} {label}: manuscript {stated}, model {model:.{dp + 2}f}")
    if not ok:
        fails.append(f"{label}: manuscript {stated}, model {model:.{dp + 2}f}")


# Table 2: refinery routes per dry tonne (fuels GJ/t; electricity and heat MWh/t consumed)
T2 = {"H": dict(hc_gj=5.31, jet_gj=2.13, ethanol_gj=0.00, ch4_gj=1.05, el_mwh=0.440, heat_mwh_th=0.448, cost_eur=214),
      "EH": dict(hc_gj=3.64, jet_gj=1.46, ethanol_gj=2.23, ch4_gj=0.73, el_mwh=0.361, heat_mwh_th=0.479, cost_eur=254),
      "A": dict(hc_gj=0.00, jet_gj=0.00, ethanol_gj=0.00, ch4_gj=4.80, el_mwh=0.111, heat_mwh_th=0.111, cost_eur=124)}
for route, vals in T2.items():
    for k, v in vals.items():
        chk(f"Table 2 {route} {k}", v, B[route][k], 0 if k == "cost_eur" else (3 if "mwh" in k else 2))
    for k, v in (("fert_n_kg", 8.4), ("fert_p_kg", 1.76), ("fert_k_kg", 36.8)):
        chk(f"Table 2 {route} {k}", v, B[route][k], 2)

# Table 3: principal cases
T3 = {"today": (4.76, 25.96, 0, 0.0, 91.8), "dropin": (3.42, 14.13, 2474, 18.7, 91.7),
      "bridge": (4.99, 19.10, 3875, 29.9, 87.7), "maxel": (2.71, 11.89, 1503, 10.9, 93.3)}
for c, (cost, el, km2, share, ghg) in T3.items():
    s = R[c]
    chk(f"Table 3 {c} cost", cost, s["total_cost_busd"], 2)
    chk(f"Table 3 {c} electricity", el, s["electricity_delivered_twh"], 2)
    chk(f"Table 3 {c} farm km2", km2, s["seaweed_total_km2"], 0)
    chk(f"Table 3 {c} seaweed share", share, s["seaweed_share_pct"], 1)
    chk(f"Table 3 {c} GHG reduction", ghg, s["lifecycle"]["reduction_pct"], 1)

# Table 4: capital by component (US$ bn)
T4 = {"dropin": [1.60, 4.50, 0.00, 1.20, 0.47, 0.00, 7.06, 5.20, 1.90, 1.15, 2.97, 26.05, 1.09],
      "bridge": [3.14, 4.50, 2.84, 2.80, 1.11, 0.00, 12.80, 8.33, 3.04, 2.15, 2.00, 42.71, 1.78],
      "maxel": [1.84, 3.31, 0.00, 0.42, 0.17, 0.00, 3.46, 3.03, 1.11, 0.67, 3.68, 17.70, 0.74]}
KEYS = ["PV", "Onshore wind", "CSP", "Electrolysers", "E-fuel synthesis", "DAC", "Seaweed farms", "Biorefineries",
        "Vessels", "Solar heat (thermal storage, CSP heat)", "Charging and grid"]
for c, vals in T4.items():
    b = R[c]["build"]
    for k, v in zip(KEYS, vals):
        chk(f"Table 4 {c} {k}", v, b["capex_busd"][k], 2)
    chk(f"Table 4 {c} total", vals[11], b["capex_total_busd"], 2)
    chk(f"Table 4 {c} per year", vals[12], b["capex_per_year_2027_2050_busd"], 2)

# Table 5 and Figure 8: Monte Carlo median (p5-p95)
T5 = {"dropin": ([3.63, 4.01, 4.48], [3.35, 3.69, 4.09], [1.51, 1.67, 1.86], [135, 177, 230], [89.5, 91.3, 92.8], 138, 1000),
      "bridge": ([5.89, 7.15, 9.14], [5.68, 6.91, 8.94], [2.45, 2.97, 3.80], [403, 553, 781], [84.6, 87.0, 89.1], 0, 911),
      "maxel": ([2.70, 2.98, 3.33], [2.40, 2.57, 2.81], [1.12, 1.24, 1.38], [32, 62, 100], [92.0, 93.4, 94.5], 1000, 1000)}
for c, (cost, en, bem, ab, lc, below, feas) in T5.items():
    m = M[c]
    for lab, st, key, dp in (("cost", cost, "cost_p5_p50_p95", 2), ("energy cost", en, "energy_cost_p5_p50_p95", 2),
                             ("break-even", bem, "breakeven_multiplier_p5_p50_p95", 2),
                             ("abatement", ab, "abatement_vs_2025_usd_t_p5_p50_p95", 0),
                             ("lifecycle", lc, "lifecycle_reduction_pct_p5_p50_p95", 1)):
        for v, mv in zip(st, m[key]):
            chk(f"Table 5 {c} {lab}", v, mv, dp)
    chk(f"Table 5 {c} below Oct 2026", below, m["n_below_oct2026"], 0)
    chk(f"Table 5 {c} feasible", feas, m["n_feasible"], 0)

# Figure 3: harvesting energy (MJ per 1.44-ha cycle) and conventional/grid ratio
F3 = {"bare hose": (28.9, 3.15), "faired 80%": (18.8, 4.82), "faired 85% (reference)": (18.2, 4.99),
      "faired 90%": (17.6, 5.17), "faired 85%, 30% slurry": (14.3, 6.34), "faired 85%, 1.20-m hose": (19.2, 4.74),
      "faired 85% + coarse chopping 0.2 kWh/t": (49.3, 1.84), "faired 85% + fine maceration 1.0 kWh/t": (173.7, 0.52)}
for k, (e, r) in F3.items():
    chk(f"Figure 3 {k} MJ", e, H["cases"][k]["total_MJ"], 1)
    chk(f"Figure 3 {k} ratio", r, H["cases"][k]["conv_to_grid_ratio"], 2)
chk("Figure 3 conventional MJ", 90.9, H["assumptions"]["conventional_cycle_energy_MJ"], 1)

# Figure 6: cumulative learning levers
for st, step in zip([4.758, 4.647, 4.503, 4.414, 4.197, 3.940, 3.939, 3.382, 3.374], LV["cumulative"]):
    chk(f"Figure 6 {step['key']}", st, step["cost"], 3)

# Figure 7: sensitivity deltas (US$ bn/y)
F7 = {"Integration and network adders ×2": 0.333, "No seaweed and PV limited to 4 GW": 0.887, "No seaweed": 0.338,
      "Seaweed yield 4 t ha⁻¹ yr⁻¹": 0.338, "Seaweed yield 6 t ha⁻¹ yr⁻¹": 0.304, "Finance at 7%": 0.576,
      "Vehicle premia high": 0.425, "No fertilizer credit": 0.085, "Offshore pressing before shipping": 0.043,
      "No electrofuels": 0.031, "Onshore wind limited to 1.5 GW": 0.024,
      "No depth cycling (natural nutrients or pumps)": 0.026, "Candidate marine area 5%": 0.049,
      "Whole-seaweed HTL yield 0.12": 0.013, "Conventional harvesting energy (ratio 1.0)": 0.010,
      "LNG/CNG vehicles allowed (with liquefaction and conversion)": -0.005,
      "Domestic aviation and shipping only": -0.957}
cases = {c["case"]: c["delta_busd"] for c in RB["cases"]}
for k, v in F7.items():
    if k not in cases:
        fails.append(f"Figure 7 case missing from model output: {k}")
    else:
        chk(f"Figure 7 {k}", v, cases[k], 3)

# Figure 11: physical export surplus (TWh/y)
E = J("export_transition.json")
stages = {int(s["year"]): s for s in E["stages"]} if isinstance(E["stages"], list) else {int(k): v for k, v in E["stages"].items()}
for yr, v in zip((2035, 2040, 2045, 2050), (0.00, 1.39, 2.58, 3.44)):
    s = stages[yr]
    chk(f"Figure 11 {yr} surplus", v, s["physically_freed_hydrocarbons_twh"], 2)

# Table 1: vehicle premium, US$ per MWh of fossil fuel replaced (computed by optimise.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import copy, optimise
T1 = [("ldv_gasoline", "bev", 12.1, 9.9), ("ldv_gasoline", "e85", 2.2, 1.8), ("ldv_gasoline", "e100", 3.3, 2.7),
      ("ldv_diesel", "bev", 12.4, 10.1), ("hdv", "bet", 29.2, 23.9), ("hdv", "ed95", 7.7, 6.3),
      ("hdv", "lng", 24.0, 19.7), ("offroad", "el", 29.2, 23.9), ("offroad", "cng", 24.0, 19.7)]
for r, col in ((0.07, 2), (0.04, 3)):
    prm = copy.deepcopy(optimise.base_params()); prm["veh"]["r"] = r
    vp = optimise.vehicle_premium_per_mwh(prm)
    for row in T1:
        chk(f"Table 1 {row[0]}|{row[1]} at {r:.0%}", row[col], vp[(row[0], row[1])], 1)

# Table 6, Sections 3.9-3.11 and Figures 9-10: offshore wind/PVT options and hourly CST test
HY, HC = J("hybrid_offshore_pvt.json"), J("hourly_cst.json")
HM, NU = HY["modes"], HY["nutrients"]
T6 = {"base_fao": (3.430, 0.000, 0.000, 1.275, 2474), "wind": (3.518, 2.687, 0.000, 0.807, 1987),
      "pvt": (3.426, 0.000, 0.070, 1.205, 2474), "hybrid": (3.514, 2.687, 0.070, 0.731, 1975)}
for c, vals in T6.items():
    for lab, v, key, dp in zip(("cost", "offshore", "PVT heat", "CST heat", "farm km2"), vals,
                               ("cost_busd", "offshore_twh", "pvt_heat_twh", "cst_heat_twh", "seaweed_km2"), (3, 3, 3, 3, 0)):
        chk(f"Table 6 {c} {lab}", v, HM[c][key], dp)
chk("Table 6 caption uncapped case", 3.42, HM["base"]["cost_busd"], 2)
chk("Section 3.9 PVT electricity TWh", 0.052, HM["hybrid"]["pvt_el_twh"], 3)
chk("Section 3.9 dry seaweed Mt", 2.20, HM["hybrid"]["seaweed_dry_mt"], 2)
chk("Section 3.9 optional offshore TWh", 0.0, HM["hybrid_optional"]["offshore_twh"], 3)
chk("Section 3.9 premium at US$79/MWh, US$ m", 84, (HM["hybrid"]["cost_busd"] - HM["base_fao"]["cost_busd"]) * 1e3, 0)
SW = {s["offshore_lcoe_usd_mwh"]: s["premium_vs_base_fao_musd"] for s in HY["hybrid_offshore_lcoe_sweep"]}
for lc, v in ((58, 28), (91, 116), (105, 154), (123, 202), (135, 234)):
    chk(f"Section 3.9/Note 20 premium at US${lc}/MWh, US$ m", v, SW[lc], 0)
ok44 = HY["hybrid_offshore_lcoe_sweep"][0]["premium_vs_base_fao_musd"] < 0      # full stage pays at US$40/MWh
n += 1; LOG.append(f"{'ok  ' if ok44 else 'FAIL'} Section 3.9 full offshore stage least-cost at low offshore cost")
if not ok44: fails.append("Section 3.9 full offshore stage not least-cost at US$40/MWh")
S32 = {(r["field_mult"], r["storage_h"], r["solar"]): r for r in HC["S32"]}
for key, pct, hrs in (((1.0, 48, 1.0), 11.4, 1152), ((1.0, 48, 0.75), 21.4, None), ((1.7, 72, 0.75), 1.7, None),
                      ((1.7, 72, 1.0), 0.0, None), ((2.0, 96, 1.0), 0.0, None), ((2.0, 96, 0.75), 0.0, None),
                      ((2.25, 96, 1.0), 0.0, None), ((2.25, 96, 0.75), 0.0, None)):
    chk(f"Figure 9a/Section 3.10 unserved % {key}", pct, S32[key]["unserved_pct"], 1)
    if hrs is not None:
        chk(f"Section 3.10 unserved hours {key}", hrs, S32[key]["unserved_hours"], 0)
chk("Section 4.1 share of hours with deficit %", 13.2, S32[(1.0, 48, 1.0)]["unserved_hours"] / 87.60, 1)
S29 = {(r["field_mult"], r["wind_share"]): r for r in HC["S29"]}
chk("Section 3.10 10% wind diversion %", 8.7, S29[(1.0, 0.1)]["unserved_pct"], 1)
chk("Section 3.10 20% wind diversion %", 6.1, S29[(1.0, 0.2)]["unserved_pct"], 1)
S26 = {(r["field_mult"], r["storage_h"]): r for r in HC["S26"]}
for key, v in (((1, 12), 25.6), ((1, 168), 7.8), ((1.5, 24), 4.3), ((1.5, 48), 0.8), ((2, 24), 0.0)):
    chk(f"Section 3.10 sizing sweep {key}", v, S26[key]["unserved_pct"], 1)
S33 = {r["dni"]: r for r in HC["S33"]}
chk("Section 3.10 annual-sized field km2", 3.77, S33[1400]["annual_km2"], 2)
chk("Section 3.10 2.25x field km2", 8.49, S33[1400]["upgraded_km2"], 2)
chk("Section 3.10 store GWh", 10.2, HC["store_gwh"], 1)
for r, tot, cap in zip(HC["S34"], (3.608, 3.619, 3.642), (1.203, 1.356, 1.662)):
    chk(f"Figure 9b/Section 3.10 annual total, store US${r['store_usd_kwh']}/kWh", tot, r["hybrid_with_upgrade_busd"], 3)
    chk(f"Section 3.10 upgrade capex, store US${r['store_usd_kwh']}/kWh", cap, r["capex_busd"], 3)
for k, v in (("N", 18455), ("P", 3867), ("K", 80850)):
    chk(f"Abstract/Figure 10 recovered {k} t", v, NU["recovered_t"][k], 0)
chk("Section 3.11 recovered K2O t (about 97,400)", 97400, NU["recovered_k2o_t"], -2)
chk("Section 3.11 deliverable K t", 37107, NU["deliverable_t"]["K"], 0)
half = {r["fraction"]: r for r in NU["S31"]}[0.5]
for k, v in (("N_t", 9227), ("P_t", 1933), ("K_t", 18554)):
    chk(f"Section 3.11/Figure 10b 50% acceptance {k}", v, half[k], 0)
chk("Section 3.11 avoided manufacturing energy PJ", 1.093, NU["S31"][-1]["energy_pj"], 3)
for k, v in (("N", 30758), ("P", 4833)):
    chk(f"Supplementary Note 22 assimilated {k} t", v, NU["assimilated_t"][k], 0)

n_registered, fails_registered = n, list(fails)


# ---- 2. Numbers read from the submitted manuscript files (Tables 1-6) ----------------------------
def model_tables():
    """Model values in the cell order of Tables 1-6 (first column = row labels, skipped)."""
    import copy as _c, optimise as _o
    t1 = []
    for row in T1:
        for r in (0.07, 0.04):
            prm = _c.deepcopy(_o.base_params()); prm["veh"]["r"] = r
            t1.append(_o.vehicle_premium_per_mwh(prm)[(row[0], row[1])])
    rt = ("H", "EH", "A")
    t2 = [B[k][f] for f in ("hc_gj", "jet_gj", "ethanol_gj", "ch4_gj", "el_mwh", "heat_mwh_th") for k in rt]
    t2 += [B[k][f] for k in rt for f in ("fert_n_kg", "fert_p_kg", "fert_k_kg")] + [B[k]["cost_eur"] for k in rt]
    t3 = [v for c in ("today", "dropin", "bridge", "maxel") for v in (
        R[c]["total_cost_busd"], R[c]["electricity_delivered_twh"], R[c]["seaweed_total_km2"],
        R[c]["seaweed_share_pct"], R[c]["lifecycle"]["reduction_pct"])]
    cs = ("dropin", "bridge", "maxel")
    t4 = [R[c]["build"]["capex_busd"][k] for k in KEYS for c in cs]
    t4 += [R[c]["build"]["capex_total_busd"] for c in cs] + [R[c]["build"]["capex_per_year_2027_2050_busd"] for c in cs]
    t5 = []
    for key in ("cost_p5_p50_p95", "energy_cost_p5_p50_p95", "breakeven_multiplier_p5_p50_p95",
                "abatement_vs_2025_usd_t_p5_p50_p95", "lifecycle_reduction_pct_p5_p50_p95"):
        for c in cs:
            p5, p50, p95 = M[c][key]; t5 += [p50, p5, p95]
    t5 += [M[c]["n_below_oct2026"] for c in cs] + [M[c]["n_feasible"] for c in cs]
    t6 = [HM[c][k] for c in ("base_fao", "wind", "pvt", "hybrid")
          for k in ("cost_busd", "offshore_twh", "pvt_heat_twh", "cst_heat_twh", "seaweed_km2")]
    return [t1, t2, t3, t4, t5, t6]


def docx_tables(path):
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    out = []
    for t in re.findall(r"<w:tbl>.*?</w:tbl>", x, re.S):
        rows = []
        for r in re.findall(r"<w:tr[ >].*?</w:tr>", t, re.S):
            rows.append(["".join(re.findall(r"<w:t[^>]*>([^<]*)", c)) for c in re.findall(r"<w:tc>.*?</w:tc>", r, re.S)])
        out.append(rows)
    return out


NUM = re.compile(r"\d+(?:[ \u00a0\u202f]\d{3})*(?:[.,]\d+)*")


def parse(tok, spanish):
    tok = re.sub(r"[ \u00a0\u202f]", "", tok)
    if spanish:
        whole, _, frac = tok.partition(",")
    else:
        tok = re.sub(r",(?=\d{3}\b)", "", tok); whole, _, frac = tok.partition(".")
    return float(whole + ("." + frac if frac else "")), len(frac)


n_docx = 0
for path in args.docx:
    tabs = docx_tables(path)
    spanish = "," in tabs[0][1][1]
    LOG.append(f"--- {Path(path).name} ({'Spanish' if spanish else 'English'} edition), {len(tabs)} tables")
    for ti, (tab, model) in enumerate(zip(tabs[:6], model_tables()), start=1):
        shown = [parse(m.group(0), spanish) for row in tab[1:] for cell in row[1:] for m in NUM.finditer(cell)]
        if len(shown) != len(model):
            fails.append(f"{Path(path).name} Table {ti}: {len(shown)} numbers printed, {len(model)} expected")
            continue
        for k, ((v, d), mv) in enumerate(zip(shown, model)):
            n_docx += 1
            ok = abs(mv - v) <= 0.5 * 10 ** -d + 1e-9
            LOG.append(f"{'ok  ' if ok else 'FAIL'} {Path(path).name} Table {ti} value {k + 1}: printed {v:.{d}f}, model {mv:.{d + 3}f}")
            if not ok:
                fails.append(f"{Path(path).name} Table {ti} value {k + 1}: printed {v:.{d}f}, model {mv:.{d + 3}f}")

summary = [f"{n_registered} registered manuscript values checked against {OUT}"]
if args.docx:
    summary.append(f"{n_docx} printed table values read from {len(args.docx)} manuscript file(s) and checked against {OUT}")
summary.append(f"{len(fails)} mismatch(es)" if fails else "All values match.")
if args.report:
    import numpy, scipy
    head = [f"Verification report — {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M UTC}",
            f"Python {platform.python_version()} on {platform.platform()}; numpy {numpy.__version__}; scipy {scipy.__version__}",
            f"Outputs: {OUT}"]
    for p in args.docx:
        head.append(f"Manuscript file: {Path(p).name} sha256 {hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]}")
    Path(args.report).write_text("\n".join(head + summary + [""] + LOG) + "\n", encoding="utf-8")
print("\n".join(summary))
if fails:
    print("\n".join("  " + f for f in fails))
    sys.exit(1)
