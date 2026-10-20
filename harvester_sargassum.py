"""Grid Harvester energy for tropical Sargassum farms (about 3 kg m-2 standing wet biomass per harvest).

The kelp reference of the harvester model (harvester_slurry.py) moves 12.5 kg m-2, i.e. 180 t wet per 1.44-ha cycle.
A Sargassum farm leaves about 3 kg m-2 per harvest, so the same cycle moves 43.2 t wet (4.32 t dry). The head, vessel
and cycle time are unchanged; the suction flow falls in proportion, and the hose is resized to keep 1.0 m s-1.
Hose form and skin drag scale with diameter; fairing reduces form drag by 80-90% (85% reference).
The conventional vessel is taken as 90.9 MJ per 1.44-ha cycle, as in the kelp reference.
Size reduction at sea, if needed to pass whole Sargassum thalli through the hose, is added per wet tonne:
coarse chopping 0.2 kWh t-1, fine maceration 1.0 kWh t-1.
Writes outputs/harvester_sargassum.json.
"""
import json
from pathlib import Path

import numpy as np

from harvester_slurry import RHO, G, L_HOSE, STATIC, K, ETA, MU_W, DM, BASE, CONV, T_CYCLE, friction_factor

OUT = Path(__file__).resolve().parent / "outputs"
CYCLE_M2 = 14_400.0
STANDING = 3.0                                    # kg wet m-2 per harvest
WET_T = STANDING * CYCLE_M2 / 1000                # 43.2 t wet per cycle
DRY_T = WET_T * DM                                # 4.32 t dry per cycle
M_WET = WET_T * 1000 / T_CYCLE                    # kg s-1
FORM_UNFAIRED_1P2 = BASE["form"] / (1 - 0.85)     # unfaired form drag at 1.20 m


def case(c=0.10, fairing=0.85, resize=True, chop_kwh_t=0.0, v_target=1.0):
    q = M_WET / (c * RHO)
    d = np.sqrt(4 * q / (np.pi * v_target)) if resize else BASE["d"]
    v = q / (np.pi * d ** 2 / 4)
    f = friction_factor(RHO * v * d / MU_W, d)
    h = STATIC + (K + f * L_HOSE / d) * v ** 2 / (2 * G)
    pump = RHO * G * q * h / ETA * T_CYCLE / 1e6
    form = FORM_UNFAIRED_1P2 * (1 - fairing) * d / BASE["d"]
    skin = BASE["skin"] * d / BASE["d"]
    chop = chop_kwh_t * WET_T * 3.6
    total = pump + form + skin + BASE["other"] + chop
    return dict(slurry_wet_fraction=c, fairing=fairing, diameter_m=d, velocity_m_s=v, head_m=h, pump_MJ=pump,
                hose_form_MJ=form, hose_skin_MJ=skin, head_vessel_MJ=BASE["other"], size_reduction_MJ=chop, total_MJ=total,
                conv_to_grid_ratio=CONV / total, reduction_pct=(1 - total / CONV) * 100,
                grid_MJ_per_dry_t=total / DRY_T, conventional_MJ_per_dry_t=CONV / DRY_T,
                saving_kWh_per_dry_t=(CONV - total) / DRY_T / 3.6)


CASES = {
    "bare hose": dict(fairing=0.0),
    "faired 80%": dict(fairing=0.80),
    "faired 85% (reference)": dict(fairing=0.85),
    "faired 90%": dict(fairing=0.90),
    "faired 85%, 30% slurry": dict(fairing=0.85, c=0.30),
    "faired 85%, 1.20-m hose": dict(fairing=0.85, resize=False),
    "faired 85% + coarse chopping 0.2 kWh/t": dict(fairing=0.85, chop_kwh_t=0.2),
    "faired 85% + fine maceration 1.0 kWh/t": dict(fairing=0.85, chop_kwh_t=1.0),
}

if __name__ == "__main__":
    res = {k: case(**kw) for k, kw in CASES.items()}
    out = dict(assumptions=dict(cycle_area_m2=CYCLE_M2, standing_wet_kg_m2=STANDING, dry_fraction=DM, wet_t_per_cycle=WET_T,
                                dry_t_per_cycle=DRY_T, wet_throughput_t_h=M_WET * 3.6, cycle_time_s=T_CYCLE,
                                conventional_cycle_energy_MJ=CONV, model_ratio_used=2.68),
               cases=res)
    json.dump(out, open(OUT / "harvester_sargassum.json", "w"), indent=1, default=float)
    for k, r in res.items():
        print(f"{k:42s} D={r['diameter_m']:.2f} m total={r['total_MJ']:6.1f} MJ ratio={r['conv_to_grid_ratio']:.2f} "
              f"reduction={r['reduction_pct']:5.1f}% saving={r['saving_kWh_per_dry_t']:+.2f} kWh/t dry")
