"""Scenario construction: today's costs, learning, finance and demand levers (applied cumulatively)."""
import copy
import optimise as o

CRF = o.CRF


def cheaper_capital(prm, r_new=0.04, r_old=0.07, life=25):
    """Re-price the capital share of each cost line at a lower cost of capital."""
    f = CRF(r_new, life) / CRF(r_old, life)
    sc = lambda v, cs: v * (1 - cs + cs * f)
    for k, cs in (("pv", 0.85), ("onshore", 0.75), ("geo", 0.75), ("csp", 0.80)):
        prm[k]["lcoe"] = sc(prm[k]["lcoe"], cs)
    for k, cs in (("pv_shift", 0.8), ("network_direct", 0.7), ("network_flex", 0.7), ("flex_pv", 0.8),
                  ("flex_onshore", 0.8), ("flex_csp", 0.8)):
        prm["adder"][k] = sc(prm["adder"][k], cs)
    prm["heat"]["pvtes_cost"] = sc(prm["heat"]["pvtes_cost"], 0.85)
    prm["heat"]["csp_heat_cost"] = sc(prm["heat"]["csp_heat_cost"], 0.80)
    for k in ("eft", "emeoh", "enh3", "ech4", "atj"):
        prm[k]["cost"] = sc(prm[k]["cost"], 0.7)
    prm["dac"]["cost"] = sc(prm["dac"]["cost"], 0.6)
    for k in ("waste_ch4", "hefa", "residue_ft"):
        prm[k]["cost"] = sc(prm[k]["cost"], 0.5)
    prm["farm"]["base_eur_t"] = sc(prm["farm"]["base_eur_t"], 0.6)
    prm["farm"]["rate"] = r_new
    prm["refinery_cost_mult"] = sc(prm["refinery_cost_mult"], 0.7)
    prm["veh"]["r"] = r_new
    return prm


YIELD_LEARN = {z: 12.0 for z in ("pac_shelf", "pac_slope", "pac_deep", "car_shelf", "car_slope")} | {"car_deep": 10.7}

LEVERS = [
    ("farm", "Cheaper farming: biomass $340 → $225 per dry t at reference yield",
     lambda p: p["farm"].update(base_eur_t=225.0)),
    ("yield", "Higher yield: 9 → 12 t dry ha⁻¹ yr⁻¹ (selected strains, multiple harvests)",
     lambda p: p.update(zone_yield=YIELD_LEARN)),
    ("deep", "Cheaper deep-water structures: factor 1.3 → 1.1; depth cycling $1.13M → $0.57M km⁻²",
     lambda p: p["farm"].update(deep_factor=1.1, slope_factor=1.05, depth_cycle_capex_km2=0.57e6)),
    ("conversion", "Better conversion: whole-seaweed HTL 0.15 → 0.18, residue 0.22 → 0.27, all alginate fermented",
     lambda p: p["proc"].update(htl_biocrude_whole=0.18, htl_biocrude_resid=0.27, alginate_use=1.0)),
    ("refcapex", "Biorefinery cost −30% (nth-of-a-kind plants)",
     lambda p: p.update(refinery_cost_mult=p["refinery_cost_mult"] * 0.7)),
    ("efuels", "Electrofuel synthesis and electrolyzers −25%; direct air capture −25%",
     lambda p: [p[k].update(cost=p[k]["cost"] * 0.75) for k in ("eft", "emeoh", "enh3", "ech4", "dac")]),
    ("capital", "Cheaper capital: 4% instead of 7%", lambda p: cheaper_capital(p)),
    ("demand", "Less fuel: aviation −20%, shipping −10%, wind-assisted ships up to 15%",
     lambda p: p.update(demand_mult={"aviation": 0.80, "shipping": 0.90}, wind_assist_share=0.15)),
]
LEARNING_KEYS = ("farm", "yield", "deep", "conversion", "refcapex", "efuels")


def build_case(learning=True, capital=True, demand=True, overrides=None, r=0.04):
    p = o.base_params()
    for key, _, fn in LEVERS:
        if key in LEARNING_KEYS and not learning:
            continue
        if key == "capital":
            if capital:
                cheaper_capital(p, r_new=r)
            continue
        if key == "demand" and not demand:
            continue
        fn(p)
    for k, v in (overrides or {}).items():
        p[k] = {**p[k], **v} if isinstance(v, dict) and isinstance(p.get(k), dict) else copy.deepcopy(v)
    return p


def today():
    return build_case(learning=False, capital=False, demand=False)
