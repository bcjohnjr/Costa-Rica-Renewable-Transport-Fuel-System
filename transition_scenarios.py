"""The three headline cases for the full 2025 transport demand (learning costs, 4% finance, Grid Harvester).

drop-in rule        : least-cost system under the drop-in rule (aircraft and off-road machinery on drop-in liquids,
                      at least half of heavy-truck and bus demand on liquid fuel).
solar bridge        : fleet-compatible solar bridge. Light-duty BEVs <= 70%, heavy-duty battery trucks/buses <= 30%,
                      off-road machinery on liquids, >= 30% of gasoline-vehicle demand on renewable E85, every
                      biorefinery on the ethanol + residue-HTL route, all refinery heat from CSP steam, and co-located
                      CSP electricity covering the refineries' direct electrical load.
max electrification : the drop-in rule relaxed (heavy vehicles and machinery may electrify up to their deployment limits).
Writes outputs/transition_scenarios.json.
"""
import copy
import json
from pathlib import Path

import optimise as o
from scenarios import build_case

OUT = Path(__file__).resolve().parent / "outputs"
GRID_RATIO = 2.68

FLEET_RULES = {"ldv_bev_max_share": 0.70, "hdv_bet_max_share": 0.30, "offroad_el_max_share": 0.0, "e85_min_share": 0.30}
SOLAR_REFINERY = {"refinery_routes": ("EH",), "force_csp_heat": True, "csp_refinery_power": True}

CASE_OVERRIDES = {
    "dropin": {"force_csp_heat": True},
    "bridge": {"liquid_required": True, **FLEET_RULES, **SOLAR_REFINERY},
    "maxel": {"liquid_required": False, "force_csp_heat": True},
}
CASE_LABELS = {"dropin": "Drop-in rule", "bridge": "Fleet-compatible solar bridge", "maxel": "Maximum electrification"}


def with_grid_harvester(p, ratio=GRID_RATIO):
    p["fleet"]["grid_harvester"] = True
    p["fleet"]["grid_energy_ratio"] = ratio
    return p


def apply_case(p, key):
    for k, v in CASE_OVERRIDES[key].items():
        p[k] = copy.deepcopy(v)
    return p


def case(key, overrides=None, capital=True):
    """Full-demand learning case with the Grid Harvester; `overrides` are merged after the case definition."""
    p = build_case(learning=True, capital=capital, demand=False)
    apply_case(p, key)
    for k, v in (overrides or {}).items():
        p[k] = {**p[k], **v} if isinstance(v, dict) and isinstance(p.get(k), dict) else copy.deepcopy(v)
    return with_grid_harvester(p, (overrides or {}).get("fleet", {}).get("grid_energy_ratio", GRID_RATIO))


def bridge_steps():
    """Build-up of the solar bridge from the drop-in rule: fleet rules, then the ethanol route, then solar refineries."""
    return [("Drop-in rule", case("dropin")),
            ("+ fleet-compatibility rules", case("dropin", {"liquid_required": True, **FLEET_RULES})),
            ("+ ethanol route at every refinery", case("dropin", {"liquid_required": True, **FLEET_RULES, "refinery_routes": ("EH",)})),
            ("+ CSP heat and refinery power (solar bridge)", case("bridge"))]


if __name__ == "__main__":
    res = {}
    for k in CASE_OVERRIDES:
        r = o.solve(case(k))
        res[k] = r
        print(k, "cost", round(r["total_cost_busd"], 3), "el", round(r["electricity_delivered_twh"], 2),
              "vehicle el", round(r["electricity_vehicles_rail_twh"], 2), "seaweed km2", round(r["seaweed_total_km2"]),
              "CSP GW", round(r["capacity_gw"].get("CSP", 0), 2))
    json.dump(res, open(OUT / "transition_scenarios.json", "w"), indent=1, default=float)
