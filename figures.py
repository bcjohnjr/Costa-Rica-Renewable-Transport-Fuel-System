"""Figures 1-7 and Supplementary Figures S1-S3, with Source Data recorded for every plotted panel.

All results come from outputs/*.json written by analyses.py, transition_scenarios.py, harvester_turns.py and
harvester_sargassum.py. Figure 1 maps the farms of the drop-in-rule case.
"""
import csv
import json
import pickle
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, Rectangle, Polygon
import matplotlib.image as mpimg
import shapely

import optimise as o
import scenarios as sc
from farm import ZONES, FarmCost, farm_cost, METHODS
from biorefinery import routes
from spatial import PORTS, BBOX, STEP, COCOS, band_of
from figstyle import C, INK, INK2, MUTED, GRID, MM, save, hgrid, vgrid, record, dump_source

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
ILL = HERE / "illustrations"
R = json.load(open(OUT / "results.json"))
MC = json.load(open(OUT / "monte_carlo_summary.json"))
RB = json.load(open(OUT / "robustness.json"))
HS = json.load(open(OUT / "harvester_sargassum.json"))
HT = json.load(open(OUT / "harvester_turns.json"))
DROP = R["dropin"]
CASES = [("dropin", "Drop-in\nrule"), ("bridge", "Fleet-\ncompatible\nsolar bridge"), ("maxel", "Maximum\nelectri-\nfication")]
CCOL = {"dropin": C["blue"], "bridge": C["orange"], "maxel": C["aqua"]}
FOSSIL = DROP["fossil_cost_busd"]


def label_bars(ax, xs, vals, fmt="{:.2f}", dy=0.0, fs=5.8):
    for x, v in zip(xs, vals):
        ax.text(x, v + dy, fmt.format(v), ha="center", va="bottom", fontsize=fs, color=INK2)


# ------------------------------------------------------------------ Fig. 1 map
def fig1():
    L = pickle.load(open(OUT / "_layers.pkl", "rb"))
    lon, lat, cell = L["lon"], L["lat"], L["cell"]
    x0, y0, x1, y1 = BBOX
    nx, ny = int(round((x1 - x0) / STEP)), int(round((y1 - y0) / STEP))
    ix = np.floor((lon - x0) / STEP).astype(int); iy = np.floor((lat - y0) / STEP).astype(int)
    code = np.where(L["fish"] == "artisanal_0-6nm", 3, np.where(L["fish"] == "deep_low", 1, 2))
    code = np.where(L["mpa"], 4, code)
    code = np.where(L["ship"] & ~L["mpa"], 5, code)
    ok = (~L["ship"]) & (L["fish"] != "artisanal_0-6nm") & (~L["mpa"])
    band = band_of(L["dist_main"])
    zone = np.full(lon.shape, "", dtype=object)
    for reg, pre in (("Pacific", "pac"), ("Caribbean", "car")):
        for dep, suf in (("0-200", "shelf"), ("200-1000", "slope"), (">1000", "deep")):
            zone[(L["reg"] == reg) & (L["depth"] == dep)] = f"{pre}_{suf}"
    farm = np.zeros(lon.shape, bool)
    for zb, area in DROP["seaweed_by_zone_band_km2"].items():
        z, b = zb.split("|")
        idx = np.where(ok & (zone == z) & (band == b))[0]
        idx = idx[np.argsort(L["dist"][idx])]
        cum = np.cumsum(cell[idx])
        farm[idx[: np.searchsorted(cum, area) + 1]] = True
    code = np.where(farm, 6, code)
    grid = np.zeros((ny, nx)); grid[iy, ix] = code
    cols = ["#ffffff00", "#dbe8f3", "#f6d7a7", "#e98a4d", "#b9d8b0", "#d35f5f", C["green"]]
    fig = plt.figure(figsize=(180 * MM, 128 * MM))
    ax = fig.add_axes([0.05, 0.08, 0.60, 0.88])
    ax.imshow(np.ma.masked_equal(grid, 0), origin="lower", extent=(x0, x1, y0, y1), cmap=ListedColormap(cols),
              vmin=0, vmax=6, interpolation="nearest")
    for g in shapely.get_parts(L["land"]):
        if g.geom_type == "Polygon":
            xs, ys = g.exterior.xy
            ax.fill(xs, ys, color="#ece8de", ec="#8c8273", lw=0.4)
    g = L["cri_ll"]
    for p in shapely.get_parts(g):
        xs, ys = p.exterior.xy; ax.plot(xs, ys, color=INK2, lw=0.6)
    for n, (la, lo, r) in PORTS.items():
        ax.plot(lo, la, "o", ms=2.2, color=INK)
    ax.text(-84.25, 10.15, "COSTA RICA", fontsize=6.5, color=INK2, weight="bold", ha="center")
    ax.text(-87.06, 5.85, "Isla del Coco", fontsize=6, color=INK2, ha="center")
    ax.text(-88.9, 9.6, "PACIFIC OCEAN", fontsize=7, color=INK2)
    ax.text(-82.4, 11.6, "CARIBBEAN SEA", fontsize=7, color=INK2)
    ax.set_xlim(-91.2, -81.0); ax.set_ylim(2.6, 12.3)
    ax.set_aspect(1 / np.cos(np.radians(7.5)))
    ax.tick_params(labelsize=6)
    ax.set_xticks(range(-91, -80, 2)); ax.set_xticklabels([f"{-v}°W" for v in range(-91, -80, 2)])
    ax.set_yticks(range(3, 13, 2)); ax.set_yticklabels([f"{v}°N" for v in range(3, 13, 2)])
    ax.set_title("a  Marine space and the seaweed farms of the drop-in-rule case")
    leg = [Patch(fc=cols[6], label=f"Seaweed farms, drop-in-rule case ({DROP['seaweed_total_km2']:,.0f} km²)"),
           Patch(fc=cols[3], label="0–6 nm: artisanal fishing, estuaries (excluded)"),
           Patch(fc=cols[2], label="6 nm to 1,000 m: shelf and slope fisheries"),
           Patch(fc=cols[1], label="Deep water >1,000 m: pelagic longline"),
           Patch(fc=cols[4], label="Isla del Coco NP and Seamounts MMA (excluded)"),
           Patch(fc=cols[5], label="Shipping lanes and port approaches (excluded)"),
           plt.Line2D([], [], marker="o", ls="", color=INK, ms=2.5, label="Ports")]
    ax.legend(handles=leg, loc="lower left", fontsize=5.6, frameon=True, framealpha=0.9, edgecolor="none")
    # panel b: free area by zone and distance band
    ax2 = fig.add_axes([0.73, 0.55, 0.25, 0.38])
    zs = ["pac_shelf", "pac_slope", "pac_deep", "car_shelf", "car_slope", "car_deep"]
    lab = ["Pacific shelf", "Pacific slope", "Pacific deep", "Caribbean shelf", "Caribbean slope", "Caribbean deep"]
    bands = ["0-50", "50-100", "100-200", "200-370"]
    bc = [C["blue"], C["aqua"], C["yellow"], C["magenta"]]
    left = np.zeros(len(zs)); rows = []
    for b, cc in zip(bands, bc):
        v = np.array([ZONES[z].area_km2.get(b, 0) / 1000 for z in zs])
        ax2.barh(range(len(zs)), v, left=left, color=cc, height=0.65, ec="white", lw=0.6, label=f"{b} km")
        left += v
        rows += [(lz, b, vv * 1000) for lz, vv in zip(lab, v)]
    for i, t in enumerate(left):
        ax2.text(t + 3, i, f"{t:,.1f}", va="center", fontsize=5.6, color=INK2)
    ax2.set_xlim(0, 210)
    ax2.set_yticks(range(len(zs))); ax2.set_yticklabels(lab, fontsize=6); ax2.invert_yaxis()
    ax2.set_xlabel("Free area (thousand km²)", fontsize=6); ax2.tick_params(labelsize=6)
    ax2.legend(fontsize=5.5, title="Distance to mainland", title_fontsize=5.5, loc="lower right")
    ax2.set_title("b  Candidate area by zone")
    record("Figure_1", "b_free_area", ["zone", "distance band", "free area km2"], rows,
           "Outside shipping lanes and ports, beyond 6 nm, outside the Isla del Coco protected areas.")
    ax3 = fig.add_axes([0.73, 0.10, 0.25, 0.30])
    zb = DROP["seaweed_by_zone_band_km2"]
    agg = {}
    for k, v in zb.items():
        z = k.split("|")[0]; agg[z] = agg.get(z, 0) + v
    names = [lab[zs.index(z)] for z in zs if z in agg]; vals = [agg[z] for z in zs if z in agg]
    ax3.barh(range(len(vals)), vals, color=C["green"], height=0.6)
    for i, v in enumerate(vals):
        ax3.text(v + 30, i, f"{v:,.0f}", va="center", fontsize=6, color=INK2)
    ax3.set_yticks(range(len(vals))); ax3.set_yticklabels(names, fontsize=6); ax3.invert_yaxis()
    ax3.set_xlim(0, max(vals) * 1.35); ax3.set_xlabel("Farm area (km²)", fontsize=6); ax3.tick_params(labelsize=6)
    ax3.set_title("c  Farms used")
    record("Figure_1", "c_farms", ["zone", "farm area km2"], list(zip(names, vals)))
    save(fig, "Figure_1"); dump_source("Figure_1")


# ------------------------------------------------------------------ Fig. 2 seaweed chain
def fig2():
    fig = plt.figure(figsize=(180 * MM, 125 * MM))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.0], wspace=0.35, left=0.08, right=0.80, top=0.94, bottom=0.50)
    gs2 = fig.add_gridspec(1, 1, left=0.24, right=0.80, top=0.36, bottom=0.08)
    axs = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs2[0, 0])]
    c = FarmCost()
    ax = axs[0]
    zs = [("pac_shelf", "Pacific shelf"), ("pac_slope", "Pacific slope"), ("pac_deep", "Pacific deep"),
          ("car_shelf", "Caribbean shelf"), ("car_deep", "Caribbean deep")]
    meth = [("natural", "Natural supply", C["aqua"]), ("depth_cycling", "Depth cycling", C["green"]),
            ("solar_pipe", "Solar-pumped pipe", C["yellow"]), ("wave_pump", "Wave pump", C["orange"]),
            ("salt_fountain", "Salt fountain", C["violet"])]
    w = 0.16; rows = []
    for j, (m, ml, cc) in enumerate(meth):
        vals = []
        for z, zl in zs:
            r = farm_cost(z, list(ZONES[z].area_km2)[0], c, m)
            v = r["total_eur_t"] if np.isfinite(r["total_eur_t"]) else np.nan
            vals.append(v); rows.append((zl, ml, v, r["yield_t_ha"]))
        ax.bar(np.arange(len(zs)) + (j - 2) * w, vals, w * 0.92, color=cc, label=ml)
    ax.set_yscale("log"); ax.set_ylim(300, 1e5)
    ax.set_xticks(range(len(zs))); ax.set_xticklabels([z[1].replace(" ", "\n") for z in zs], fontsize=5.8)
    ax.set_ylabel("Biomass cost at port (US$ per dry t)"); vgrid(ax)
    ax.legend(fontsize=5.5, ncol=2, loc="upper left")
    ax.set_title("a  Biomass cost by nutrient supply")
    record("Figure_2", "a_biomass_cost", ["zone", "nutrient method", "USD per dry t", "effective yield t/ha/yr"], rows,
           "Nearest distance band; natural supply yields only the naturally supplied share; NaN = not applicable.")
    ax = axs[1]
    RT = routes()
    keys = [("EH", "Ethanol + HTL"), ("H", "Whole HTL"), ("A", "Digestion")]
    comp = [("hc_gj", "Diesel/jet", C["blue"], 1), ("ethanol_gj", "Ethanol", C["yellow"], 1), ("ch4_gj", "Biomethane", C["aqua"], 1),
            ("fert_energy_gj", "Fertilizer energy avoided", C["magenta"], 1),
            ("el_mwh", "Electricity", C["orange"], -3.6), ("heat_mwh_th", "Process heat", C["red"], -3.6)]
    rows = []
    for i, (k, kl) in enumerate(keys):
        pos = neg = 0.0
        for f, fl, cc, sgn in comp:
            v = RT[k][f] * abs(sgn) * (1 if sgn > 0 else -1)
            if v >= 0:
                ax.bar(i, v, 0.6, bottom=pos, color=cc, ec="white", lw=0.6); pos += v
            else:
                ax.bar(i, v, 0.6, bottom=neg, color=cc, ec="white", lw=0.6); neg += v
            rows.append((kl, fl, v))
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xticks(range(3)); ax.set_xticklabels([k[1] for k in keys], fontsize=6)
    ax.set_ylabel("GJ per dry t of Sargassum"); vgrid(ax)
    ax.legend(handles=[Patch(fc=cc, label=fl) for _, fl, cc, _ in comp], fontsize=5.5, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    ax.set_ylim(-4.5, 9); ax.set_xticklabels(["Ethanol\n+ HTL", "Whole\nHTL", "Digestion"], fontsize=6)
    ax.set_title("b  Wet biorefinery balances")
    record("Figure_2", "b_refinery", ["route", "flow", "GJ per dry t (inputs negative)"], rows)
    ax = axs[2]
    t = o.base_params(); lc = sc.cheaper_capital(o.base_params())
    def heat_costs(p):
        pv = p["pv"]["lcoe"]; h = p["heat"]; a = p["adder"]
        grid = pv + a["pv_day"] + a["network_direct"]
        return [("PV-charged thermal storage", pv / h["pvtes_eff"] + h["pvtes_cost"]),
                ("CSP steam with storage", h["csp_heat_cost"]),
                ("Heat pump (low-temperature)", grid / h["hp_cop"]),
                ("Electric boiler (grid)", grid / h["eboiler_eff"])]
    ht, hl = heat_costs(t), heat_costs(lc)
    y = np.arange(len(ht))
    ax.barh(y + 0.19, [v for _, v in ht], 0.36, color=C["orange"], label="7% finance")
    ax.barh(y - 0.19, [v for _, v in hl], 0.36, color=C["blue"], label="4% finance")
    for i in range(len(ht)):
        ax.text(ht[i][1] + 2, i + 0.19, f"{ht[i][1]:.0f}", va="center", fontsize=5.8, color=INK2)
        ax.text(hl[i][1] + 2, i - 0.19, f"{hl[i][1]:.0f}", va="center", fontsize=5.8, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([n for n, _ in ht], fontsize=6); ax.invert_yaxis()
    ax.set_xlim(0, 130); ax.set_xlabel("Cost of delivered heat (US$ per MWh_th)"); hgrid(ax)
    ax.legend(fontsize=5.5, loc="upper right")
    ax.set_title("c  Solar and electric process heat")
    record("Figure_2", "c_heat", ["source", "USD/MWh_th at 7%", "USD/MWh_th at 4%"], [(a, b, d) for (a, b), (_, d) in zip(ht, hl)],
           "Heat pumps limited to 60% of refinery heat (low-temperature duties).")
    save(fig, "Figure_2"); dump_source("Figure_2")


# ------------------------------------------------------------------ Fig. 3 Grid Harvester
def _spiral(ax):
    """Conventional 10-m vessel harvesting a 240 m x 60 m (1.44-ha) field in a spiral with ten 90-degree turns."""
    ax.add_patch(Rectangle((0, 0), 240, 60, fc="#eef5e9", ec=INK2, lw=0.6))
    pts = [(5, 5), (235, 5), (235, 55), (5, 55), (5, 15), (225, 15), (225, 45), (15, 45), (15, 25), (215, 25), (215, 35), (25, 35)]
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=INK, lw=0.9)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        ax.annotate("", xy=((x0 + x1) / 2 + 0.01 * (x1 - x0), (y0 + y1) / 2 + 0.01 * (y1 - y0)), xytext=((x0 + x1) / 2, (y0 + y1) / 2),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.6, mutation_scale=6))
    r = 10.0                                            # turning radius = vessel width; corner of (1 - pi/4) r^2 missed
    for cx, cy, sx, sy in ((0, 0, 1, 1), (240, 0, -1, 1), (240, 60, -1, -1), (0, 60, 1, -1)):
        t = np.linspace(0, np.pi / 2, 20)
        arc = [(cx + sx * (r - r * np.cos(a)), cy + sy * (r - r * np.sin(a))) for a in t]
        ax.add_patch(Polygon([(cx, cy)] + [(cx + sx * r, cy)] + arc[::-1][1:] + [(cx, cy + sy * r)], closed=True, fc=C["red"], ec="none", alpha=0.8))
    ax.annotate("", xy=(0, -7), xytext=(240, -7), arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.5))
    ax.text(120, -13, "240 m", ha="center", va="top", fontsize=5.8, color=INK2)
    ax.annotate("", xy=(-7, 0), xytext=(-7, 60), arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.5))
    ax.text(-11, 30, "60 m", ha="right", va="center", fontsize=5.8, color=INK2, rotation=90)
    ax.text(250, 62, "corners missed\nin 90° turns", fontsize=5.6, color=C["red"], va="top")
    ax.text(250, 32, f"{HT['conventional']['missed_pct']:.2f}% of the\ncycle area\nmissed", fontsize=5.6, color=INK2, va="top")
    ax.set_xlim(-25, 300); ax.set_ylim(-22, 68); ax.set_aspect("equal"); ax.axis("off")


def fig3():
    fig = plt.figure(figsize=(180 * MM, 165 * MM))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 0.62, 0.95], hspace=0.18, wspace=0.06, left=0.08, right=0.98, top=0.97, bottom=0.07)
    for pos, f, t in ((gs[0, 0], "grid_harvester_side.jpg", "a  Side view"), (gs[0, 1], "grid_harvester_top.jpg", "b  Top view and head path")):
        ax = fig.add_subplot(pos); ax.imshow(mpimg.imread(ILL / f)); ax.axis("off"); ax.set_title(t)
    ax = fig.add_subplot(gs[1, 0]); _spiral(ax); ax.set_title("c  Conventional vessel: spiral path")
    ax = fig.add_subplot(gs[1, 1]); ax.imshow(mpimg.imread(ILL / "grid_turn_stationary_head.png"), cmap="gray"); ax.axis("off")
    ax.set_title("d  Grid Harvester: stationary 180° turn")
    ax.text(0.0, -0.12, f"{HT['grid']['stationary']['missed_pct']:.2f}% of the cycle area missed without LMM; "
            f"{HT['grid']['stationary']['lmm_twice_pct']:.2f}% harvested twice with LMM", transform=ax.transAxes, fontsize=5.8, color=INK2)
    ax = fig.add_subplot(gs[2, :])
    cs = HS["cases"]
    bars = [("Conventional\nvessel", HS["assumptions"]["conventional_cycle_energy_MJ"], MUTED),
            ("Grid Harvester,\nbare hose", cs["bare hose"]["total_MJ"], C["blue"]),
            ("Grid Harvester,\nfaired hose (85%)", cs["faired 85% (reference)"]["total_MJ"], C["blue"]),
            ("Faired hose +\ncoarse chopping", cs["faired 85% + coarse chopping 0.2 kWh/t"]["total_MJ"], C["yellow"]),
            ("Faired hose +\nfine maceration", cs["faired 85% + fine maceration 1.0 kWh/t"]["total_MJ"], C["red"])]
    x = np.arange(len(bars))
    ax.bar(x, [b[1] for b in bars], 0.6, color=[b[2] for b in bars])
    conv = bars[0][1]
    for i, (n, v, _) in enumerate(bars):
        txt = f"{v:.1f} MJ" if i == 0 else f"{v:.1f} MJ\n({(1 - v / conv) * 100:+.0f}%)".replace("(+", "(−").replace("(−-", "(+") if v < conv else f"{v:.1f} MJ\n(+{(v / conv - 1) * 100:.0f}%)"
        ax.text(i, v + 3, txt, ha="center", va="bottom", fontsize=6, color=INK2)
    ax.axhline(conv, color=MUTED, lw=0.6, ls="--")
    ax.set_xticks(x); ax.set_xticklabels([b[0] for b in bars], fontsize=6.2)
    ax.set_ylabel("Energy per 1.44-ha harvest cycle (MJ)"); ax.set_ylim(0, 215); vgrid(ax)
    ax.set_title("e  Harvesting energy at a Sargassum standing crop of 3 kg m⁻² (43.2 t wet per cycle)")
    record("Figure_3", "c_d_turn_losses", ["configuration", "missed % of cycle", "harvested twice % (with LMM)"],
           [("Conventional vessel, ten 90° turns", HT["conventional"]["missed_pct"], 0.0),
            ("Grid Harvester, stationary 180° turns", HT["grid"]["stationary"]["missed_pct"], HT["grid"]["stationary"]["lmm_twice_pct"]),
            ("Grid Harvester, turning while moving forward", HT["grid"]["forward"]["missed_pct"], HT["grid"]["forward"]["lmm_twice_pct"])])
    record("Figure_3", "e_energy", ["configuration", "MJ per 1.44-ha cycle", "change vs conventional %", "saving kWh per dry t"],
           [(b[0].replace("\n", " "), b[1], (b[1] / conv - 1) * 100,
             (conv - b[1]) / HS["assumptions"]["dry_t_per_cycle"] / 3.6) for b in bars],
           "1.44-ha cycle, 3 kg m-2 standing wet Sargassum (4.32 t dry); hose resized to 1.0 m/s at 10% slurry; "
           "coarse chopping 0.2 kWh and fine maceration 1.0 kWh per wet tonne.")
    save(fig, "Figure_3"); dump_source("Figure_3")


# ------------------------------------------------------------------ Fig. 4 drop-in-rule system
def fig4():
    s = DROP
    fig, axs = plt.subplots(1, 3, figsize=(180 * MM, 66 * MM), gridspec_kw={"width_ratios": [0.9, 1.0, 1.35]})
    ax = axs[0]
    use = [("Vehicles", s["vehicle_electricity_twh"], C["red"]), ("Biorefineries", s["electricity_refineries_twh"], C["green"]),
           ("Thermal storage\n(refinery heat)", s["pv_for_heat_twh"], C["magenta"]), ("Electrofuels", s["electricity_for_efuels_twh"], C["violet"]),
           ("Direct air capture", s["electricity_for_dac_twh"], C["aqua"])]
    sup = [("PV", s["generation_twh"]["PV"], C["yellow"]), ("Onshore wind", s["generation_twh"]["Onshore wind"], C["blue"]),
           ("Geothermal", s["generation_twh"]["Geothermal"], C["orange"]), ("CSP", s["generation_twh"]["CSP"], C["red"])]
    for i, (lst, lab) in enumerate(((sup, "Supply"), (use, "Use"))):
        left = 0
        for n, v, cc in lst:
            if v > 1e-3:
                ax.barh(i, v, 0.55, left=left, color=cc, ec="white", lw=0.6)
                if v > 2.5:
                    ax.text(left + v / 2, i, f"{v:.1f}", ha="center", va="center", fontsize=5.6, color="white")
                left += v
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Supply", "Use"]); ax.invert_yaxis()
    ax.set_xlabel("New electricity (TWh yr⁻¹)"); hgrid(ax); ax.set_ylim(4.3, -0.5)
    hs = [Patch(fc=cc, label=f"{n.replace(chr(10), ' ')} {v:.1f}") for n, v, cc in sup + use if v > 1e-3]
    ax.legend(handles=hs, fontsize=5.2, loc="lower left", ncol=1, handlelength=1.0, borderaxespad=0.2)
    ax.set_title("a  New electricity")
    record("Figure_4", "a_electricity", ["side", "item", "TWh/yr"], [("supply", n, v) for n, v, _ in sup] + [("use", n.replace("\n", " "), v) for n, v, _ in use])
    ax = axs[1]
    f = s["fuels_twh"]
    fl = [("Seaweed HTL diesel/jet", f["seaweed HTL diesel/jet"], C["green"]), ("Seaweed biomethane", f["seaweed biomethane (net of fleet)"], C["aqua"]),
          ("Residue Fischer–Tropsch", f["residue_FT"], C["orange"]), ("Waste-lipid HVO", f["HEFA_waste_lipids"], C["magenta"]),
          ("Molasses ethanol", f["crop_ethanol_existing"], C["yellow"]), ("e-Fischer–Tropsch", f["eFT_liquids"], C["violet"]),
          ("Waste biomethane", f["waste_biomethane"], C["red"])]
    fl2 = [x for x in fl if x[1] > 1e-3]
    ax.barh(range(len(fl2)), [v for _, v, _ in fl2], 0.6, color=[cc for _, _, cc in fl2])
    for i, (n, v, cc) in enumerate(fl2):
        ax.text(v + 0.08, i, f"{v:.2f}", va="center", fontsize=5.8, color=INK2)
    ax.set_yticks(range(len(fl2))); ax.set_yticklabels([n for n, _, _ in fl2], fontsize=6); ax.invert_yaxis()
    ax.set_xlim(0, 6.2); ax.set_xlabel("Fuel supply (TWh yr⁻¹)"); hgrid(ax)
    ax.set_title("b  Renewable fuels")
    record("Figure_4", "b_fuels", ["fuel", "TWh/yr"], [(n, v) for n, v, _ in fl])
    ax = axs[2]
    seg = [("ldv_gasoline", "Petrol cars"), ("ldv_diesel", "Diesel light vehicles"), ("hdv", "Trucks and buses"),
           ("offroad", "Off-road machinery"), ("aviation", "Aviation"), ("shipping", "Shipping")]
    car = [("el_direct", "Battery-electric", C["blue"]), ("dropin", "Drop-in diesel", C["green"]), ("jet", "Jet", C["aqua"]),
           ("ethanol", "Ethanol (ED95)", C["yellow"]), ("e85", "E85", C["orange"]), ("methanol", "Methanol", C["violet"])]
    rows = []
    for i, (sg, sl) in enumerate(seg):
        left = 0
        for cr, cl, cc in car:
            v = sum(val for k, val in s["end_use_twh"].items() if k.split("|")[0] == sg and o.OPTIONS[sg][k.split("|")[1]][0] == cr)
            if v > 1e-3:
                ax.barh(i, v, 0.62, left=left, color=cc, ec="white", lw=0.6); left += v
            rows.append((sl, cl, v))
        if sg == "shipping" and s["wind_assist_twh_saved"] > 0:
            ax.barh(i, s["wind_assist_twh_saved"], 0.62, left=left, color="white", ec=MUTED, hatch="////", lw=0.5)
            rows.append((sl, "wind assistance (saved)", s["wind_assist_twh_saved"]))
        ax.text(s["demand_twh"][sg] + 0.15, i, f"{s['demand_twh'][sg]:.1f}", va="center", fontsize=5.8, color=INK2)
    ax.set_yticks(range(len(seg))); ax.set_yticklabels([x[1] for x in seg], fontsize=6.2); ax.invert_yaxis()
    ax.set_xlabel("Fossil energy replaced (TWh yr⁻¹)"); hgrid(ax); ax.set_xlim(0, 17)
    ax.legend(handles=[Patch(fc=cc, label=cl) for cr, cl, cc in car if cr not in ("e85",)], fontsize=5.2, loc="lower right", handlelength=1.0)
    ax.set_title("c  Transport segments")
    record("Figure_4", "c_segments", ["segment", "carrier", "TWh fossil replaced"], rows)
    fig.tight_layout(w_pad=1.0)
    save(fig, "Figure_4"); dump_source("Figure_4")


# ------------------------------------------------------------------ Fig. 5 cost and infrastructure
def fig5():
    fig, axs = plt.subplots(1, 3, figsize=(180 * MM, 66 * MM), gridspec_kw={"width_ratios": [1.25, 1.0, 1.0]})
    x = np.arange(len(CASES))
    ax = axs[0]
    en = [R[k]["energy_cost_busd"] for k, _ in CASES]; vp = [R[k]["vehicle_premium_busd"] for k, _ in CASES]
    ax.bar(x, en, 0.55, color=[CCOL[k] for k, _ in CASES], label="Energy")
    ax.bar(x, vp, 0.55, bottom=en, color="white", ec=[CCOL[k] for k, _ in CASES], hatch="////", lw=0.6, label="Vehicle premia")
    lo = [MC[k]["cost_p5_p50_p95"][0] for k, _ in CASES]; md = [MC[k]["cost_p5_p50_p95"][1] for k, _ in CASES]; hi = [MC[k]["cost_p5_p50_p95"][2] for k, _ in CASES]
    ax.errorbar(x + 0.36, md, yerr=[np.array(md) - lo, np.array(hi) - md], fmt="o", ms=2.5, color=INK, lw=0.7, capsize=2,
                label="Monte Carlo median, 5th–95th pct.")
    for i, k in enumerate(k for k, _ in CASES):
        ax.text(i, R[k]["total_cost_busd"] + 0.1, f"{R[k]['total_cost_busd']:.2f}", ha="center", fontsize=6, color=INK)
    ax.axhline(FOSSIL["oct2026"], color=C["red"], lw=0.8, ls="--"); ax.text(3.45, FOSSIL["oct2026"], "Fossil\nOct 2026", fontsize=5.4, color=C["red"], ha="right", va="center", bbox=dict(fc="white", ec="none", pad=0.5))
    ax.axhline(FOSSIL["avg2025"], color=C["red"], lw=0.8, ls=":"); ax.text(3.45, FOSSIL["avg2025"], "Fossil\n2025", fontsize=5.4, color=C["red"], ha="right", va="center", bbox=dict(fc="white", ec="none", pad=0.5))
    ax.set_xticks(x); ax.set_xticklabels([l for _, l in CASES], fontsize=5.8); ax.set_xlim(-0.5, 3.5)
    ax.set_ylabel("Annual cost (US$ bn yr⁻¹)"); ax.set_ylim(0, 10); vgrid(ax)
    ax.legend(fontsize=5.4, loc="upper left")
    ax.set_title("a  Annual cost")
    record("Figure_5", "a_cost", ["case", "energy cost US$bn", "vehicle premia US$bn", "total US$bn", "MC p5", "MC median", "MC p95",
                                   "fossil Oct 2026 US$bn", "fossil 2025 US$bn"],
           [(l.replace("\n", " "), e, v, R[k]["total_cost_busd"], a, b, c, FOSSIL["oct2026"], FOSSIL["avg2025"])
            for (k, l), e, v, a, b, c in zip(CASES, en, vp, lo, md, hi)],
           "Monte Carlo: 1,000 common draws; solar-bridge statistics exclude the draws in which seaweed fails (infeasible).")
    ax = axs[1]
    ve = [R[k]["vehicle_electricity_twh"] for k, _ in CASES]; ne = [R[k]["electricity_delivered_twh"] for k, _ in CASES]
    ax.bar(x - 0.18, ve, 0.34, color=[CCOL[k] for k, _ in CASES], label="Vehicle charging")
    ax.bar(x + 0.18, ne, 0.34, color="white", ec=[CCOL[k] for k, _ in CASES], hatch="////", lw=0.6, label="All new electricity")
    label_bars(ax, x - 0.18, ve, "{:.1f}", 0.3); label_bars(ax, x + 0.18, ne, "{:.1f}", 0.3)
    ax.set_xticks(x); ax.set_xticklabels([l for _, l in CASES], fontsize=5.8); ax.set_ylim(0, 27)
    ax.set_ylabel("Electricity (TWh yr⁻¹)"); vgrid(ax); ax.legend(fontsize=5.4, loc="upper left")
    ax.set_title("b  Electricity")
    record("Figure_5", "b_electricity", ["case", "vehicle electricity TWh/yr", "new electricity TWh/yr"],
           [(l.replace("\n", " "), a, b) for (k, l), a, b in zip(CASES, ve, ne)])
    ax = axs[2]
    cg = [R[k]["build"]["capex_busd"]["Charging and grid"] for k, _ in CASES]; km = [R[k]["seaweed_total_km2"] / 1000 for k, _ in CASES]
    ax.bar(x - 0.18, cg, 0.34, color=[CCOL[k] for k, _ in CASES], label="Charging and grid capital (US$ bn)")
    ax.bar(x + 0.18, km, 0.34, color="white", ec=[CCOL[k] for k, _ in CASES], hatch="....", lw=0.6, label="Seaweed farms (thousand km²)")
    label_bars(ax, x - 0.18, cg, "{:.2f}", 0.05); label_bars(ax, x + 0.18, km, "{:.2f}", 0.05)
    ax.set_xticks(x); ax.set_xticklabels([l for _, l in CASES], fontsize=5.8); ax.set_ylim(0, 5.6); vgrid(ax)
    ax.legend(fontsize=5.4, loc="upper left")
    ax.set_title("c  Grid and marine build")
    record("Figure_5", "c_infrastructure", ["case", "charging and grid capital US$bn", "seaweed farms km2"],
           [(l.replace("\n", " "), a, b * 1000) for (k, l), a, b in zip(CASES, cg, km)])
    fig.tight_layout(w_pad=1.2)
    save(fig, "Figure_5"); dump_source("Figure_5")


# ------------------------------------------------------------------ Fig. 6 lifecycle
def fig6():
    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 62 * MM), gridspec_kw={"width_ratios": [1.3, 1.0]})
    ax = axs[0]
    parts = [("Direct electric transport", C["blue"]), ("Seaweed fuels", C["green"]), ("Residue and waste biofuels", C["orange"]), ("Electrofuels", C["violet"])]
    fos = DROP["lifecycle"]["fossil_wtw_mtco2e"]
    ax.bar(0, fos, 0.55, color=MUTED); ax.text(0, fos + 0.15, f"{fos:.2f}", ha="center", fontsize=6)
    rows = [("Fossil comparator", "fossil", fos)]
    for i, (k, l) in enumerate(CASES, 1):
        lc = R[k]["lifecycle"]; b = 0
        for p, cc in parts:
            v = lc["parts_mtco2e"].get(p, 0.0)
            ax.bar(i, v, 0.55, bottom=b, color=cc, ec="white", lw=0.4); b += v
            rows.append((l.replace("\n", " "), p, v))
        lo_, hi_ = lc["lowcarbon_factor_sensitivity_mtco2e"]
        ax.errorbar(i, lc["lowcarbon_wtw_mtco2e"], yerr=[[lc["lowcarbon_wtw_mtco2e"] - lo_], [hi_ - lc["lowcarbon_wtw_mtco2e"]]], color=INK, lw=0.7, capsize=2)
        ax.text(i + 0.32, lc["lowcarbon_wtw_mtco2e"], f"{lc['lowcarbon_wtw_mtco2e']:.2f}", fontsize=6, va="center")
    ax.set_xticks(range(4)); ax.set_xticklabels(["Fossil\ntransport"] + [l for _, l in CASES], fontsize=5.8)
    ax.set_ylabel("Screening lifecycle emissions (Mt CO₂e yr⁻¹)"); vgrid(ax)
    ax.legend(handles=[Patch(fc=cc, label=p) for p, cc in parts], fontsize=5.5, loc="upper right")
    ax.set_title("a  Well-to-wheel emissions")
    record("Figure_6", "a_emissions", ["case", "component", "MtCO2e/yr"], rows, "Error bars: low and high lifecycle-factor sets.")
    ax = axs[1]
    red = [R[k]["lifecycle"]["reduction_pct"] for k, _ in CASES]
    rng = [R[k]["lifecycle"]["reduction_factor_sensitivity_pct"] for k, _ in CASES]
    x = np.arange(3)
    ax.bar(x, red, 0.55, color=[CCOL[k] for k, _ in CASES])
    ax.errorbar(x, red, yerr=[[r - a for r, (a, b) in zip(red, rng)], [b - r for r, (a, b) in zip(red, rng)]], fmt="none", color=INK, lw=0.7, capsize=2)
    for i, v in enumerate(red):
        ax.text(i + 0.32, v, f"{v:.1f}%", fontsize=6, va="center")
    ax.set_ylim(75, 100); ax.set_xticks(x); ax.set_xticklabels([l for _, l in CASES], fontsize=5.8)
    ax.set_ylabel("Reduction relative to fossil transport (%)"); vgrid(ax)
    ax.set_title("b  Reduction")
    record("Figure_6", "b_reduction", ["case", "reduction %", "low-factor %", "high-factor %"],
           [(l.replace("\n", " "), v, b, a) for (k, l), v, (a, b) in zip(CASES, red, rng)])
    fig.tight_layout(w_pad=1.5)
    save(fig, "Figure_6"); dump_source("Figure_6")


# ------------------------------------------------------------------ Fig. 7 seaweed and harvesting energy
def fig7():
    rb = {r["case"]: r for r in RB["cases"]}
    cases = [("Grid Harvester\n(ratio 2.68)", RB["central_busd"], RB["central_electricity_twh"], RB["central_seaweed_km2"], C["blue"]),
             ("Sargassum, no size\nreduction (4.99)",) + tuple(rb["Sargassum harvester without size reduction (ratio 4.99)"][k] for k in ("cost_busd", "electricity_twh", "seaweed_km2")) + (C["aqua"],),
             ("Sargassum, coarse\nchopping (1.84)",) + tuple(rb["Sargassum harvester with coarse chopping (ratio 1.84)"][k] for k in ("cost_busd", "electricity_twh", "seaweed_km2")) + (C["yellow"],),
             ("Conventional\nharvesting (1.0)",) + tuple(rb["Conventional harvesting energy (ratio 1.0)"][k] for k in ("cost_busd", "electricity_twh", "seaweed_km2")) + (MUTED,),
             ("No seaweed",) + tuple(rb["No seaweed"][k] for k in ("cost_busd", "electricity_twh", "seaweed_km2")) + (C["violet"],)]
    fig, axs = plt.subplots(1, 3, figsize=(180 * MM, 66 * MM))
    x = np.arange(len(cases))
    for ax, j, yl, t, fmt, top in ((axs[0], 1, "Annual cost (US$ bn yr⁻¹)", "a  Annual cost", "{:.3f}", 4.2),
                                   (axs[1], 2, "New electricity (TWh yr⁻¹)", "b  New electricity", "{:.1f}", 29),
                                   (axs[2], 3, "Seaweed farm area (km²)", "c  Seaweed farm area", "{:,.0f}", 3900)):
        v = [c[j] for c in cases]
        ax.bar(x, v, 0.6, color=[c[4] for c in cases])
        label_bars(ax, x, v, fmt, top * 0.01, fs=5.4)
        ax.set_xticks(x); ax.set_xticklabels([c[0] for c in cases], fontsize=5.2, rotation=35, ha="right", rotation_mode="anchor")
        ax.set_ylabel(yl); ax.set_ylim(0, top); vgrid(ax); ax.set_title(t)
    record("Figure_7", "a_b_c", ["case", "cost US$bn/yr", "new electricity TWh/yr", "seaweed km2"],
           [(c[0].replace("\n", " "), c[1], c[2], c[3]) for c in cases],
           "Drop-in-rule case; the conventional/grid harvesting-energy ratio scales the fleet harvesting-fuel term.")
    fig.tight_layout(w_pad=1.2)
    save(fig, "Figure_7"); dump_source("Figure_7")


# ------------------------------------------------------------------ Supplementary
def s1():
    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 62 * MM))
    for ax, f, t in zip(axs, ("grid_harvester_side.jpg", "grid_harvester_top.jpg"), ("a  Side view", "b  Top view and head path")):
        ax.imshow(mpimg.imread(ILL / f)); ax.axis("off"); ax.set_title(t)
    fig.tight_layout()
    save(fig, "Supplementary_Figure_S1")


def s2():
    noweed = [r for r in RB["cases"] if r["case"] == "No seaweed"][0]
    s = DROP
    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 62 * MM))
    ax = axs[0]
    labels = ["New\nelectricity\n(TWh yr⁻¹)", "PV\n(GW)", "Onshore\nwind (GW)", "Electro-\nlysers (GW)", "Direct air\ncapture\n(Mt CO₂ yr⁻¹)"]
    a = [s["electricity_delivered_twh"], s["capacity_gw"]["PV"], s["capacity_gw"]["Onshore wind"], s["electrolyser_gw"], s["co2_mt"]["DAC"]]
    b = [noweed["electricity_twh"], noweed["pv_gw"], noweed["wind_gw"], noweed["electrolyser_gw"], noweed["dac_mt"]]
    x = np.arange(len(a))
    ax.bar(x - 0.18, a, 0.34, color=C["green"], label="With native seaweed")
    ax.bar(x + 0.18, b, 0.34, color=C["violet"], label="Without seaweed")
    label_bars(ax, x - 0.18, a, "{:.1f}", 0.3, 5.4); label_bars(ax, x + 0.18, b, "{:.1f}", 0.3, 5.4)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=5.6); ax.legend(fontsize=6); vgrid(ax)
    ax.axhline(12.99, color=MUTED, lw=0.7, ls=":"); ax.text(4.4, 13.4, "2025 national\nelectricity demand", fontsize=5.4, ha="right", color=INK2)
    ax.set_title("a  Drop-in-rule case with and without seaweed")
    record("Supplementary_Figure_S2", "a_with_without", ["item", "with seaweed", "without seaweed"], list(zip([l.replace("\n", " ") for l in labels], a, b)))
    ax = axs[1]
    mc = list(csv.DictReader(open(OUT / "monte_carlo_dropin.csv")))
    yv = np.array([float(r["yield_t_ha"]) for r in mc]); km = np.array([float(r["seaweed_km2"]) for r in mc])
    al = np.array([r["seaweed_allowed"] == "True" for r in mc])
    ax.scatter(yv[al], km[al], s=4, color=C["green"], alpha=0.5, lw=0, label="Seaweed allowed")
    ax.scatter(yv[~al], km[~al], s=4, color=MUTED, alpha=0.6, lw=0, label="Seaweed chain fails")
    ax.set_xlabel("Sampled seaweed yield (t dry ha⁻¹ yr⁻¹)"); ax.set_ylabel("Seaweed farm area chosen (km²)")
    ax.legend(fontsize=5.6, markerscale=2); vgrid(ax)
    ax.set_title("b  Monte Carlo, drop-in rule: farm area against yield")
    record("Supplementary_Figure_S2", "b_mc_yield_area", ["yield t/ha/yr", "farm km2", "seaweed allowed"],
           [(float(a_), float(b_), bool(c_)) for a_, b_, c_ in zip(yv, km, al)])
    fig.tight_layout()
    save(fig, "Supplementary_Figure_S2"); dump_source("Supplementary_Figure_S2")


def s3():
    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 60 * MM))
    rows = []
    for k, l in CASES:
        mc = list(csv.DictReader(open(OUT / f"monte_carlo_{k}.csv")))
        m = np.array([float(r["breakeven_multiplier_vs_2025"]) for r in mc]); g = np.array([float(r["lifecycle_reduction_pct"]) for r in mc])
        axs[0].hist(m, bins=np.linspace(0.9, 5.4, 91), color=CCOL[k], alpha=0.75, ec="white", lw=0.3, label=l.replace("\n", " "))
        axs[1].hist(g, bins=np.linspace(82, 96, 57), color=CCOL[k], alpha=0.75, ec="white", lw=0.3, label=l.replace("\n", " "))
        rows += [(l.replace("\n", " "), int(r["draw"]), float(a), float(b)) for r, a, b in zip(mc, m, g)]
    axs[0].axvline(R["oct2026_vs_2025_ratio"], color=INK, lw=1.0)
    axs[0].text(R["oct2026_vs_2025_ratio"] + 0.05, axs[0].get_ylim()[1] * 0.92, f"Oct 2026 / 2025\nfossil bill ({R['oct2026_vs_2025_ratio']:.2f})", fontsize=5.6)
    axs[0].set_xlabel("Break-even multiplier on 2025 fossil prices"); axs[0].set_ylabel("Draws"); axs[0].set_title("a  Break-even fossil price")
    axs[0].legend(fontsize=5.5, loc="upper right")
    axs[1].set_xlabel("Lifecycle GHG reduction (%)"); axs[1].set_ylabel("Draws"); axs[1].set_title("b  Lifecycle reduction")
    record("Supplementary_Figure_S3", "draws", ["case", "draw", "break-even multiplier", "lifecycle reduction %"], rows,
           "Solar bridge: draws in which the seaweed chain fails are infeasible and omitted.")
    fig.tight_layout()
    save(fig, "Supplementary_Figure_S3"); dump_source("Supplementary_Figure_S3")


if __name__ == "__main__":
    import sys
    have_gis = (OUT / "_layers.pkl").exists()
    for f in ((fig1,) if have_gis else ()) + (fig2, fig3, fig4, fig5, fig6, fig7, s1, s2, s3):
        f(); print("done", f.__name__)
