"""Screening well-to-wheel lifecycle greenhouse-gas accounting for the solved system.

This layer evaluates the economic solution; it does not change the optimiser and is not an ISO 14040/44
process LCA. Functional unit: one year of the modelled transport energy service. Vehicle manufacture is
excluded. Electricity-generation factors are cradle-to-grave; fuel factors are fuel-cycle intensities that
already include the energy used to make the fuel, so that electricity is not counted a second time.

Central factors
  road gasoline/diesel 92 gCO2e/MJ (IPCC AR6 WGIII Ch. 10); fossil jet 89 (ICAO CORSIA); marine 93.3 (IMO)
  e-fuels with renewable electricity 12; renewable ammonia 3.2 (IPCC); residue and waste biofuels 25
  offshore macroalgal fuels 22 (Greene et al. 2020; range 14-29)
  electricity: PV 40, onshore wind 9.3, geothermal 38, CSP 23 gCO2e/kWh (NREL 2021; IPCC AR5 Annex III)
"""

FOSSIL_G_PER_MJ = {"ldv_gasoline": 92.0, "ldv_diesel": 92.0, "hdv": 92.0, "offroad": 92.0,
                   "aviation": 89.0, "shipping": 93.3}

ELECTRICITY_G_PER_KWH = {"PV": 40.0, "Onshore wind": 9.3, "Geothermal": 38.0, "CSP": 23.0}

FUEL_G_PER_MJ = {
    "eFT_liquids": 12.0, "e_methanol": 12.0, "e_ammonia": 3.2, "e_methane": 12.0,
    "ATJ_jet_from_ethanol": 25.0, "waste_biomethane": 25.0, "HEFA_waste_lipids": 25.0, "residue_FT": 25.0,
    "crop_ethanol_existing": 25.0,
    "seaweed HTL diesel/jet": 22.0, "seaweed ethanol": 22.0, "seaweed biomethane (net of fleet)": 22.0,
}
BIO = ("ATJ_jet_from_ethanol", "waste_biomethane", "HEFA_waste_lipids", "residue_FT", "crop_ethanol_existing")
SEA = ("seaweed HTL diesel/jet", "seaweed ethanol", "seaweed biomethane (net of fleet)")
EF = ("eFT_liquids", "e_methanol", "e_methane")

LOW_FACTORS = {"electricity": {"PV": 20.0, "Onshore wind": 7.0, "Geothermal": 6.0, "CSP": 15.0},
               "biofuel": 18.0, "seaweed": 14.0, "efuel": 8.0, "ammonia": 2.0}
HIGH_FACTORS = {"electricity": {"PV": 60.0, "Onshore wind": 15.0, "Geothermal": 80.0, "CSP": 40.0},
                "biofuel": 36.0, "seaweed": 29.0, "efuel": 25.0, "ammonia": 19.0}


def _electricity_intensity(s, factors):
    gen = s["generation_twh"]
    tot = sum(gen.values())
    return sum(gen[k] * factors[k] for k in gen) / tot if tot > 0 else 0.0


def _fuel_factors(bracket):
    f = dict(FUEL_G_PER_MJ)
    for k in BIO: f[k] = bracket["biofuel"]
    for k in SEA: f[k] = bracket["seaweed"]
    for k in EF: f[k] = bracket["efuel"]
    f["e_ammonia"] = bracket["ammonia"]
    return f


def fossil_lifecycle_mt(s):
    # 1 TWh = 3.6e9 MJ; 1 Mt = 1e12 g -> 0.0036
    return sum(s["demand_twh"].get(k, 0.0) * v * 0.0036 for k, v in FOSSIL_G_PER_MJ.items())


def lowcarbon_lifecycle_mt(s, electricity_factors=None, fuel_factors=None, parts=False):
    ef = electricity_factors or ELECTRICITY_G_PER_KWH
    ff = fuel_factors or FUEL_G_PER_MJ
    e_ci = _electricity_intensity(s, ef)
    direct_el = s["electricity_vehicles_rail_twh"] * e_ci * 0.001
    by = {k: max(v, 0.0) * ff[k] * 0.0036 for k, v in s["fuels_twh"].items()}
    if parts:
        return {"Direct electric transport": direct_el,
                "Seaweed fuels": sum(by[k] for k in SEA),
                "Residue and waste biofuels": sum(by[k] for k in BIO),
                "Electrofuels": sum(by[k] for k in EF) + by["e_ammonia"]}
    return direct_el + sum(by.values())


def screening_lifecycle(s):
    fossil = fossil_lifecycle_mt(s)
    low = lowcarbon_lifecycle_mt(s)
    lo = lowcarbon_lifecycle_mt(s, LOW_FACTORS["electricity"], _fuel_factors(LOW_FACTORS))
    hi = lowcarbon_lifecycle_mt(s, HIGH_FACTORS["electricity"], _fuel_factors(HIGH_FACTORS))
    return {"fossil_wtw_mtco2e": fossil, "lowcarbon_wtw_mtco2e": low, "lowcarbon_factor_sensitivity_mtco2e": [lo, hi],
            "avoided_wtw_mtco2e": fossil - low, "reduction_pct": 100.0 * (fossil - low) / fossil,
            "reduction_factor_sensitivity_pct": [100.0 * (fossil - hi) / fossil, 100.0 * (fossil - lo) / fossil],
            "parts_mtco2e": lowcarbon_lifecycle_mt(s, parts=True),
            "electricity_ci_gco2e_kwh": _electricity_intensity(s, ELECTRICITY_G_PER_KWH)}


def sampled_lifecycle(s, rng):
    tri = rng.triangular
    el = {"PV": tri(20, 40, 60), "Onshore wind": tri(7, 9.3, 15), "Geothermal": tri(6, 38, 80), "CSP": tri(15, 23, 40)}
    b = {"biofuel": tri(18, 25, 36), "seaweed": tri(14, 22, 29), "efuel": tri(8, 12, 25), "ammonia": tri(2, 3.2, 19)}
    low = lowcarbon_lifecycle_mt(s, el, _fuel_factors(b))
    fossil = fossil_lifecycle_mt(s)
    return low, fossil, 100.0 * (fossil - low) / fossil
