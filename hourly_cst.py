"""Synthetic 8,760-hour test of high-temperature CST heat (Supplementary Notes 18 and 23;
Figure 9, Supplementary Tables S26, S29, S32-S34, Supplementary Figures S5, S6 and S8).

Not an hourly re-optimization: refinery high-temperature heat demand is held constant at its annual mean and
a CST field (collector multiple of the annual-energy size) with a hot store serves it hour by hour.
Profiles are constructed, seeded and documented in PROFILE; they are not measured Costa Rican weather.

Dispatch order each hour: solar field -> hot store -> optional electric heater fed by a fixed share of the
hourly offshore wind output -> unserved. Surplus collection charges the store; collection beyond a full store
is curtailed. Storage hours are expressed relative to the mean high-temperature demand.

Reads outputs/hybrid_offshore_pvt.json and outputs/transition_scenarios.json; writes outputs/hourly_cst.json.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"

PROFILE = dict(
    seed=20261021,
    latitude_deg=10.6,                         # Guanacaste
    # Relative monthly clear-day likelihood (dry season Dec-Apr, wet season May-Nov, July-August veranillo);
    # scaled so that the expected annual DNI equals FIELD["dni_kwh_m2"] (see clear_probabilities)
    p_clear_shape=[0.90, 0.92, 0.92, 0.85, 0.45, 0.35, 0.50, 0.45, 0.30, 0.25, 0.45, 0.80],
    persistence=0.5,                           # lag-1 correlation of the clear/cloudy day sequence
    cloudy_dni_ratio=0.35,                     # cloudy-day DNI relative to clear sky (2.0/5.75 in Figure S5)
    cloudy_ghi_ratio=0.55,                     # cloudy-day global irradiance, for PVT preheat
    # Offshore wind: Papagayo-jet season (Dec-Apr) strong, wet season weaker; diurnal +/-10%; daily AR(1) noise
    wind_season=[1.45, 1.50, 1.45, 1.30, 0.80, 0.70, 0.85, 0.80, 0.60, 0.55, 0.75, 1.30],
    wind_diurnal_amp=0.10, wind_ar=0.7, wind_sigma=0.15,
    offshore_cf=0.631 * 0.90,                  # ICE estimate with the 90% delivery factor
)
FIELD = dict(dni_kwh_m2=1400.0, field_to_process=0.42, packing=0.42)   # Section 3.8 screening values
UPGRADE = dict(field_mult=2.25, storage_h=96,
               # cost parameters of the post-optimization firming screen (Supplementary Table S34)
               collector_usd_m2=222.6, store_usd_kwh=(15, 30, 60),
               annual_factor_field=0.0785, annual_factor_store=0.0745)


def clear_sky(p=PROFILE):
    hours = np.arange(8760)
    doy = hours // 24; hod = hours % 24 + 0.5
    decl = np.radians(23.44) * np.sin(2 * np.pi * (284 + doy + 1) / 365)
    lat = np.radians(p["latitude_deg"])
    ha = np.radians(15 * (hod - 12))
    sin_el = np.sin(lat) * np.sin(decl) + np.cos(lat) * np.cos(decl) * np.cos(ha)
    am = np.where(sin_el > 0.02, 1 / np.maximum(sin_el, 0.02), np.inf)
    dni_cs = np.where(sin_el > 0.02, 1000 * 0.7 ** (am ** 0.678), 0.0)       # W/m2, Meinel attenuation
    ghi_cs = np.where(sin_el > 0, 1000 * sin_el * 0.75, 0.0)
    return doy, hod, dni_cs, ghi_cs


def clear_probabilities(p=PROFILE):
    """Scale the monthly clear-day shape so the expected annual DNI equals the paper's central DNI."""
    doy, _, dni_cs, _ = clear_sky(p)
    month = np.minimum((np.arange(365) / 30.42).astype(int), 11)
    cs_day = np.bincount(doy, dni_cs) / 1000                                   # kWh/m2 per clear day
    shape = np.array(p["p_clear_shape"])[month]
    r = p["cloudy_dni_ratio"]
    lo, hi = 0.0, 1.0 / shape.max()
    for _ in range(60):
        k = (lo + hi) / 2
        annual = (cs_day * (k * shape + r * (1 - k * shape))).sum()
        lo, hi = (k, hi) if annual < FIELD["dni_kwh_m2"] else (lo, k)
    return list(np.clip(k * np.array(p["p_clear_shape"]), 0, 1)), float(cs_day.sum())


def profiles(p=PROFILE):
    rng = np.random.default_rng(p["seed"])
    days = np.arange(365)
    month = np.minimum((days / 30.42).astype(int), 11)
    p_clear, _ = clear_probabilities(p)
    # clear/cloudy day sequence: two-state Markov chain with monthly stationary probability
    clear = np.zeros(365, bool)
    for d in days:
        pc = p_clear[month[d]]
        if d == 0:
            prob = pc
        else:
            prob = pc + p["persistence"] * (1 - pc) if clear[d - 1] else pc * (1 - p["persistence"])
        clear[d] = rng.random() < prob
    doy, hod, dni_cs, ghi_cs = clear_sky(p)
    day_clear = clear[doy]
    dni = dni_cs * np.where(day_clear, 1.0, p["cloudy_dni_ratio"])
    ghi = ghi_cs * np.where(day_clear, 1.0, p["cloudy_ghi_ratio"])
    # offshore wind
    noise = np.zeros(365); e = rng.normal(0, p["wind_sigma"], 365)
    for d in days[1:]:
        noise[d] = p["wind_ar"] * noise[d - 1] + e[d]
    w = np.array(p["wind_season"])[month[doy]] * (1 + noise[doy]) * (1 + p["wind_diurnal_amp"] * np.cos(2 * np.pi * (hod - 3) / 24))
    w = np.clip(w, 0, None)
    w = w / w.mean()
    w = np.minimum(w, 1 / p["offshore_cf"]); w = w / w.mean()
    # vehicle charging (illustration, Figure S5): overnight base, morning and evening peaks
    ch = 0.82 + 0.28 * np.exp(-((hod - 8.5) / 1.6) ** 2) + 0.62 * np.exp(-((hod - 19) / 1.8) ** 2)
    ch = ch / ch.mean()
    # Normalized to the annual mean: a field sized on annual energy (field_mult = 1) collects exactly
    # the annual duty. The realized annual DNI sets only the hourly timing; areas use FIELD["dni_kwh_m2"].
    return dict(dni=dni / dni.mean(), ghi=ghi / ghi.mean(), wind=w, charge=ch, clear_days=int(day_clear[::24].sum()),
                annual_dni_kwh_m2=float(dni.sum() / 1000), p_clear=p_clear)


def simulate(P, demand_twh, field_mult, storage_h, solar_scale=1.0, wind_share=0.0, wind_twh=0.0,
             pvt_twh=0.0, pvt_max_share=0.15):
    """Hourly balance. Returns unserved share of demand, unserved hours, curtailment and PVT heat used."""
    D = demand_twh * 1e6 / 8760                                     # MW_th, constant
    collect = field_mult * D * P["dni"] * solar_scale                # field sized on annual energy
    wind_heat = wind_share * wind_twh * 1e6 / 8760 * P["wind"] * 0.99
    pvt = pvt_twh * 1e6 / 8760 * P["ghi"]
    pvt_used = np.minimum(pvt, pvt_max_share * D)
    need = D - pvt_used
    cap = storage_h * D
    soc = 0.5 * cap; unserved = np.zeros(8760); curtail = 0.0
    for t in range(8760):
        surplus = collect[t] - need[t]
        if surplus >= 0:
            room = cap - soc
            soc += min(surplus, room); curtail += max(surplus - room, 0.0)
        else:
            deficit = -surplus
            draw = min(deficit, soc); soc -= draw; deficit -= draw
            deficit -= min(deficit, wind_heat[t])
            unserved[t] = deficit
    tot = need.sum()
    return dict(unserved_pct=100 * unserved.sum() / (D * 8760), unserved_hours=int((unserved > 1e-6 * D).sum()),
                curtailment_twh=curtail / 1e6, pvt_used_twh=pvt_used.sum() / 1e6)


def field_km2(q_twh, dni=FIELD["dni_kwh_m2"]):
    return q_twh * 1e9 / (dni * FIELD["field_to_process"]) / FIELD["packing"] / 1e6


def run():
    P = profiles()
    H = json.load(open(OUT / "hybrid_offshore_pvt.json"))["modes"]
    dropin_q = json.load(open(OUT / "transition_scenarios.json"))["dropin"]["heat_twh_th"]["CSP steam"]
    hy = H["hybrid"]
    hybrid_q = hy["refinery_heat_twh"]                       # high-temperature duty before PVT preheat
    res = dict(profile=PROFILE, field=FIELD, upgrade=UPGRADE, clear_days=P["clear_days"], p_clear=P["p_clear"],
               annual_dni_kwh_m2=P["annual_dni_kwh_m2"], clear_sky_dni_kwh_m2=clear_probabilities()[1],
               dropin_heat_twh=dropin_q, hybrid_heat_twh=hybrid_q, hybrid_offshore_twh=hy["offshore_twh"],
               hybrid_pvt_twh=hy["pvt_heat_twh"])
    # S26: drop-in duty, field x storage
    res["S26"] = [dict(field_mult=m, storage_h=s, field_km2=field_km2(dropin_q) * m, **simulate(P, dropin_q, m, s))
                  for m in (1, 1.5, 2, 3) for s in (12, 24, 48, 168)]
    # S29: hybrid duty with PVT preheat, 48 h store, share of offshore output to the heater
    res["S29"] = [dict(field_mult=m, wind_share=w, **simulate(P, hybrid_q, m, 48, wind_share=w, wind_twh=hy["offshore_twh"],
                                                                  pvt_twh=hy["pvt_heat_twh"]))
                  for m in (1.0, 1.5, 2.0, 3.0) for w in (0.0, 0.10, 0.20)]
    # Figure S6: 10% diversion, storage 12/48/168 h
    res["S6"] = [dict(field_mult=m, storage_h=s, **simulate(P, hybrid_q, m, s, wind_share=0.10, wind_twh=hy["offshore_twh"],
                                                             pvt_twh=hy["pvt_heat_twh"]))
                 for s in (12, 48, 168) for m in (1.0, 1.5, 2.0, 3.0)]
    # S32: firming stress, reference and 25% less irradiance
    res["S32"] = [dict(field_mult=m, storage_h=s, solar=sc, **simulate(P, hybrid_q, m, s, solar_scale=sc, pvt_twh=hy["pvt_heat_twh"]))
                  for (m, s) in ((1.0, 48), (1.7, 72), (2.0, 96), (2.25, 96), (2.5, 96)) for sc in (1.0, 0.75)]
    # S33: collector field by irradiance for the hybrid CST duty; S34: firming investment
    cst_q = hybrid_q - hy["pvt_heat_twh"]
    res["S33"] = [dict(dni=d, annual_km2=field_km2(cst_q, d), upgraded_km2=UPGRADE["field_mult"] * field_km2(cst_q, d),
                       extra_km2=(UPGRADE["field_mult"] - 1) * field_km2(cst_q, d)) for d in (1000, 1200, 1400, 1700, 2000)]
    extra_m2 = (UPGRADE["field_mult"] - 1) * field_km2(cst_q) * 1e6
    store_kwh = UPGRADE["storage_h"] * cst_q * 1e9 / 8760
    res["S34"] = []
    for c in UPGRADE["store_usd_kwh"]:
        cf = extra_m2 * UPGRADE["collector_usd_m2"] / 1e9; cs = store_kwh * c / 1e9
        add = cf * UPGRADE["annual_factor_field"] + cs * UPGRADE["annual_factor_store"]
        res["S34"].append(dict(store_usd_kwh=c, capex_busd=cf + cs, extra_annual_busd=add, hybrid_with_upgrade_busd=hy["cost_busd"] + add))
    res["store_gwh"] = store_kwh / 1e6
    # Figure S5: first ten days of the profiles
    res["S5_first_240h"] = {k: P[k][:240].tolist() for k in ("dni", "wind", "charge")}
    json.dump(res, open(OUT / "hourly_cst.json", "w"), indent=1, default=float)
    return res


if __name__ == "__main__":
    R = run()
    print("annual DNI", round(R["annual_dni_kwh_m2"]), "clear-sky", round(R["clear_sky_dni_kwh_m2"]), "p_clear", [round(x, 2) for x in R["p_clear"]])
    print("clear days", R["clear_days"], "| drop-in duty", round(R["dropin_heat_twh"], 4), "| hybrid duty", round(R["hybrid_heat_twh"], 4))
    for r in R["S26"]:
        print(f"S26 field {r['field_mult']:>4} store {r['storage_h']:>3} h  area {r['field_km2']:5.2f}  unserved {r['unserved_pct']:6.2f}%  {r['unserved_hours']:5d} h  curtail {r['curtailment_twh']:.3f}")
    for r in R["S29"]:
        print(f"S29 field {r['field_mult']:>4} wind {r['wind_share']:.0%}  unserved {r['unserved_pct']:6.2f}%  {r['unserved_hours']:5d} h  PVT used {r['pvt_used_twh']:.3f}")
    for r in R["S32"]:
        print(f"S32 field {r['field_mult']:>4} store {r['storage_h']:>3} solar {r['solar']:.0%}  unserved {r['unserved_pct']:6.2f}%  {r['unserved_hours']:5d} h")
    for r in R["S33"]:
        print(f"S33 DNI {r['dni']}  {r['annual_km2']:.2f}  {r['upgraded_km2']:.2f}  {r['extra_km2']:.2f}")
    for r in R["S34"]:
        print(f"S34 store {r['store_usd_kwh']}  capex {r['capex_busd']:.3f}  annual {r['extra_annual_busd']:.3f}  total {r['hybrid_with_upgrade_busd']:.3f}")
    print("store GWh", round(R["store_gwh"], 2))
