"""Offshore wind and PVT joint optimization (Supplementary Note 20; Table 6, Supplementary Table S28).

Extends the drop-in learning case (transition_scenarios.case("dropin")) with
  * the FAO historic-demand cap on domestically sold recovered potassium (37,107 t K/yr), and
  * optional or imposed offshore wind and PVT slurry preheating, through the optional
    `offshore` and `pvt` hooks of optimise.solve (inactive in every national case).

Every assumption is stated in ASSUMPTIONS and written to outputs/hybrid_offshore_pvt.json.
Writes outputs/hybrid_offshore_pvt.json.
"""
import copy
import json
from pathlib import Path

import optimise as o
import transition_scenarios as T

OUT = Path(__file__).resolve().parent / "outputs"

# FAO inorganic-fertilizer use, Costa Rica 2020: about 44,700 t K2O -> 44,700 * 2*39.098/94.196 t K.
FAO_K_CAP_MT = 44700 * (2 * 39.098 / 94.196) / 1e6

CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)

ASSUMPTIONS = dict(
    offshore=dict(
        mw=540.0,
        ice_twh=2.986,              # ICE feasibility estimate for the 540 MW Punta Descartes stage (capacity factor 63.1%)
        availability=0.90,          # imposed deployment delivers 90% of the ICE estimate
        lcoe=79.0,                  # USD/MWh: IRENA 2024 global weighted-average offshore LCOE (USD 0.079/kWh),
                                    # not credited with ICE's higher projected capacity factor
        adder_direct=17.0,          # integration adder, as onshore wind (Supplementary Table S4 adders)
        adder_flex=20.0,
        heater_max_share=0.20,      # offshore electricity may supply at most 20% of refinery heat via the electric heater
    ),
    pvt=dict(
        area_km2=0.20,              # collector aperture
        ghi_kwh_m2=1850.0,          # global horizontal irradiation, Costa Rican lowland screening value
        el_eff=0.14,                # annual electrical yield / GHI
        th_eff=0.19,                # annual useful heat at 25->65 C / GHI
        capex_usd_m2=300.0,         # installed PVT collectors, heat exchanger and loop
        om_share=0.015,             # annual O&M as share of capex
        r=0.04, life=20,
        preheat_share=0.15,         # PVT heat cannot exceed 15% of refinery heat (25->65 C slurry preheat)
    ),
)


def pvt_hook(imposed=True):
    a = ASSUMPTIONS["pvt"]
    annual_usd_m2 = a["capex_usd_m2"] * (CRF(a["r"], a["life"]) + a["om_share"])
    return dict(heat_twh_km2=a["ghi_kwh_m2"] * a["th_eff"] / 1e3,      # kWh/m2 -> TWh/km2
                el_twh_km2=a["ghi_kwh_m2"] * a["el_eff"] / 1e3,
                annual_cost_musd_km2=annual_usd_m2,                    # USD/m2 -> MUSD/km2
                max_km2=a["area_km2"], min_km2=a["area_km2"] if imposed else 0.0,
                preheat_share=a["preheat_share"])


def offshore_hook(imposed=True, lcoe=None):
    a = ASSUMPTIONS["offshore"]
    return dict(twh=a["ice_twh"] * a["availability"], imposed=imposed,
                lcoe=a["lcoe"] if lcoe is None else lcoe,
                adder_direct=a["adder_direct"], adder_flex=a["adder_flex"],
                heater_max_share=a["heater_max_share"])


def fao(p):
    p["fert"]["cap_mt"] = {**p["fert"]["cap_mt"], "k": FAO_K_CAP_MT}
    return p


MODES = {
    "base": lambda: T.case("dropin"),
    "base_fao": lambda: fao(T.case("dropin")),
    "wind": lambda: {**fao(T.case("dropin")), "offshore": offshore_hook(True)},
    "pvt": lambda: {**fao(T.case("dropin")), "pvt": pvt_hook(True)},
    "hybrid": lambda: {**fao(T.case("dropin")), "offshore": offshore_hook(True), "pvt": pvt_hook(True)},
    "hybrid_optional": lambda: {**fao(T.case("dropin")), "offshore": offshore_hook(False), "pvt": pvt_hook(False)},
}


def row(r):
    hy = r.get("hybrid", {})
    return dict(cost_busd=r["total_cost_busd"], offshore_twh=hy.get("offshore_twh", 0.0),
                offshore_heat_twh=hy.get("offshore_heat_twh", 0.0),
                pvt_heat_twh=hy.get("pvt_heat_twh", 0.0), pvt_el_twh=hy.get("pvt_el_twh", 0.0),
                cst_heat_twh=r["heat_twh_th"]["CSP steam"], seaweed_km2=r["seaweed_total_km2"],
                seaweed_dry_mt=r["seaweed_dry_mt"], refinery_heat_twh=r["seaweed_refinery_heat_twh"],
                fertiliser_mt=r["fertiliser_mt"])


# Nutrient chain for the hybrid case (Supplementary Note 22, Table S31, Figure 10).
NUTRIENTS = dict(
    content=dict(N=0.014, P=0.0022),            # dry-mass nutrient content assimilated by the farms
    fao_use_t=dict(N=94500, P2O5=21300, K2O=44700),   # FAO national inorganic-fertilizer use, 2020
    manufacturing_gj_t=dict(N=40.0, P=15.0, K=8.0),   # avoided industrial manufacturing energy per t element
    acceptance=(0.0, 0.25, 0.50, 0.75, 1.00),   # fraction passing the quality-control gate
)


def nutrients(h):
    a = NUTRIENTS
    dry_t = h["seaweed_dry_mt"] * 1e6
    rec = {k: v * 1e6 for k, v in h["fertiliser_mt"].items()}           # recovered elements, t/yr (LP output)
    capped = dict(N=min(rec["N"], a["fao_use_t"]["N"]),
                  P=min(rec["P"], a["fao_use_t"]["P2O5"] * 2 * 30.974 / 141.943),
                  K=min(rec["K"], FAO_K_CAP_MT * 1e6))
    rows = []
    for f in a["acceptance"]:
        d = {k: v * f for k, v in capped.items()}
        rows.append(dict(fraction=f, N_t=d["N"], P_t=d["P"], K_t=d["K"],
                         energy_pj=sum(d[k] * a["manufacturing_gj_t"][k] for k in d) / 1e6))
    return dict(assumptions=a, assimilated_t={k: dry_t * c for k, c in a["content"].items()},
                recovered_t=rec, recovered_k2o_t=rec["K"] * 94.196 / (2 * 39.098),
                deliverable_t=capped, S31=rows)


def run():
    res = {"assumptions": ASSUMPTIONS, "fao_k_cap_mt": FAO_K_CAP_MT, "modes": {}}
    for k, f in MODES.items():
        res["modes"][k] = row(o.solve(f()))
    sweep = []
    for lc in (40, 58, 79, 91, 105, 123, 135):
        p = {**fao(T.case("dropin")), "offshore": offshore_hook(True, lc), "pvt": pvt_hook(True)}
        r = row(o.solve(p))
        sweep.append(dict(offshore_lcoe_usd_mwh=lc, hybrid_cost_busd=r["cost_busd"],
                          premium_vs_base_fao_musd=(r["cost_busd"] - res["modes"]["base_fao"]["cost_busd"]) * 1000,
                          seaweed_km2=r["seaweed_km2"], cst_heat_twh=r["cst_heat_twh"]))
    res["hybrid_offshore_lcoe_sweep"] = sweep
    res["nutrients"] = nutrients(res["modes"]["hybrid"])
    json.dump(res, open(OUT / "hybrid_offshore_pvt.json", "w"), indent=1, default=float)
    return res


if __name__ == "__main__":
    R = run()
    for k, v in R["modes"].items():
        print(f"{k:16s} cost {v['cost_busd']:.3f}  offshore {v['offshore_twh']:.3f}  PVT heat {v['pvt_heat_twh']:.3f}  "
              f"CST {v['cst_heat_twh']:.3f}  seaweed {v['seaweed_km2']:.0f} km2")
    for s in R["hybrid_offshore_lcoe_sweep"]:
        print(f"offshore LCOE {s['offshore_lcoe_usd_mwh']:>4}  hybrid {s['hybrid_cost_busd']:.3f}  premium {s['premium_vs_base_fao_musd']:+.0f} MUSD  seaweed {s['seaweed_km2']:.0f}")
