"""All analyses reported in the manuscript. Every case keeps the full 2025 transport demand.

1. Headline cases: today's costs (7%, no Grid Harvester) and the three full-demand learning cases with the Grid
   Harvester (drop-in rule, fleet-compatible solar bridge, maximum electrification); fossil-bill comparison.
2. Build-up of the solar bridge from the drop-in rule, and the cost of each fleet-compatibility rule on its own.
3. Cost levers applied cumulatively from today's costs to the drop-in-rule case.
4. Monte Carlo (1,000 common draws applied to each headline case), with break-even fossil-price multipliers.
5. Price exposure (2025 average -> October 2026).
6. Stress tests and forced design options around the drop-in-rule case, including Grid Harvester energy ratios.
7. E85 sensitivities on the solar bridge (conversion allowance and minimum E85 share).
Writes outputs/results.json, outputs/levers.json, outputs/monte_carlo_<case>.csv, outputs/monte_carlo_summary.json,
outputs/robustness.json, outputs/robustness.csv and outputs/e85_sensitivity.json.
"""
import copy
import csv
import json
from pathlib import Path

import numpy as np

import optimise as o
import scenarios as sc
import transition_scenarios as ts
from lifecycle import sampled_lifecycle

OUT = Path(__file__).resolve().parent / "outputs"
RNG = np.random.default_rng(20261014)
CASES = ("dropin", "bridge", "maxel")
ZONES = ("pac_shelf", "pac_slope", "pac_deep", "car_shelf", "car_slope", "car_deep")


def brief(s):
    keys = ("total_cost_busd", "energy_cost_busd", "vehicle_premium_busd", "fossil_cost_busd", "electricity_delivered_twh",
            "generation_twh", "capacity_gw", "pv_for_heat_twh", "seaweed_total_km2", "seaweed_dry_mt", "seaweed_wet_mt",
            "seaweed_share_pct", "seaweed_hc_twh", "seaweed_jet_twh", "seaweed_cost_busd", "fuels_twh", "fertiliser_mt",
            "fertiliser_value_busd", "fertiliser_energy_avoided_pj", "co2_mt", "build", "end_use_twh", "heat_twh_th",
            "seaweed_by_zone_km2", "seaweed_by_zone_band_km2", "seaweed_by_route_km2", "seaweed_by_nutrient_method_km2",
            "seaweed_by_preprocess_km2", "seaweed_by_band_km2", "fossil_co2_mt", "demand_twh", "demand_total_twh",
            "electrolyser_gw", "electricity_vehicles_rail_twh", "electricity_for_efuels_twh", "electricity_for_dac_twh",
            "electricity_refineries_twh", "lifecycle", "marginal_usd_mwh", "abatement_usd_t", "seaweed_fleet_fuel_twh",
            "kite_saved_twh", "wind_assist_twh_saved", "bio_methanol_from_CH4_twh", "seaweed_refinery_heat_twh", "upwelling_pipes")
    b = {k: s[k] for k in keys}
    b["vehicle_electricity_twh"] = s["electricity_vehicles_rail_twh"]       # no rail demand is represented
    return b


def harvesters(s, standing_kg_m2=3.0, hours=4000):
    """Grid Harvester units: throughput scales with standing wet biomass (416.7 t/h at 12.5 kg/m2 for kelp)."""
    thr = 416.7 * standing_kg_m2 / 12.5
    return dict(throughput_t_wet_h=thr, hours_per_year=hours, units=s["seaweed_wet_mt"] * 1e6 / (thr * hours))


def vs_fossil(s):
    f = s["fossil_cost_busd"]
    return {"vs_oct2026_pct": (s["total_cost_busd"] / f["oct2026"] - 1) * 100,
            "vs_2025_pct": (s["total_cost_busd"] / f["avg2025"] - 1) * 100,
            "breakeven_multiplier_vs_2025": s["total_cost_busd"] / f["avg2025"],
            "energy_only_breakeven_vs_2025": s["energy_cost_busd"] / f["avg2025"]}


def headline():
    R = {}
    S = {"today": o.solve(sc.today())} | {k: o.solve(ts.case(k)) for k in CASES}
    for k, s in S.items():
        R[k] = brief(s)
        R[k]["harvesters"] = harvesters(s)
        R[k]["fossil_comparison"] = vs_fossil(s)
    # vehicle-premium range (central is inside the objective; low/high re-solved)
    zero = {"veh": {"car": 0, "van": 0, "truck": 0, "lng_truck": 0, "ed95_truck": 0, "e100_car": 0, "e85_car": 0}}
    high = {"veh": {"car": 3400, "van": 5700, "truck": 68000, "lng_truck": 45000, "ed95_truck": 15000, "e85_car": 1500}}
    for k in R:
        mk = (lambda ov: sc.build_case(learning=False, capital=False, demand=False, overrides=ov)) if k == "today" else (lambda ov, k=k: ts.case(k, ov))
        lo, hi = o.solve(mk(zero)), o.solve(mk(high))
        R[k]["vehicle_premium_range_total_busd"] = [lo["total_cost_busd"], hi["total_cost_busd"]]
        R[k]["vehicle_premium_range_busd"] = [lo["vehicle_premium_busd"], hi["vehicle_premium_busd"]]
    # price exposure: internationally priced inputs of the low-carbon system are commodity biofuels
    shock = {k: o.FOSSIL["oct2026"][k] / o.FOSSIL["avg2025"][k] - 1 for k in o.FOSSIL["oct2026"]}
    low = S["dropin"]; f = low["fuels_twh"]; p = ts.case("dropin")
    traded = (f["HEFA_waste_lipids"] * p["hefa"]["cost"] + f["crop_ethanol_existing"] * p["crop_etoh"]["cost"]) / 1000
    fs = low["fossil_cost_busd"]
    R["exposure"] = dict(fossil_swing_busd=fs["oct2026"] - fs["avg2025"], fossil_swing_pct=(fs["oct2026"] / fs["avg2025"] - 1) * 100,
                         lowcarbon_commodity_linked_busd=traded, lowcarbon_swing_busd=traded * shock["hdv"],
                         lowcarbon_swing_pct=traded * shock["hdv"] / low["total_cost_busd"] * 100, shock=shock)
    R["import_share_pct"] = 0.0
    R["oct2026_vs_2025_ratio"] = fs["oct2026"] / fs["avg2025"]
    # build-up of the solar bridge, and each fleet rule alone on the drop-in case
    steps = []
    for label, q in ts.bridge_steps():
        s = o.solve(q)
        steps.append(dict(step=label, cost_busd=s["total_cost_busd"], seaweed_km2=s["seaweed_total_km2"],
                          vehicle_electricity_twh=s["electricity_vehicles_rail_twh"], new_electricity_twh=s["electricity_delivered_twh"]))
    R["bridge_steps"] = steps
    single = []
    base = S["dropin"]["total_cost_busd"]
    for label, ov in (("Light-duty BEVs at most 70%", {"ldv_bev_max_share": 0.70}),
                      ("Heavy-duty battery vehicles at most 30%", {"hdv_bet_max_share": 0.30}),
                      ("Off-road machinery on liquids only", {"offroad_el_max_share": 0.0}),
                      ("At least 30% of gasoline-vehicle demand on E85", {"e85_min_share": 0.30})):
        s = o.solve(ts.case("dropin", ov))
        single.append(dict(rule=label, cost_busd=s["total_cost_busd"], delta_busd=s["total_cost_busd"] - base))
    R["fleet_rules_single"] = single
    json.dump(R, open(OUT / "results.json", "w"), indent=1, default=float)
    return R, S


def levers():
    p = sc.today()
    s0 = o.solve(p)
    out = [dict(key="today", label="Today's costs (7%)", cost=s0["total_cost_busd"], seaweed_km2=s0["seaweed_total_km2"],
                seaweed_share=s0["seaweed_share_pct"], electricity_twh=s0["electricity_delivered_twh"])]
    steps = [(k, l, f) for k, l, f in sc.LEVERS if k != "demand"]
    steps.append(("grid", "Grid Harvester harvesting energy (conventional/grid ratio 2.68)", lambda q: ts.with_grid_harvester(q)))
    for key, label, fn in steps:
        sc.cheaper_capital(p) if key == "capital" else fn(p)
        s = o.solve(p)
        out.append(dict(key=key, label=label, cost=s["total_cost_busd"], step_saving=out[-1]["cost"] - s["total_cost_busd"],
                        seaweed_km2=s["seaweed_total_km2"], seaweed_share=s["seaweed_share_pct"],
                        electricity_twh=s["electricity_delivered_twh"]))
    res = dict(cumulative=out)
    json.dump(res, open(OUT / "levers.json", "w"), indent=1, default=float)
    return res


def tri(a, m, b):
    return RNG.triangular(a, m, b)


def mc_draw():
    """One parameter draw, as overrides on the learned full-demand parameters (common to all three cases)."""
    r = tri(0.03, 0.04, 0.07)
    yld = tri(4.0, 9.0, 14.0)
    d = dict(r=r, yield_t_ha=yld,
             zone_yield={z: yld for z in ZONES[:5]} | {"car_deep": yld * 8 / 9},
             farm=dict(base_eur_t=tri(170, 250, 680), deep_factor=tri(1.05, 1.15, 1.60), slope_factor=tri(1.0, 1.1, 1.3),
                       depth_cycle_capex_km2=tri(0.34e6, 0.79e6, 3.4e6)),
             proc=dict(htl_biocrude_whole=tri(0.12, 0.165, 0.25), htl_biocrude_resid=tri(0.18, 0.245, 0.30),
                       alginate_use=tri(0.5, 0.9, 1.0), ad_ch4_nm3_kgvs=tri(0.15, 0.20, 0.25)),
             refinery_mult=0.7 * tri(0.8, 1.0, 1.4), pv=tri(36, 45, 56), onshore=tri(43, 52, 62), onshore_cap=tri(1.5, 3.0, 4.0),
             efuel_mult=tri(0.6, 0.85, 1.2), dac_mult=tri(0.5, 0.85, 1.2), pvtes=tri(10, 14, 25), csp_heat=tri(70, 95, 130),
             fert_mult=tri(0.7, 1.0, 1.3), wind_assist=tri(0.0, 0.08, 0.15),
             area_share={z: (tri(0.025, 0.10, 0.10) if z.endswith(("shelf", "slope")) else tri(0.0625, 0.25, 0.25)) for z in ZONES},
             veh=dict(car=tri(0, 1100, 3400), van=tri(0, 2300, 5700), truck=tri(0, 34000, 68000), lng_truck=tri(0, 28000, 45000),
                      ed95_truck=tri(0, 9000, 15000), e100_car=tri(0, 300, 600), e85_car=tri(0, 200, 1500)),
             grid_ratio=tri(1.84, 2.68, 4.99),
             seaweed=RNG.random() >= 0.10)
    return d


def mc_params(d, key):
    """Today's base parameters with the draw applied, priced at the drawn cost of capital, then the case rules."""
    p = o.base_params()
    p["zone_yield"] = dict(d["zone_yield"])
    p["farm"].update(d["farm"]); p["proc"].update(d["proc"])
    p["refinery_cost_mult"] = d["refinery_mult"]
    p["pv"]["lcoe"] = d["pv"]; p["onshore"]["lcoe"] = d["onshore"]; p["onshore"]["cap_gw"] = d["onshore_cap"]
    for k in ("eft", "emeoh", "enh3", "ech4"):
        p[k]["cost"] *= d["efuel_mult"]
    p["dac"]["cost"] *= d["dac_mult"]
    p["heat"]["pvtes_cost"] = d["pvtes"]; p["heat"]["csp_heat_cost"] = d["csp_heat"]
    p["fert"]["price"] = {k: v * d["fert_mult"] for k, v in p["fert"]["price"].items()}
    p["wind_assist_share"] = d["wind_assist"]
    p["area_share"] = dict(d["area_share"])
    p["veh"].update(d["veh"])
    sc.cheaper_capital(p, r_new=d["r"])
    ts.apply_case(p, key)
    ts.with_grid_harvester(p, d["grid_ratio"])
    p["allow_seaweed"] = d["seaweed"]
    return p


def monte_carlo(n=1000):
    draws = [mc_draw() for _ in range(n)]
    summary = {}
    for key in CASES:
        rows = []
        lc_rng = np.random.default_rng(20261015)
        infeasible = []
        for i, d in enumerate(draws):
            try:
                s = o.solve(mc_params(d, key))
            except RuntimeError:                         # e.g. E85 ethanol cannot be supplied when seaweed fails
                infeasible.append(dict(draw=i, seaweed_allowed=d["seaweed"], yield_t_ha=d["yield_t_ha"]))
                continue
            lc, fl, red = sampled_lifecycle(s, lc_rng)
            fs = s["fossil_cost_busd"]
            rows.append(dict(draw=i, wacc=d["r"], yield_t_ha=d["yield_t_ha"], farm_usd_t=d["farm"]["base_eur_t"],
                             grid_ratio=d["grid_ratio"], e85_car_usd=d["veh"]["e85_car"], seaweed_allowed=d["seaweed"],
                             cost_busd=s["total_cost_busd"], energy_cost_busd=s["energy_cost_busd"],
                             vehicle_premium_busd=s["vehicle_premium_busd"], fossil_oct2026_busd=fs["oct2026"],
                             fossil_2025_busd=fs["avg2025"], seaweed_km2=s["seaweed_total_km2"],
                             seaweed_share_pct=s["seaweed_share_pct"], electricity_twh=s["electricity_delivered_twh"],
                             efuels_twh=s["fuels_twh"]["eFT_liquids"], lowcarbon_lifecycle_mtco2e=lc,
                             fossil_lifecycle_mtco2e=fl, lifecycle_reduction_pct=red,
                             breakeven_multiplier_vs_2025=s["total_cost_busd"] / fs["avg2025"],
                             abatement_vs_2025_usd_t=(s["total_cost_busd"] - fs["avg2025"]) * 1000 / (fl - lc)))
        with open(OUT / f"monte_carlo_{key}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        A = lambda k: np.array([float(r[k]) for r in rows])
        c, e, f26, f25, km = A("cost_busd"), A("energy_cost_busd"), A("fossil_oct2026_busd"), A("fossil_2025_busd"), A("seaweed_km2")
        pc = lambda v: np.percentile(v, [5, 50, 95]).tolist()
        json.dump(infeasible, open(OUT / f"monte_carlo_{key}_infeasible.json", "w"), indent=1, default=float)
        summary[key] = dict(n=n, cost_p5_p50_p95=pc(c), energy_cost_p5_p50_p95=pc(e),
                            fossil_oct2026=float(np.median(f26)), fossil_2025=float(np.median(f25)),
                            n_below_oct2026=int(np.sum(c < f26)), n_energy_only_below_oct2026=int(np.sum(e < f26)),
                            n_below_2025=int(np.sum(c < f25)), n_energy_only_below_2025=int(np.sum(e < f25)),
                            breakeven_multiplier_p5_p50_p95=pc(A("breakeven_multiplier_vs_2025")),
                            seaweed_km2_p5_p50_p95=pc(km), seaweed_share_p5_p50_p95=pc(A("seaweed_share_pct")),
                            electricity_twh_p5_p50_p95=pc(A("electricity_twh")),
                            lifecycle_reduction_pct_p5_p50_p95=pc(A("lifecycle_reduction_pct")),
                            abatement_vs_2025_usd_t_p5_p50_p95=pc(A("abatement_vs_2025_usd_t")),
                            n_feasible=len(rows), n_infeasible=len(infeasible),
                            n_infeasible_seaweed_disabled=int(sum(1 for r in infeasible if not r["seaweed_allowed"])),
                            n_seaweed_disabled=int(sum(1 for d in draws if not d["seaweed"])),
                            n_seaweed_used=int(np.sum(km > 1)),
                            median_seaweed_used_draws_km2=float(np.median(km[km > 1])) if np.any(km > 1) else 0.0)
    json.dump(summary, open(OUT / "monte_carlo_summary.json", "w"), indent=1)
    return summary


STRESS = [
    ("No seaweed", {"allow_seaweed": False}),
    ("No seaweed and PV limited to 4 GW", {"allow_seaweed": False, "pv": {"cap_gw": 4.0}}),
    ("No seaweed and onshore wind limited to 1.5 GW", {"allow_seaweed": False, "onshore": {"cap_gw": 1.5}}),
    ("Seaweed yield 4 t ha⁻¹ yr⁻¹", {"zone_yield": {z: 4.0 for z in ZONES}}),
    ("Seaweed yield 6 t ha⁻¹ yr⁻¹", {"zone_yield": {z: 6.0 for z in ZONES}}),
    ("Whole-seaweed HTL yield 0.12", {"proc": {"htl_biocrude_whole": 0.12}}),
    ("Candidate marine area 25%", "area:0.25"),
    ("Candidate marine area 5%", "area:0.05"),
    ("No depth cycling (natural nutrients or pumps)", {"nutrient_methods": ("natural", "solar_pipe", "wave_pump", "wave_pump_xl", "salt_fountain")}),
    ("No fertilizer credit", {"fert": {"price": {"n": 0.0, "p": 0.0, "k": 0.0}}}),
    ("Integration and network adders ×2", "adders:2.0"),
    ("Onshore wind limited to 1.5 GW", {"onshore": {"cap_gw": 1.5}}),
    ("PV limited to 4 GW", {"pv": {"cap_gw": 4.0}}),
    ("Finance at 7%", "finance:0.07"),
    ("Vehicle premia high", {"veh": {"car": 3400, "van": 5700, "truck": 68000, "lng_truck": 45000, "ed95_truck": 15000, "e85_car": 1500}}),
    ("Conventional harvesting energy (ratio 1.0)", "grid:1.0"),
    ("Sargassum harvester with coarse chopping (ratio 1.84)", "grid:1.84"),
    ("Sargassum harvester without size reduction (ratio 4.99)", "grid:4.99"),
    ("Domestic aviation and shipping only", {"scope": "domestic"}),
]
OPTIONS_FORCED = [
    ("Refinery heat from CSP steam only", {"force_csp_heat": True}),
    ("CSP supplies ≥25% of new electricity", {"csp_min_share_el": 0.25}),
    ("Seaweed supplies all heavy liquids", {"seaweed_supplies_liquids": True}),
    ("Ethanol route at every refinery", {"refinery_routes": ("EH",)}),
    ("Offshore pressing before shipping", {"preprocess": ("press",)}),
    ("Solar-pumped upwelling only", {"nutrient_methods": ("natural", "solar_pipe")}),
    ("No electrofuels", {"allow_efuels": False}),
    ("LNG/CNG vehicles allowed (with liquefaction and conversion)", {"allow_methane_vehicles": True}),
]


def _case(spec):
    if isinstance(spec, dict):
        return ts.case("dropin", spec)
    kind, v = spec.split(":"); v = float(v)
    if kind == "finance":
        return ts.case("dropin", capital=False)
    p = ts.case("dropin")
    if kind == "area":
        p["area_share"] = {k: min(x, v) if k.endswith(("shelf", "slope")) else v for k, x in p["area_share"].items()}
    elif kind == "adders":
        for k in ("pv_day", "pv_shift", "onshore", "network_direct", "network_flex", "flex_pv", "flex_onshore", "flex_csp"):
            p["adder"][k] *= v
    elif kind == "grid":
        p["fleet"]["grid_harvester"] = v != 1.0
        p["fleet"]["grid_energy_ratio"] = v
    return p


def robustness():
    central = o.solve(ts.case("dropin"))
    rows = []
    for group, lst in (("stress", STRESS), ("option", OPTIONS_FORCED)):
        for label, spec in lst:
            s = o.solve(_case(spec))
            rows.append(dict(group=group, case=label, cost_busd=s["total_cost_busd"], delta_busd=s["total_cost_busd"] - central["total_cost_busd"],
                             energy_cost_busd=s["energy_cost_busd"], vehicle_premium_busd=s["vehicle_premium_busd"],
                             fossil_oct2026_busd=s["fossil_cost_busd"]["oct2026"], fossil_2025_busd=s["fossil_cost_busd"]["avg2025"],
                             seaweed_km2=s["seaweed_total_km2"], seaweed_share_pct=s["seaweed_share_pct"],
                             electricity_twh=s["electricity_delivered_twh"], pv_gw=s["capacity_gw"]["PV"],
                             wind_gw=s["capacity_gw"]["Onshore wind"], csp_gw=s["capacity_gw"]["CSP"],
                             electrolyser_gw=s["electrolyser_gw"], dac_mt=s["co2_mt"]["DAC"],
                             efuels_twh=s["fuels_twh"]["eFT_liquids"] + s["fuels_twh"]["e_methanol"] + s["fuels_twh"]["e_ammonia"] + s["fuels_twh"]["e_methane"],
                             methane_marginal_usd_mwh=s["marginal_usd_mwh"].get("methane", 0.0),
                             lifecycle_reduction_pct=s["lifecycle"]["reduction_pct"]))
    with open(OUT / "robustness.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump(dict(central_busd=central["total_cost_busd"], central_seaweed_km2=central["seaweed_total_km2"],
                   central_electricity_twh=central["electricity_delivered_twh"],
                   central_methane_marginal_usd_mwh=central["marginal_usd_mwh"].get("methane", 0.0), cases=rows),
              open(OUT / "robustness.json", "w"), indent=1, default=float)
    return rows


def e85_sensitivity():
    """Solar bridge: per-vehicle E85 conversion allowance, and minimum E85 share of gasoline-vehicle demand."""
    allow, share = [], []
    for usd in (0, 200, 500, 1000, 1500):
        s = o.solve(ts.case("bridge", {"veh": {"e85_car": usd}}))
        allow.append(dict(e85_car_usd=usd, cost_busd=s["total_cost_busd"], vehicle_premium_busd=s["vehicle_premium_busd"],
                          e85_twh=s["end_use_twh"].get("ldv_gasoline|e85", 0.0)))
    for m in (0.30, 0.50, 0.70):
        s = o.solve(ts.case("bridge", {"e85_min_share": m, "ldv_bev_max_share": min(0.70, 1 - m)}))
        share.append(dict(e85_min_share=m, cost_busd=s["total_cost_busd"], seaweed_km2=s["seaweed_total_km2"],
                          vehicle_electricity_twh=s["electricity_vehicles_rail_twh"],
                          charging_grid_capex_busd=s["build"]["capex_busd"]["Charging and grid"]))
    res = dict(conversion_allowance=allow, e85_share=share)
    json.dump(res, open(OUT / "e85_sensitivity.json", "w"), indent=1, default=float)
    return res


if __name__ == "__main__":
    R, S = headline()
    for k in ("today",) + CASES:
        r = R[k]
        print(k, round(r["total_cost_busd"], 3), "energy", round(r["energy_cost_busd"], 3), "veh", round(r["vehicle_premium_busd"], 3),
              "range", [round(v, 3) for v in r["vehicle_premium_range_total_busd"]],
              {a: round(b, 1) for a, b in r["fossil_comparison"].items()},
              "sw", round(r["seaweed_total_km2"]), round(r["seaweed_share_pct"], 1), "el", round(r["electricity_delivered_twh"], 2),
              "LCA", round(r["lifecycle"]["reduction_pct"], 1), "harv", round(r["harvesters"]["units"]))
    print("fossil", {a: round(b, 3) for a, b in S["dropin"]["fossil_cost_busd"].items()})
    print("exposure", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in R["exposure"].items() if k != "shock"})
    for st in R["bridge_steps"]:
        print("bridge step", st["step"], round(st["cost_busd"], 3), round(st["seaweed_km2"]))
    for st in R["fleet_rules_single"]:
        print("rule", st["rule"], round(st["delta_busd"], 3))
    for c in levers()["cumulative"]:
        print("lever", c["key"], round(c["cost"], 3), round(c.get("step_saving", 0), 3), round(c["seaweed_km2"]))
    for r in robustness():
        print(f"{r['group']:7s} {r['case'][:58]:58s} {r['cost_busd']:.3f} {r['delta_busd']:+.3f} sw {r['seaweed_km2']:6.0f} el {r['electricity_twh']:5.1f} CH4 {r['methane_marginal_usd_mwh']:4.0f} LCA {r['lifecycle_reduction_pct']:.1f}")
    print(e85_sensitivity())
    for k, v in monte_carlo().items():
        print(k, {a: (([round(x, 2) for x in b]) if isinstance(b, list) else (round(b, 2) if isinstance(b, float) else b)) for a, b in v.items()})
