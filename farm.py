"""Native-seaweed farms in Costa Rican waters: zones, yields, nutrient supply and biomass cost (USD 2026).

Species
  Pacific    Sargassum liebmannii J. Agardh, a native brown alga of the Pacific coast, cultivated on floating
             long-lines in the Gulf of Nicoya and at Cuajiniquil (Radulovich et al. 2015, Aquaculture 436:40).
  Caribbean  Sargassum platycarpum Montagne, a native brown alga cultivated off Cahuita-Puerto Viejo at
             104.8 t fresh ha-1 yr-1 (about 10 t dry at 9.7% dry matter; Radulovich et al. 2015).
  The mean yield of the five Costa Rican species quantified in those trials was 9.3 t dry ha-1 yr-1.

Nutrient demand is met partly by natural supply (Papagayo upwelling, river plumes, the shallow eastern-
tropical-Pacific nitracline) and partly by one of:
  wave_pump      passive wave-driven pipe pump; field test off Hawaii delivered 16-45 m3/h per 0.75 m x 300 m
                 tube, ~10% of predictions, and failed structurally (White et al. 2010).
  wave_pump_xl   the same principle at 1.5 m diameter.
  solar_pipe     floating-PV-driven low-head pump in a 1.6 m x 400 m pipe.
  salt_fountain  heat-driven salt fountain (Stommel et al. 1956): needs surface water saltier than the
                 deep water (true in the Caribbean, where Subtropical Underwater overlies fresher Antarctic
                 Intermediate Water; not in the low-salinity eastern tropical Pacific).
  depth_cycling  farm grids lowered to the nitracline at night and raised to the light by day
                 (Navarrete et al. 2021, Macrocystis, 9-80 m daily). Off Pacific Costa Rica the nitracline lies at
                 ~20-60 m (Fiedler 2002; Pennington et al. 2006), within that range; in the Caribbean it is
                 deeper (~100-150 m), so cycling meets only part of the need.
"""
from dataclasses import dataclass, asdict
import json
from pathlib import Path

SECONDS_YR = 3.156e7
CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)
OUT = Path(__file__).resolve().parent / "outputs"
REF_YIELD = 15.0   # t dry/ha/yr at which the base farm cost is defined (Greene et al. 2020 scale)


@dataclass
class Zone:
    name: str
    yield_t_ha: float           # t dry / ha / yr with adequate nutrients
    n_frac: float               # tissue N, fraction of dry mass
    natural_n_share: float      # share of N demand met by natural supply
    nitrate_300m: float         # uM
    nitrate_400m: float
    nitrate_700m: float
    salt_fountain_ok: bool
    depth_cycle_effect: float   # share of the supplemental N need that depth cycling can meet
    species: str
    area_km2: dict              # free area (outside lanes and ports, beyond 6 nm, outside Cocos MPAs) by band
    mid_km: dict


def _areas():
    """Free areas from spatial.py (outputs/marine_space.json); falls back to the archived values."""
    archived = {"pac_shelf": {"0-50": 7184.0, "50-100": 718.0},
                "pac_slope": {"0-50": 6632.0, "50-100": 1765.0, "100-200": 1030.0, "200-370": 259.0},
                "pac_deep": {"0-50": 10032.0, "50-100": 23718.0, "100-200": 50821.0, "200-370": 83598.0},
                "car_shelf": {"0-50": 848.0},
                "car_slope": {"0-50": 4138.0, "50-100": 8.0},
                "car_deep": {"0-50": 3465.0, "50-100": 8475.0, "100-200": 5712.0}}
    f = OUT / "marine_space.json"
    if f.exists():
        return json.load(open(f))["free_area_by_zone_and_band_km2"]
    return archived


MID = {"0-50": 30, "50-100": 75, "100-200": 150, "200-370": 285}
A = _areas()
PAC = "Sargassum liebmannii (native, Pacific)"
CAR = "Sargassum platycarpum (native, Caribbean)"
ZONES = {
    "pac_shelf": Zone("Pacific shelf 0-200 m", 9.0, 0.014, 0.85, 35, 38, 42, False, 1.0, PAC, A["pac_shelf"], MID),
    "pac_slope": Zone("Pacific slope 200-1,000 m", 9.0, 0.014, 0.60, 35, 38, 42, False, 1.0, PAC, A["pac_slope"], MID),
    "pac_deep": Zone("Pacific deep >1,000 m", 9.0, 0.014, 0.30, 35, 38, 42, False, 1.0, PAC, A["pac_deep"], MID),
    "car_shelf": Zone("Caribbean shelf 0-200 m", 9.0, 0.014, 0.70, 15, 20, 28, True, 0.5, CAR, A["car_shelf"], MID),
    "car_slope": Zone("Caribbean slope 200-1,000 m", 9.0, 0.014, 0.40, 15, 20, 28, True, 0.5, CAR, A["car_slope"], MID),
    "car_deep": Zone("Caribbean deep >1,000 m", 8.0, 0.014, 0.10, 15, 20, 28, True, 0.5, CAR, A["car_deep"], MID),
}
for _z in ZONES.values():
    _z.mid_km = {b: MID[b] for b in _z.area_km2}


@dataclass
class FarmCost:
    base_eur_t: float = 340.0          # USD per dry t at 15 t/ha: long-line farm incl. harvest and 40 km transport
    deep_factor: float = 1.30          # deep moorings beyond 1,000 m
    slope_factor: float = 1.20
    transport_eur_t_wet_km: float = 0.023
    capture_eff: float = 0.25
    wave_unit_m3s: float = 0.0083
    wave_unit_capex: float = 68e3
    wave_unit_life: float = 5
    wave_xl_m3s: float = 0.033
    wave_xl_capex: float = 283e3
    solar_pipe_m3s_avg: float = 0.67
    solar_pipe_capex: float = 565e3
    solar_pipe_life: float = 15
    salt_m3s: float = 0.006
    salt_capex: float = 790e3
    salt_life: float = 15
    depth_cycle_capex_km2: float = 1.13e6
    depth_cycle_opex_km2: float = 56.5e3
    depth_cycle_life: float = 15
    om_frac: float = 0.03
    rate: float = 0.07
    dm_harvest: float = 0.10           # 9.7% dry matter (Radulovich et al. 2015)


def nitrate_gN_m3(uM):
    return uM * 1e-3 * 14.0


def nutrient_options(z: Zone, c: FarmCost):
    """USD per dry tonne of seaweed for each nutrient method (inf if not applicable)."""
    t_km2 = z.yield_t_ha * 100
    n_need = t_km2 * z.n_frac * 1000 * (1 - z.natural_n_share)
    out, units = {}, {}

    def pipe(q, capex, life, uM):
        kgN_unit = q * SECONDS_YR * nitrate_gN_m3(uM) * c.capture_eff / 1000
        n_units = n_need / kgN_unit if kgN_unit > 0 else float("inf")
        ann = n_units * capex * (CRF(c.rate, life) + c.om_frac)
        return ann / t_km2, n_units
    out["wave_pump"], units["wave_pump"] = pipe(c.wave_unit_m3s, c.wave_unit_capex, c.wave_unit_life, z.nitrate_300m)
    out["wave_pump_xl"], units["wave_pump_xl"] = pipe(c.wave_xl_m3s, c.wave_xl_capex, c.wave_unit_life, z.nitrate_300m)
    out["solar_pipe"], units["solar_pipe"] = pipe(c.solar_pipe_m3s_avg, c.solar_pipe_capex, c.solar_pipe_life, z.nitrate_400m)
    if z.salt_fountain_ok:
        out["salt_fountain"], units["salt_fountain"] = pipe(c.salt_m3s, c.salt_capex, c.salt_life, z.nitrate_700m)
    else:
        out["salt_fountain"], units["salt_fountain"] = float("inf"), 0
    out["depth_cycling"] = (c.depth_cycle_capex_km2 * CRF(c.rate, c.depth_cycle_life) + c.depth_cycle_opex_km2) / t_km2
    units["depth_cycling"] = 1.0
    m3_per_t = n_need / t_km2 * 1000 / (nitrate_gN_m3(z.nitrate_400m) * c.capture_eff) if n_need > 0 else 0.0
    return out, units, {"n_supplement_kgN_per_t": n_need / t_km2, "deep_water_m3_per_t_dw": m3_per_t}


def farm_cost(zone_key, band, c: FarmCost, method="depth_cycling", yield_override=None):
    z = ZONES[zone_key]
    y = yield_override or z.yield_t_ha
    factor = 1.0 if zone_key.endswith("shelf") else (c.slope_factor if zone_key.endswith("slope") else c.deep_factor)
    wet = 1 / c.dm_harvest
    transport = wet * max(z.mid_km[band] - 40, 0) * c.transport_eur_t_wet_km
    zz = Zone(**{**asdict(z), "yield_t_ha": y})
    nut, units, info = nutrient_options(zz, c)
    eff_yield = y
    if z.natural_n_share >= 1.0 or method == "natural":
        # natural supply only: yield is limited to the naturally supplied share
        method = "natural"
        eff_yield = y * min(1.0, z.natural_n_share)
        nut_cost = 0.0
    elif method == "depth_cycling" and z.depth_cycle_effect < 1.0:
        unmet = (1 - z.natural_n_share) * (1 - z.depth_cycle_effect)
        eff_yield = y * (1 - unmet)
        nut_cost = nut["depth_cycling"] * y / eff_yield
    else:
        nut_cost = nut[method]
    base = c.base_eur_t * factor * (0.4 + 0.6 * REF_YIELD / eff_yield)
    return dict(zone=zone_key, band=band, method=method, yield_t_ha=eff_yield, base_eur_t=base,
                transport_eur_t=transport, nutrient_eur_t=nut_cost, total_eur_t=base + transport + nut_cost,
                transport_km=z.mid_km[band], units_per_km2=units.get(method, 0), **info)


METHODS = ("natural", "depth_cycling", "solar_pipe", "wave_pump", "wave_pump_xl", "salt_fountain")

if __name__ == "__main__":
    c = FarmCost()
    tab = {}
    for k, z in ZONES.items():
        nut, units, info = nutrient_options(z, c)
        rows = {m: farm_cost(k, list(z.area_km2)[0], c, m) for m in METHODS}
        tab[k] = {"species": z.species, "nutrient_usd_per_t": {m: (v if v != float("inf") else None) for m, v in nut.items()},
                  "units_per_km2": units, **info,
                  "biomass_cost_nearest_band_usd_per_t": {m: (r["total_eur_t"] if r["total_eur_t"] != float("inf") else None)
                                                          for m, r in rows.items()},
                  "effective_yield_t_ha": {m: r["yield_t_ha"] for m, r in rows.items()}}
        print(k, {m: (round(v) if v is not None else "n/a") for m, v in tab[k]["biomass_cost_nearest_band_usd_per_t"].items()})
    json.dump(tab, open(OUT / "nutrient_supply_options.json", "w"), indent=1)
