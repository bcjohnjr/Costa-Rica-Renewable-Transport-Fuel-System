"""Least-cost renewable supply for all transport energy sold in Costa Rica, with native-seaweed fuels.

Annual linear programme (scipy/HiGHS). Units: TWh/yr, km2, Mt, USD 2026 (pre-tax).
Demand: fossil transport energy sold in Costa Rica in 2025 (RECOPE and ARESEP statistics), including fuel for
  international flights and ships bunkered in Costa Rica.
End uses: battery-electric, drop-in liquid (renewable diesel/jet), ethanol (E85/E100, ED95), methane (only if
  methane vehicles are allowed; liquefaction and conversion costs are then charged), methanol, ammonia.
  The drop-in rule (central case) requires aviation and off-road machinery to use drop-in liquids and at
  least half of heavy-truck and bus demand to use liquid fuel.
Supply: new PV, onshore wind, geothermal, concentrated solar power (CSP) with storage, native-seaweed farms
  (shelf, slope and deep water; natural nutrients, depth cycling or pumped upwelling), wet biorefineries
  (HTL diesel/jet, ethanol, biomethane, fertiliser) heated by solar heat (CSP steam or PV-charged
  high-temperature thermal storage), heat pumps or electric boilers; ethanol-to-jet; residue and waste fuels;
  electrofuels; direct air capture and biogenic CO2. No nuclear and no fossil energy is used.
Vehicle purchase premia at normal fleet replacement are part of the objective and reported separately.
A transition scenario represents E85 as 85% renewable ethanol plus 15% renewable drop-in hydrocarbon on an energy basis; no fossil blending component is used.
"""
import copy
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from farm import ZONES, FarmCost, farm_cost, METHODS
from biorefinery import Feed, Proc, routes as refinery_routes
from preprocess import Pre, options as preprocess_options
from lifecycle import screening_lifecycle

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
TWH_PER_PJ = 1 / 3.6
GJ2TWH = 1 / 3.6e6
CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)

# ------------------------------------------------------------------ demand (2025)
# Costa Rican Ministry of Finance: 2025 actual taxed road-fuel volumes, Table 6, Feb. 2026.
# 581 Ml regular + 844 Ml super = 1,425 Ml gasoline; diesel 1,332 Ml inclusive of
# off-road proxy (200 Ml) to avoid counting machinery twice. The non-road allocation
# of 200 Ml is a scenario assumption, NOT a separate independently measured volume.
# Jet 369.8 Ml is a December 2025 RECOPE/ARESEP forward projection, NOT audited final sales.
# Marine bunkering 45 Ml is a scenario assumption. Domestic vs international needs split.
# Hacienda: https://www.hacienda.go.cr/docs/MH-DGPN-DG-INF-0005-2026_YER.pdf (Table 6, p.39)
# ARESEP/RECOPE planning: https://direccionejecutiva.poder-judicial.go.cr/... (December 2025 annex)
VOL_2025_ML = {"gasoline": 581.0 + 844.0, "road_diesel": 1332.0 - 200.0,
               "offroad_diesel": 200.0, "jet": 369.8, "marine": 45.0}
MJ_PER_L = {"gasoline": 0.736 * 43.4, "diesel": 0.8363 * 43.0, "jet": 0.799 * 43.2, "marine": 0.89 * 42.7}
LDV_DIESEL_SHARE = 0.40       # pick-ups, SUVs, vans and taxis; remainder trucks and buses


def demand(scope="all"):
    road_d = VOL_2025_ML["road_diesel"] * MJ_PER_L["diesel"] / 1e3 * TWH_PER_PJ
    d = {"ldv_gasoline": VOL_2025_ML["gasoline"] * MJ_PER_L["gasoline"] / 1e3 * TWH_PER_PJ,
         "ldv_diesel": LDV_DIESEL_SHARE * road_d,
         "hdv": (1 - LDV_DIESEL_SHARE) * road_d,
         "offroad": VOL_2025_ML["offroad_diesel"] * MJ_PER_L["diesel"] / 1e3 * TWH_PER_PJ,
         "aviation": VOL_2025_ML["jet"] * MJ_PER_L["jet"] / 1e3 * TWH_PER_PJ,
         "shipping": VOL_2025_ML["marine"] * MJ_PER_L["marine"] / 1e3 * TWH_PER_PJ,
         "rail_el": 0.0}
    if scope == "domestic":
        d["aviation"] *= 0.04
        d["shipping"] *= 0.50
    return d


CO2_T_PER_MWH = {"ldv_gasoline": 0.249, "ldv_diesel": 0.267, "hdv": 0.267, "offroad": 0.267,
                 "aviation": 0.257, "shipping": 0.275, "rail_el": 0.0}
# Pre-tax prices, USD/MWh. Road: ARESEP retail price minus impuesto unico (Ley 8114), converted at the BCCR
# rate (Oct 2026: 764/719/785 CRC/l super/regular/diesel, tax 272/259.75/154, 452 CRC/USD; 2025 mean of
# Jan, Nov and Dec retail prices, tax 269/256.75/152, 505 CRC/USD). Jet: IATA monitor (EUR 89 and 52/MWh
# at 1.125 and 1.13 USD/EUR). Marine: EUR 56 and 40/MWh converted likewise.
FOSSIL = {"oct2026": {"ldv_gasoline": 119, "ldv_diesel": 140, "hdv": 140, "offroad": 140, "aviation": 100, "shipping": 63},
          "avg2025": {"ldv_gasoline": 87, "ldv_diesel": 81, "hdv": 81, "offroad": 81, "aviation": 59, "shipping": 45}}

# segment -> option: (carrier, MWh carrier per MWh fossil replaced, max share, delivery USD/MWh carrier, liquid?)
OPTIONS = {
    "ldv_gasoline": {"bev": ("el_direct", 0.31, 1.0, 51, False), "liq": ("dropin", 1.0, 1.0, 17, True),
                     "e85": ("e85", 1.0, 1.0, 17, True), "e100": ("ethanol", 1.0, 1.0, 17, True)},
    "ldv_diesel": {"bev": ("el_direct", 0.375, 1.0, 51, False), "liq": ("dropin", 1.0, 1.0, 17, True)},
    "hdv": {"bet": ("el_direct", 0.53, 0.90, 40, False), "lng": ("methane", 1.15, 0.50, 32, False),
            "liq": ("dropin", 1.0, 1.0, 17, True), "ed95": ("ethanol", 1.05, 0.50, 23, True)},
    "offroad": {"el": ("el_direct", 0.45, 0.40, 34, False), "cng": ("methane", 1.10, 0.30, 11, False),
                "liq": ("dropin", 1.0, 1.0, 17, True)},
    "aviation": {"jet": ("jet", 1.0, 1.0, 6, True)},
    "shipping": {"meoh": ("methanol", 1.0, 1.0, 6, True), "nh3": ("ammonia", 1.05, 0.50, 9, True),
                 "lng": ("methane", 1.0, 0.40, 26, False), "liq": ("dropin", 1.0, 1.0, 6, True)},
    "rail_el": {"el": ("el_direct", 1.0, 1.0, 0, False)},
}
METHANE_OPTS = (("hdv", "lng"), ("offroad", "cng"), ("shipping", "lng"))

# Vehicle use for premium conversion: annual km and fossil fuel energy per km (kWh/km)
KM = {"car": 14773, "van": 18000, "truck": 40000}
KWH_KM = {"petrol_car": 0.076 * 8.86, "diesel_ldv": 0.085 * 9.99, "truck": 0.32 * 9.99}

UNIT_CAPEX = {
    "PV (USD/kW)": 700, "Onshore wind (USD/kW)": 1500, "Geothermal (USD/kW)": 5000, "CSP (USD/kW)": 6500,
    "Electrolysers (USD/kW)": 1130, "E-fuel synthesis (USD/kW fuel)": 1020, "DAC (USD per t/yr)": 1700,
    "Seaweed farm shelf (USD/km2)": 2.3e6, "Seaweed farm deep (USD/km2)": 4.1e6, "Biorefinery (USD per t dw/yr)": 1860,
    "Vessel (USD each)": 68e6, "ATJ plant (USD/kW jet)": 1020, "Charging and grid (USD bn per TWh/yr of EV load)": 0.40,
    "Thermal storage + heaters (USD per MWh_th/yr)": 160, "CSP heat (USD per MWh_th/yr)": 900,
}


def base_params():
    return dict(
        pv=dict(lcoe=45, cf=0.18, cap_gw=20, mw_km2=50),
        onshore=dict(lcoe=52, cf=0.40, cap_gw=3.0),
        geo=dict(lcoe=90, cf=0.85, cap_gw=0.30),
        csp=dict(lcoe=170, cf=0.40, cap_gw=3.0),
        adder=dict(pv_day=9, pv_shift=62, onshore=17, geo=0, csp=0, network_direct=23, network_flex=9,
                   pv_day_share=0.45, flex_pv=34, flex_onshore=20, flex_geo=0, flex_csp=6),
        heat=dict(hp_cop=2.5, hp_max_share=0.6, eboiler_eff=0.99,
                  pvtes_eff=0.95, pvtes_cost=14.0,       # PV-charged thermal storage: heaters + store, USD/MWh_th
                  csp_heat_cost=95.0),                   # CSP steam with storage at DNI < 1,800 kWh/m2/yr
        eft=dict(el=2.40, cost=124, co2=0.30),
        emeoh=dict(el=1.90, cost=68, co2=0.25),
        enh3=dict(el=1.75, cost=57),
        ech4=dict(el=1.80, cost=62, co2=0.20),
        atj=dict(eff=0.925, cost=51),
        biomeoh=dict(ch4_per_meoh=1.5, cost=28),
        dac=dict(el=1.5, cost=340),
        bio_co2_other=dict(cap=1.0, cost=100),     # sugar-mill fermentation and bagasse boilers
        seaweed_co2_capture=23.0,
        waste_ch4=dict(cap=1.5, cost=90, co2=0.20),  # coffee pulp, pineapple residues, manure, landfill gas
        hefa=dict(cap=0.15, cost=185),              # domestic used cooking oil and animal fats
        crop_etoh=dict(cap=0.10, cost=110),         # molasses ethanol; no cropland expansion, no palm oil
        residue_ft=dict(cap=1.5, cost=190),         # pineapple stubble, rice husk, forestry residues
        allow_efuels=True,
        fert=dict(price={"n": 1.47, "p": 2.94, "k": 0.73}, cap_mt={"n": 0.08, "p": 0.015, "k": 0.06}, export_share=0.6),
        farm=asdict(FarmCost()),
        nutrient_methods=METHODS,
        area_share={"pac_shelf": 0.10, "pac_slope": 0.10, "pac_deep": 0.25, "car_shelf": 0.10, "car_slope": 0.10, "car_deep": 0.25},
        zone_yield={},
        refinery_routes=("EH", "H", "A"),
        proc=asdict(Proc()),
        preprocess=("wet", "press"),
        fleet=dict(harvest_gj=0.35, mj_tkm_near=0.15, mj_tkm_far=0.12, kite_near=0.10, kite_far=0.15,
                   grid_harvester=False, grid_energy_ratio=2.68),
        liquid_required=True,
        allow_methane_vehicles=False,
        seaweed_supplies_liquids=False,
        allow_seaweed=True,
        heat_sources=("pvtes", "csp", "hp", "eb"),
        force_csp_heat=False,
        csp_min_share_el=0.0,
        csp_refinery_power=False,
        ldv_bev_max_share=1.0,
        hdv_bet_max_share=0.90,
        offroad_el_max_share=0.40,
        e85_min_share=0.0,
        e85_ethanol_fraction=0.85,
        scope="all",
        demand_mult={},
        wind_assist_share=0.08,
        veh=dict(car=1100, van=2300, truck=34000, lng_truck=28000, ed95_truck=9000, e100_car=300, e85_car=200, r=0.07, life=15),
        refinery_cost_mult=1.0,
    )


def vehicle_premium_per_mwh(prm):
    """USD per MWh of fossil fuel replaced, by (segment, option)."""
    v = prm["veh"]
    f = CRF(v["r"], v["life"])
    pm = lambda prem, km, kwh_km: prem * f / km * (1000 / kwh_km)
    car_d = 0.6 * pm(v["car"], KM["car"], KWH_KM["diesel_ldv"]) + 0.4 * pm(v["van"], KM["van"], KWH_KM["diesel_ldv"])
    return {("ldv_gasoline", "bev"): pm(v["car"], KM["car"], KWH_KM["petrol_car"]),
            ("ldv_gasoline", "e85"): pm(v.get("e85_car", 200), KM["car"], KWH_KM["petrol_car"]),
            ("ldv_gasoline", "e100"): pm(v["e100_car"], KM["car"], KWH_KM["petrol_car"]),
            ("ldv_diesel", "bev"): car_d,
            ("hdv", "bet"): pm(v["truck"], KM["truck"], KWH_KM["truck"]),
            ("hdv", "lng"): pm(v["lng_truck"], KM["truck"], KWH_KM["truck"]),
            ("hdv", "ed95"): pm(v["ed95_truck"], KM["truck"], KWH_KM["truck"]),
            ("offroad", "el"): pm(v["truck"], KM["truck"], KWH_KM["truck"]),
            ("offroad", "cng"): pm(v["lng_truck"], KM["truck"], KWH_KM["truck"])}


class LP:
    def __init__(self):
        self.names, self.cost, self.bounds, self.ub, self.eq = [], [], [], [], []

    def var(self, name, cost=0.0, lb=0.0, ub=None):
        self.names.append(name); self.cost.append(cost); self.bounds.append((lb, ub))
        return len(self.names) - 1

    def le(self, co, rhs, tag=None):
        self.ub.append((co, rhs, tag))

    def eqc(self, co, rhs, tag=None):
        self.eq.append((co, rhs, tag))

    def solve(self):
        n = len(self.names)

        def mat(rows):
            A = np.zeros((len(rows), n)); b = np.zeros(len(rows))
            for i, (co, rhs, _) in enumerate(rows):
                for j, v in co.items():
                    A[i, j] += v
                b[i] = rhs
            return A, b
        Au, bu = mat(self.ub); Ae, be = mat(self.eq)
        res = linprog(np.array(self.cost), A_ub=Au, b_ub=bu, A_eq=Ae, b_eq=be, bounds=self.bounds, method="highs")
        if res.status != 0:
            raise RuntimeError(res.message)
        duals = {}
        for i, (_, _, tag) in enumerate(self.ub):
            if tag: duals[tag] = -res.ineqlin.marginals[i]
        for i, (_, _, tag) in enumerate(self.eq):
            if tag: duals[tag] = -res.eqlin.marginals[i]
        return dict(zip(self.names, res.x)), res.fun, duals


def add(d, k, v):
    d[k] = d.get(k, 0.0) + v


def seaweed_systems(prm):
    """Enumerate (zone, band, nutrient method, pre-processing, refinery route) systems."""
    fc = FarmCost(**prm["farm"])
    fl = prm["fleet"]
    pre_opts = preprocess_options(Pre(**{**prm.get("pre", {}), "dm_harvest": fc.dm_harvest}))
    feed = Feed()
    systems = []
    for zk, z in ZONES.items():
        y = prm["zone_yield"].get(zk)
        for band in z.area_km2:
            for m in prm["nutrient_methods"]:
                fcost = farm_cost(zk, band, fc, m, yield_override=y)
                if not np.isfinite(fcost["total_eur_t"]) or fcost["yield_t_ha"] <= 0:
                    continue
                t_km2 = fcost["yield_t_ha"] * 100
                km = z.mid_km[band]
                far = km > 100
                wet = 1 / fc.dm_harvest
                transit = wet * km * (fl["mj_tkm_far"] if far else fl["mj_tkm_near"]) * 1.6 / 1000
                kite = fl["kite_far"] if far else fl["kite_near"]
                for pk in prm["preprocess"]:
                    po = pre_opts[pk]
                    mass_ratio = po["mass_t"] / wet
                    transport_new = po["mass_t"] * max(km - 40, 0) * fc.transport_eur_t_wet_km
                    farm_usd = fcost["total_eur_t"] - fcost["transport_eur_t"] + transport_new + po["cost"]
                    pproc = Proc(**{**prm["proc"], **({} if po["ensile"] else {"ensile_sugar_loss": 0.0})})
                    pfeed = Feed(**{**asdict(feed), "mannitol": feed.mannitol * po["mannitol_keep"]})
                    rts = refinery_routes(pfeed, pproc)
                    for r in prm["refinery_routes"]:
                        rr = dict(rts[r])
                        for kk in ("hc_gj", "jet_gj", "ch4_gj"):
                            rr[kk] *= po["vs_keep"]
                        if r != "EH":
                            rr["co2_ferm_t"] *= po["vs_keep"]
                        ref_cost = (rr["cost_eur"] - (0.0 if po["ensile"] else pproc.cost_ensile)) * prm["refinery_cost_mult"]
                        systems.append(dict(
                            key=f"{zk}|{band}|{m}|{pk}|{r}", zone=zk, band=band, method=fcost["method"], pre=pk, route=r,
                            area_cap=z.area_km2[band] * prm["area_share"][zk], t_km2=t_km2,
                            farm_usd_t=farm_usd, refinery_usd_t=ref_cost,
                            fleet_gj_t=(fl["harvest_gj"] / fl.get("grid_energy_ratio", 1.0) if fl.get("grid_harvester", False) else fl["harvest_gj"]) + transit * mass_ratio * (1 - kite),
                            kite_saved_gj_t=transit * mass_ratio * kite,
                            ethanol_gj=rr["ethanol_gj"], hc_gj=rr["hc_gj"], jet_gj=rr["jet_gj"], ch4_gj=rr["ch4_gj"],
                            el_mwh=rr["el_mwh"], heat_mwh=rr["heat_mwh_th"], co2_t=rr["co2_ferm_t"],
                            fert=(rr["fert_n_kg"], rr["fert_p_kg"], rr["fert_k_kg"]), fert_energy_gj=rr["fert_energy_gj"],
                            fert_co2_t=rr["fert_co2_t"], units_km2=fcost["units_per_km2"],
                            deep_water_m3_t=fcost["deep_water_m3_per_t_dw"], wet_mass_t=po["mass_t"]))
    return systems


def solve(prm):
    d = demand(prm["scope"])
    for k, m in prm.get("demand_mult", {}).items():
        d[k] *= m
    lp = LP()
    a = prm["adder"]
    G = {}
    G["pv_day"] = lp.var("pv_direct_day", prm["pv"]["lcoe"] + a["pv_day"] + a["network_direct"])
    G["pv_shift"] = lp.var("pv_direct_shifted", prm["pv"]["lcoe"] + a["pv_shift"] + a["network_direct"])
    G["pv_flex"] = lp.var("pv_flex", prm["pv"]["lcoe"] + a["flex_pv"] + a["network_flex"])
    G["pv_heat"] = lp.var("pv_for_thermal_storage", prm["pv"]["lcoe"])           # behind the meter at the refinery
    for t, key in (("onshore", "onshore"), ("geo", "geo"), ("csp", "csp")):
        G[t + "_dir"] = lp.var(f"{t}_direct", prm[t]["lcoe"] + a[key] + a["network_direct"])
        G[t + "_flex"] = lp.var(f"{t}_flex", prm[t]["lcoe"] + a["flex_" + key] + a["network_flex"])
    h = prm["heat"]
    off = prm.get("offshore")      # optional offshore wind (Supplementary Note 20); absent in the national cases
    if off:
        G["off_dir"] = lp.var("offshore_direct", off["lcoe"] + off["adder_direct"] + a["network_direct"])
        G["off_flex"] = lp.var("offshore_flex", off["lcoe"] + off["adder_flex"] + a["network_flex"])
    HS = {}
    HS["pvtes"] = lp.var("heat_pv_thermal_storage", h["pvtes_cost"])
    HS["csp"] = lp.var("heat_csp_steam", h["csp_heat_cost"])
    HS["hp"] = lp.var("heat_heat_pump")
    HS["eb"] = lp.var("heat_electric_boiler")
    for k, i in HS.items():
        if k not in prm["heat_sources"]:
            lp.bounds[i] = (0, 0)
    if off:
        # offshore electricity to the refinery's electric backup heater (heat, MWh_th)
        HS["off_heat"] = lp.var("heat_offshore_electric", (off["lcoe"] + a["network_direct"]) / h["eboiler_eff"])
    pvt = prm.get("pvt")           # optional PVT slurry preheating (Supplementary Note 20)
    if pvt:
        HS["pvt"] = lp.var("heat_pvt_preheat")
        A_PVT = lp.var("pvt_area_km2", pvt["annual_cost_musd_km2"], pvt.get("min_km2", 0.0), pvt["max_km2"])
        lp.le({HS["pvt"]: 1.0, A_PVT: -pvt["heat_twh_km2"]}, 0.0)
    lp.eqc({G["pv_heat"]: 1.0, HS["pvtes"]: -1 / h["pvtes_eff"]}, 0.0)

    systems = seaweed_systems(prm)
    K = {s["key"]: lp.var("sw_km2|" + s["key"], s["t_km2"] * (s["farm_usd_t"] + s["refinery_usd_t"]) / 1e6) for s in systems}
    zb = {}
    for s in systems:
        zb.setdefault((s["zone"], s["band"]), []).append(s)
    for ss in zb.values():
        lp.le({K[s["key"]]: 1.0 for s in ss}, ss[0]["area_cap"])

    F = {}
    F["eft"] = lp.var("eFT_liquids", prm["eft"]["cost"])
    F["emeoh"] = lp.var("e_methanol", prm["emeoh"]["cost"])
    F["enh3"] = lp.var("e_ammonia", prm["enh3"]["cost"])
    F["ech4"] = lp.var("e_methane", prm["ech4"]["cost"])
    F["atj"] = lp.var("ATJ_jet_from_ethanol", prm["atj"]["cost"])
    F["biomeoh"] = lp.var("bio_methanol_from_CH4", prm["biomeoh"]["cost"])
    F["waste_ch4"] = lp.var("waste_biomethane", prm["waste_ch4"]["cost"], 0, prm["waste_ch4"]["cap"])
    F["hefa"] = lp.var("HEFA_waste_lipids", prm["hefa"]["cost"], 0, prm["hefa"]["cap"])
    F["resft"] = lp.var("residue_FT", prm["residue_ft"]["cost"], 0, prm["residue_ft"]["cap"])
    F["cetoh"] = lp.var("crop_ethanol_existing", prm["crop_etoh"]["cost"], 0, prm["crop_etoh"]["cap"])
    F["dac"] = lp.var("DAC_CO2_Mt", prm["dac"]["cost"])
    F["bco2"] = lp.var("other_biogenic_CO2_Mt", prm["bio_co2_other"]["cost"], 0, prm["bio_co2_other"]["cap"])
    F["kco2"] = lp.var("seaweed_CO2_used_Mt", prm["seaweed_co2_capture"])
    F["wind_assist"] = lp.var("wind_assist_saving", 51.0, 0, prm["wind_assist_share"] * d["shipping"])
    fert = {}
    for nut in ("n", "p", "k"):
        pr = prm["fert"]["price"][nut] * 1000
        fert[nut + "_dom"] = lp.var(f"fert_{nut}_domestic_Mt", -pr, 0, prm["fert"]["cap_mt"][nut])
        fert[nut + "_exp"] = lp.var(f"fert_{nut}_export_Mt", -pr * prm["fert"]["export_share"])

    vp = vehicle_premium_per_mwh(prm)
    U = {}
    for sg, opts in OPTIONS.items():
        for o, (car, ratio, share, extra, liq) in opts.items():
            U[(sg, o)] = lp.var(f"use|{sg}|{o}", extra * ratio + vp.get((sg, o), 0.0))
    for sg, opts in OPTIONS.items():
        co = {U[(sg, o)]: 1.0 for o in opts}
        if sg == "shipping":
            co[F["wind_assist"]] = 1.0
        lp.eqc(co, d[sg])
        for o, (car, ratio, share, extra, liq) in opts.items():
            cap = share
            if sg == "ldv_gasoline" and o == "bev":
                cap = min(cap, prm.get("ldv_bev_max_share", 1.0))
            if sg == "ldv_diesel" and o == "bev":
                cap = min(cap, prm.get("ldv_bev_max_share", 1.0))
            if sg == "hdv" and o == "bet":
                cap = min(cap, prm.get("hdv_bet_max_share", 0.90))
            if sg == "offroad" and o == "el":
                cap = min(cap, prm.get("offroad_el_max_share", 0.40))
            if (sg, o) in METHANE_OPTS and not prm["allow_methane_vehicles"]:
                cap = 0.0
            if prm["liquid_required"]:
                if sg == "offroad" and not liq:
                    cap = 0.0
                if sg == "hdv" and o == "bet":
                    cap = min(cap, 0.5)
                if sg == "hdv" and o == "lng":
                    cap = 0.0
            if cap < 1.0:
                lp.le({U[(sg, o)]: 1.0}, cap * d[sg])
    if prm["liquid_required"]:
        lp.le({U[("hdv", "liq")]: -1.0, U[("hdv", "ed95")]: -1.0}, -0.5 * d["hdv"])
    if prm.get("e85_min_share", 0.0) > 0:
        lp.le({U[("ldv_gasoline", "e85")]: -1.0}, -prm["e85_min_share"] * d["ldv_gasoline"])

    def use(car):
        co = {}
        for (sg, o), i in U.items():
            if OPTIONS[sg][o][0] == car:
                add(co, i, OPTIONS[sg][o][1])
        return co

    co = use("dropin")
    for k, v in use("e85").items(): add(co, k, (1.0 - prm.get("e85_ethanol_fraction", 0.85)) * v)
    for k, v in use("jet").items(): add(co, k, v)
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["hc_gj"] * GJ2TWH)
    for f in ("eft", "hefa", "resft", "atj"): add(co, F[f], -1.0)
    lp.le(co, 0.0, "dropin")
    co = use("jet")
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["jet_gj"] * GJ2TWH)
    for f in ("eft", "hefa", "resft", "atj"): add(co, F[f], -1.0)
    lp.le(co, 0.0, "jet")
    co = use("ethanol")
    for k, v in use("e85").items(): add(co, k, prm.get("e85_ethanol_fraction", 0.85) * v)
    add(co, F["atj"], 1 / prm["atj"]["eff"]); add(co, F["cetoh"], -1.0)
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["ethanol_gj"] * GJ2TWH)
    lp.le(co, 0.0, "ethanol")
    co = use("methane")
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * (s["ch4_gj"] - s["fleet_gj_t"]) * GJ2TWH)
    add(co, F["waste_ch4"], -1); add(co, F["ech4"], -1); add(co, F["biomeoh"], prm["biomeoh"]["ch4_per_meoh"])
    lp.le(co, 0.0, "methane")
    co = use("methanol"); add(co, F["emeoh"], -1); add(co, F["biomeoh"], -1); lp.le(co, 0.0, "methanol")
    co = use("ammonia"); add(co, F["enh3"], -1); lp.le(co, 0.0, "ammonia")
    lp.le({F["eft"]: prm["eft"]["co2"], F["emeoh"]: prm["emeoh"]["co2"], F["ech4"]: prm["ech4"]["co2"],
           F["dac"]: -1, F["bco2"]: -1, F["kco2"]: -1, F["waste_ch4"]: -prm["waste_ch4"]["co2"]}, 0.0, "co2")
    co = {F["kco2"]: 1.0}
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["co2_t"] / 1e6)
    lp.le(co, 0.0)
    for j, nut in enumerate(("n", "p", "k")):
        co = {fert[nut + "_dom"]: 1.0, fert[nut + "_exp"]: 1.0}
        for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["fert"][j] / 1e9)
        lp.le(co, 0.0)
    # process heat
    co = {HS[k]: -1.0 for k in HS}
    for s in systems: add(co, K[s["key"]], s["t_km2"] * s["heat_mwh"] / 1e6)
    lp.le(co, 0.0, "heat")
    if pvt:
        co = {HS["pvt"]: 1.0}
        for s_ in systems: add(co, K[s_["key"]], -pvt["preheat_share"] * s_["t_km2"] * s_["heat_mwh"] / 1e6)
        lp.le(co, 0.0, "pvt_preheat_share")
    if off:
        co = {G["off_dir"]: 1.0, G["off_flex"]: 1.0, HS["off_heat"]: 1 / h["eboiler_eff"]}
        if off.get("imposed", False):
            lp.eqc(co, off["twh"], "offshore_imposed")
        else:
            lp.le(co, off["twh"], "offshore_cap")
        co = {HS["off_heat"]: 1.0}
        for s_ in systems: add(co, K[s_["key"]], -off["heater_max_share"] * s_["t_km2"] * s_["heat_mwh"] / 1e6)
        lp.le(co, 0.0, "offshore_heater_share")
    co = {HS["hp"]: 1.0}
    for s in systems: add(co, K[s["key"]], -h["hp_max_share"] * s["t_km2"] * s["heat_mwh"] / 1e6)
    lp.le(co, 0.0)
    if prm["force_csp_heat"]:
        for k in ("pvtes", "hp", "eb"):
            lp.bounds[HS[k]] = (0, 0)
    # electricity: direct (vehicles, refineries, heat pumps, boilers) and flexible (electrolysis, DAC)
    co = use("el_direct")
    for s in systems: add(co, K[s["key"]], s["t_km2"] * s["el_mwh"] / 1e6)
    add(co, HS["hp"], 1 / h["hp_cop"]); add(co, HS["eb"], 1 / h["eboiler_eff"])
    for k in ("pv_day", "pv_shift", "onshore_dir", "geo_dir", "csp_dir"):
        add(co, G[k], -1.0)
    if off: add(co, G["off_dir"], -1.0)
    if pvt: add(co, A_PVT, -pvt["el_twh_km2"])
    lp.eqc(co, 0.0, "el_direct")
    co = {F["eft"]: prm["eft"]["el"], F["emeoh"]: prm["emeoh"]["el"], F["enh3"]: prm["enh3"]["el"],
          F["ech4"]: prm["ech4"]["el"], F["dac"]: prm["dac"]["el"]}
    for k in ("pv_flex", "onshore_flex", "geo_flex", "csp_flex"):
        add(co, G[k], -1.0)
    if off: add(co, G["off_flex"], -1.0)
    lp.le(co, 0.0, "el_flex")
    co = {G["pv_day"]: 1.0}
    for k, v in use("el_direct").items(): add(co, k, -a["pv_day_share"] * v)
    lp.le(co, 0.0)
    if prm.get("csp_refinery_power", False):
        # Co-located solar-biorefineries: CSP electricity must at least cover the refineries' direct electrical load.
        co = {G["csp_dir"]: -1.0}
        for sy in systems:
            add(co, K[sy["key"]], sy["t_km2"] * sy["el_mwh"] / 1e6)
        lp.le(co, 0.0, "csp_refinery_power")

    def cap(keys, gw, cf):
        lp.le({G[k]: 1.0 for k in keys}, gw * cf * 8.76)
    cap(("pv_day", "pv_shift", "pv_flex", "pv_heat"), prm["pv"]["cap_gw"], prm["pv"]["cf"])
    cap(("onshore_dir", "onshore_flex"), prm["onshore"]["cap_gw"], prm["onshore"]["cf"])
    cap(("geo_dir", "geo_flex"), prm["geo"]["cap_gw"], prm["geo"]["cf"])
    cap(("csp_dir", "csp_flex"), prm["csp"]["cap_gw"], prm["csp"]["cf"])
    if prm["csp_min_share_el"] > 0:
        tot = {G[k]: -prm["csp_min_share_el"] for k in G}
        for k in ("csp_dir", "csp_flex"):
            tot[G[k]] += 1.0
        lp.le({k: -v for k, v in tot.items()}, 0.0)
    if not prm["allow_seaweed"]:
        for k in K.values():
            lp.bounds[k] = (0, 0)
    if prm["seaweed_supplies_liquids"]:
        co = {U[("aviation", "jet")]: 1.0, U[("offroad", "liq")]: 1.0, U[("hdv", "liq")]: 1.0,
              U[("hdv", "ed95")]: OPTIONS["hdv"]["ed95"][1]}
        for s in systems:
            add(co, K[s["key"]], -s["t_km2"] * (s["hc_gj"] + s["ethanol_gj"] * prm["atj"]["eff"]) * GJ2TWH)
        add(co, F["hefa"], -1.0); add(co, F["cetoh"], -1.0)
        lp.le(co, 0.0)
        for f in ("eft", "resft"):
            lp.bounds[F[f]] = (0, 0)
    if not prm["allow_efuels"]:
        for f in ("eft", "emeoh", "enh3", "ech4"):
            lp.bounds[F[f]] = (0, 0)

    x, total, duals = lp.solve()
    return summarise(x, total, duals, prm, d, systems, vp)


def summarise(x, total, duals, prm, d, systems, vp):
    s = {"total_cost_busd": total / 1000}
    vprem = sum(x[f"use|{sg}|{o}"] * v for (sg, o), v in vp.items()) / 1000
    s["vehicle_premium_busd"] = vprem
    s["energy_cost_busd"] = s["total_cost_busd"] - vprem
    gen = {"PV": x["pv_direct_day"] + x["pv_direct_shifted"] + x["pv_flex"] + x["pv_for_thermal_storage"],
           "Onshore wind": x["onshore_direct"] + x["onshore_flex"],
           "Geothermal": x["geo_direct"] + x["geo_flex"],
           "CSP": x["csp_direct"] + x["csp_flex"]}
    cf = {"PV": prm["pv"]["cf"], "Onshore wind": prm["onshore"]["cf"], "Geothermal": prm["geo"]["cf"], "CSP": prm["csp"]["cf"]}
    s["generation_twh"] = gen
    s["pv_for_heat_twh"] = x["pv_for_thermal_storage"]
    s["capacity_gw"] = {k: v / (cf[k] * 8.76) for k, v in gen.items()}
    s["electricity_delivered_twh"] = sum(gen.values())
    if "offshore_direct" in x or "pvt_area_km2" in x:
        s["hybrid"] = {"offshore_twh": x.get("offshore_direct", 0.0) + x.get("offshore_flex", 0.0) + x.get("heat_offshore_electric", 0.0) / prm["heat"]["eboiler_eff"],
                       "offshore_direct_twh": x.get("offshore_direct", 0.0), "offshore_flex_twh": x.get("offshore_flex", 0.0),
                       "offshore_heat_twh": x.get("heat_offshore_electric", 0.0),
                       "pvt_area_km2": x.get("pvt_area_km2", 0.0), "pvt_heat_twh": x.get("heat_pvt_preheat", 0.0),
                       "pvt_el_twh": x.get("pvt_area_km2", 0.0) * (prm.get("pvt") or {}).get("el_twh_km2", 0.0)}
    s["heat_twh_th"] = {"PV-charged thermal storage": x["heat_pv_thermal_storage"], "CSP steam": x["heat_csp_steam"],
                        "heat pumps": x["heat_heat_pump"], "electric boilers": x["heat_electric_boiler"]}
    sysd = {sy["key"]: sy for sy in systems}
    kel = {k.split("|", 1)[1]: v for k, v in x.items() if k.startswith("sw_km2|") and v > 1e-3}
    tot = lambda f: sum(v * sysd[k]["t_km2"] * f(sysd[k]) for k, v in kel.items())
    s["seaweed_km2"] = kel
    s["seaweed_total_km2"] = sum(kel.values())
    s["seaweed_dry_mt"] = tot(lambda q: 1) / 1e6
    s["seaweed_wet_mt"] = s["seaweed_dry_mt"] / prm["farm"]["dm_harvest"]
    s["seaweed_ethanol_twh"] = tot(lambda q: q["ethanol_gj"]) / 3.6e6
    s["seaweed_hc_twh"] = tot(lambda q: q["hc_gj"]) / 3.6e6
    s["seaweed_jet_twh"] = tot(lambda q: q["jet_gj"]) / 3.6e6
    s["seaweed_ch4_gross_twh"] = tot(lambda q: q["ch4_gj"]) / 3.6e6
    s["seaweed_fleet_fuel_twh"] = tot(lambda q: q["fleet_gj_t"]) / 3.6e6
    s["kite_saved_twh"] = tot(lambda q: q["kite_saved_gj_t"]) / 3.6e6
    s["seaweed_refinery_el_twh"] = tot(lambda q: q["el_mwh"]) / 1e6
    s["seaweed_refinery_heat_twh"] = tot(lambda q: q["heat_mwh"]) / 1e6
    s["seaweed_cost_busd"] = sum(v * sysd[k]["t_km2"] * (sysd[k]["farm_usd_t"] + sysd[k]["refinery_usd_t"]) for k, v in kel.items()) / 1e9
    s["fertiliser_mt"] = {n: tot(lambda q, j=j: q["fert"][j]) / 1e9 for j, n in enumerate(("N", "P", "K"))}
    s["fertiliser_value_busd"] = sum(x[f"fert_{n}_{w}_Mt"] * prm["fert"]["price"][n] * (1 if w == "domestic" else prm["fert"]["export_share"])
                                     for n in ("n", "p", "k") for w in ("domestic", "export"))
    s["fertiliser_energy_avoided_pj"] = tot(lambda q: q["fert_energy_gj"]) / 1e6
    s["fertiliser_co2_avoided_mt"] = tot(lambda q: q["fert_co2_t"]) / 1e6
    s["upwelling_pipes"] = tot(lambda q: q["units_km2"] / q["t_km2"] if q["method"] in ("solar_pipe", "wave_pump", "wave_pump_xl", "salt_fountain") else 0)
    for key, field in (("seaweed_by_zone_km2", "zone"), ("seaweed_by_route_km2", "route"),
                       ("seaweed_by_nutrient_method_km2", "method"), ("seaweed_by_preprocess_km2", "pre"),
                       ("seaweed_by_band_km2", "band")):
        s[key] = {}
        for k, v in kel.items():
            add(s[key], sysd[k][field], v)
    s["seaweed_by_zone_band_km2"] = {}
    for k, v in kel.items():
        add(s["seaweed_by_zone_band_km2"], sysd[k]["zone"] + "|" + sysd[k]["band"], v)
    fuels = {k: x[k] for k in ("eFT_liquids", "e_methanol", "e_ammonia", "e_methane", "ATJ_jet_from_ethanol",
                               "waste_biomethane", "HEFA_waste_lipids", "residue_FT", "crop_ethanol_existing")}
    fuels["seaweed HTL diesel/jet"] = s["seaweed_hc_twh"]
    atj_from_seaweed = max(0.0, x["ATJ_jet_from_ethanol"] / prm["atj"]["eff"] - x["crop_ethanol_existing"])
    fuels["seaweed ethanol"] = max(0.0, s["seaweed_ethanol_twh"] - atj_from_seaweed)
    fuels["seaweed biomethane (net of fleet)"] = s["seaweed_ch4_gross_twh"] - s["seaweed_fleet_fuel_twh"]
    s["fuels_twh"] = fuels
    s["bio_methanol_from_CH4_twh"] = x["bio_methanol_from_CH4"]
    s["co2_mt"] = {"DAC": x["DAC_CO2_Mt"], "other biogenic": x["other_biogenic_CO2_Mt"], "seaweed": x["seaweed_CO2_used_Mt"]}
    s["wind_assist_twh_saved"] = x["wind_assist_saving"]
    s["end_use_twh"] = {k[4:]: v for k, v in x.items() if k.startswith("use|") and v > 1e-6}
    el_fuels = (prm["eft"]["el"] * x["eFT_liquids"] + prm["emeoh"]["el"] * x["e_methanol"] + prm["enh3"]["el"] * x["e_ammonia"]
                + prm["ech4"]["el"] * x["e_methane"])
    s["electricity_for_efuels_twh"] = el_fuels
    s["electricity_for_dac_twh"] = prm["dac"]["el"] * x["DAC_CO2_Mt"]
    s["electrolyser_gw"] = el_fuels * 0.95 / (0.55 * 8.76)
    ev = sum(v * OPTIONS[k.split("|")[0]][k.split("|")[1]][1] for k, v in s["end_use_twh"].items()
             if OPTIONS[k.split("|")[0]][k.split("|")[1]][0] == "el_direct")
    s["electricity_vehicles_rail_twh"] = ev
    s["electricity_refineries_twh"] = s["seaweed_refinery_el_twh"] + x["heat_heat_pump"] / prm["heat"]["hp_cop"] + x["heat_electric_boiler"] / prm["heat"]["eboiler_eff"]
    s["marginal_usd_mwh"] = {k: v for k, v in duals.items() if k != "co2"}
    s["co2_marginal_usd_t"] = duals.get("co2", 0.0)
    s["demand_twh"] = d
    s["fossil_cost_busd"] = {sc: sum(FOSSIL[sc][k] * d[k] for k in FOSSIL[sc]) / 1000 for sc in FOSSIL}
    s["fossil_co2_mt"] = sum(CO2_T_PER_MWH[k] * d[k] for k in d)
    dem = sum(v for k, v in d.items() if k != "rail_el")
    s["demand_total_twh"] = dem
    s["avg_cost_usd_mwh"] = total / dem
    s["lifecycle"] = screening_lifecycle(s)
    avoided = s["lifecycle"]["avoided_wtw_mtco2e"]
    s["abatement_usd_t"] = {sc: (total - v * 1000) / avoided for sc, v in s["fossil_cost_busd"].items()}
    s["seaweed_share_pct"] = (s["seaweed_hc_twh"] + fuels["seaweed ethanol"] + atj_from_seaweed * prm["atj"]["eff"]
                              + max(fuels["seaweed biomethane (net of fleet)"], 0)) / dem * 100
    s["build"] = build_list(s, prm, x, ev)
    return s


def build_list(s, prm, x, ev):
    c = s["capacity_gw"]; u = UNIT_CAPEX
    shelf = sum(v for k, v in s["seaweed_by_zone_km2"].items() if k.endswith(("shelf", "slope")))
    deep = s["seaweed_total_km2"] - shelf
    efuel_gw = (x["eFT_liquids"] + x["e_methanol"] + x["e_ammonia"] + x["e_methane"]) / (0.55 * 8.76)
    b = {"PV (GW)": c["PV"], "Onshore wind (GW)": c["Onshore wind"], "Geothermal (GW)": c["Geothermal"], "CSP (GW)": c["CSP"],
         "Electrolysers (GW)": s["electrolyser_gw"], "DAC (Mt CO2/yr)": s["co2_mt"]["DAC"],
         "Seaweed farms (km2)": s["seaweed_total_km2"], "Seaweed (Mt dry/yr)": s["seaweed_dry_mt"],
         "Seaweed (Mt wet/yr)": s["seaweed_wet_mt"], "Biorefineries (0.5 Mt dry/yr each)": s["seaweed_dry_mt"] / 0.5,
         "Harvest/transport vessels (1 Mt wet/yr each)": s["seaweed_wet_mt"],
         "PV land (km2)": c["PV"] * 1000 / prm["pv"]["mw_km2"]}
    capex = {"PV": c["PV"] * u["PV (USD/kW)"] / 1e3, "Onshore wind": c["Onshore wind"] * u["Onshore wind (USD/kW)"] / 1e3,
             "Geothermal": c["Geothermal"] * u["Geothermal (USD/kW)"] / 1e3, "CSP": c["CSP"] * u["CSP (USD/kW)"] / 1e3,
             "Electrolysers": s["electrolyser_gw"] * u["Electrolysers (USD/kW)"] / 1e3,
             "E-fuel synthesis": efuel_gw * u["E-fuel synthesis (USD/kW fuel)"] / 1e3,
             "DAC": s["co2_mt"]["DAC"] * u["DAC (USD per t/yr)"] / 1e3,
             "Seaweed farms": (shelf * u["Seaweed farm shelf (USD/km2)"] + deep * u["Seaweed farm deep (USD/km2)"]) / 1e9,
             "Biorefineries": s["seaweed_dry_mt"] * u["Biorefinery (USD per t dw/yr)"] / 1e3,
             "Vessels": s["seaweed_wet_mt"] * u["Vessel (USD each)"] / 1e9,
             "ATJ plants": x["ATJ_jet_from_ethanol"] / (0.9 * 8.76) * u["ATJ plant (USD/kW jet)"] / 1e3,
             "Solar heat (thermal storage, CSP heat)": (x["heat_pv_thermal_storage"] * u["Thermal storage + heaters (USD per MWh_th/yr)"]
                                                        + x["heat_csp_steam"] * u["CSP heat (USD per MWh_th/yr)"]) / 1e3,
             "Charging and grid": ev * u["Charging and grid (USD bn per TWh/yr of EV load)"]}
    b["capex_busd"] = capex
    b["capex_total_busd"] = sum(capex.values())
    b["capex_per_year_2027_2050_busd"] = b["capex_total_busd"] / 24
    return b


def merge(base, over):
    b = copy.deepcopy(base)
    for k, v in over.items():
        b[k] = {**b[k], **v} if isinstance(v, dict) and isinstance(b.get(k), dict) else v
    return b


if __name__ == "__main__":
    s = solve(base_params())
    print({k: round(v, 3) for k, v in demand().items()}, round(sum(demand().values()), 2))
    print("cost", round(s["total_cost_busd"], 3), "energy", round(s["energy_cost_busd"], 3), "veh", round(s["vehicle_premium_busd"], 3),
          "fossil", {k: round(v, 3) for k, v in s["fossil_cost_busd"].items()})
    print("gen", {k: round(v, 2) for k, v in s["generation_twh"].items()}, "GW", {k: round(v, 2) for k, v in s["capacity_gw"].items()})
    print("fuels", {k: round(v, 2) for k, v in s["fuels_twh"].items() if abs(v) > 1e-3})
    print("seaweed km2", round(s["seaweed_total_km2"]), s["seaweed_by_zone_km2"], s["seaweed_by_nutrient_method_km2"], s["seaweed_by_route_km2"])
    print("end use", {k: round(v, 2) for k, v in s["end_use_twh"].items()})
    print("heat", {k: round(v, 3) for k, v in s["heat_twh_th"].items()}, "co2", s["co2_mt"])
    print("marg", {k: round(v) for k, v in s["marginal_usd_mwh"].items()}, "LCA", round(s["lifecycle"]["reduction_pct"], 1))
