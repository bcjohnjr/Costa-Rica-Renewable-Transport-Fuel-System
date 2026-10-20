"""Wet Sargassum biorefinery without thermal drying, per dry tonne of seaweed (USD 2026).

Routes (none dries seaweed thermally; fermentation, HTL and digestion all run on wet feed):
  EH  ensiled seaweed -> press -> enzymatic hydrolysis (incl. alginate lyase) -> fermentation -> distillation
      -> ethanol; stillage solids -> hydrothermal liquefaction (HTL, ~350 C) -> biocrude -> hydrotreating
      with H2 from solid-oxide electrolysis -> renewable diesel/jet; HTL aqueous phase -> anaerobic digestion.
  H   whole-seaweed HTL -> hydrotreating; aqueous phase -> digestion.
  A   anaerobic digestion only.
Process heat is supplied in optimise.py by solar heat (concentrated-solar steam, or PV-charged high-temperature
thermal storage), industrial heat pumps or electric boilers. No nuclear or fossil heat is used.

Composition (dry basis) for native Sargassum: ash 33% (Feedipedia mean 35.9%, range 18-51%; Diaz-Vazquez
et al. 2015: 27.5%); alginate 20%; mannitol 4%; laminarin 2%; cellulose 6%; fucoidan 7%; protein 9%
(N 1.4%); lipid 1.2%; P 0.22%; K 4.6%.
HTL: Sargassum spp. 18.4% bio-oil on an ash-free basis at 350 C, HHV 32.3 MJ/kg (Diaz-Vazquez et al. 2015,
13% on a dry basis at 27.5% ash); S. patens 32.1% dry basis (Li et al. 2012). Central 15% dry basis.
Ethanol: 0.41 g/g of fermented sugar with engineered alginate pathway (Wargacki et al. 2012).
Arsenic: Sargassum accumulates arsenic. Nutrients are recovered as precipitated salts (struvite, ammonium
sulphate, potassium sulphate) from treated process water, not by land application of digestate.
"""
from dataclasses import dataclass, asdict
import json
from pathlib import Path

LHV_ETOH = 26.8e-3   # GJ/kg
LHV_HC = 43.2e-3     # GJ/kg hydrotreated hydrocarbons
LHV_CH4_NM3 = 35.8e-3
OUT = Path(__file__).resolve().parent / "outputs"


@dataclass
class Feed:
    ash: float = 0.33
    mannitol: float = 0.04
    laminarin: float = 0.02
    cellulose: float = 0.06
    alginate: float = 0.20
    fucoidan: float = 0.07
    protein: float = 0.09
    lipid: float = 0.012
    n: float = 0.014
    p: float = 0.0022
    k: float = 0.046
    carb_factor: float = 1.0


@dataclass
class Proc:
    ensile_sugar_loss: float = 0.08
    cellulose_access: float = 0.8
    alginate_use: float = 0.5
    etoh_per_sugar: float = 0.41
    distill_gj_per_t_etoh: float = 8.0
    htl_biocrude_resid: float = 0.22
    htl_biocrude_whole: float = 0.15
    biocrude_hhv: float = 33.0
    ht_yield: float = 0.82
    ht_h2: float = 0.035
    jet_cut: float = 0.40
    htl_solids: float = 0.15
    htl_dh_mj_kg: float = 1.35
    htl_heat_recovery: float = 0.80
    htl_topping_electric: float = 0.30
    aq_cod_resid: float = 0.25
    aq_cod_whole: float = 0.25
    aq_ch4_nm3_kgcod: float = 0.25
    aq_inhibition: float = 0.70
    ad_ch4_nm3_kgvs: float = 0.20      # Sargassum BMP is lower than kelp (polyphenols, high ash)
    soec_kwh_e_kg: float = 38.0
    soec_kwh_th_kg: float = 8.0
    el_base_mwh: float = 0.135
    ad_heat_gj: float = 0.2
    n_recovery: float = 0.60
    p_recovery: float = 0.80
    k_recovery: float = 0.80
    # costs, USD per dry tonne (annualised capital + O&M, 7%), excluding energy
    cost_ensile: float = 23.0
    cost_press_hydrolysis_enzymes: float = 51.0
    cost_ferment_distill: float = 45.0
    cost_htl: float = 68.0
    cost_htl_whole: float = 107.0
    cost_ht: float = 28.0
    cost_ad: float = 17.0
    cost_ad_whole: float = 79.0
    cost_nutrients: float = 22.0       # incl. arsenic-selective precipitation of recovered salts
    gj_per_t_n: float = 40.0
    gj_per_t_p: float = 15.0
    gj_per_t_k: float = 8.0
    co2_per_t_n: float = 2.7
    co2_per_t_p: float = 1.5
    co2_per_t_k: float = 0.6


def _fert(f, p):
    n, ph, k = f.n * p.n_recovery * 1000, f.p * p.p_recovery * 1000, f.k * p.k_recovery * 1000
    return dict(fert_n_kg=n, fert_p_kg=ph, fert_k_kg=k,
                fert_energy_gj=(n * p.gj_per_t_n + ph * p.gj_per_t_p + k * p.gj_per_t_k) / 1000,
                fert_co2_t=(n * p.co2_per_t_n + ph * p.co2_per_t_p + k * p.co2_per_t_k) / 1000)


def route_eh(f=Feed(), p=Proc()):
    sugars = f.carb_factor * ((f.mannitol + f.laminarin) * (1 - p.ensile_sugar_loss) + f.cellulose * p.cellulose_access
                              + f.alginate * p.alginate_use)
    etoh = sugars * p.etoh_per_sugar
    vs = 1 - f.ash
    resid_org = max(vs - sugars, 0.05)
    biocrude = resid_org * p.htl_biocrude_resid
    hc = biocrude * p.ht_yield
    h2_kg = biocrude * p.ht_h2 * 1000
    slurry = (resid_org + f.ash * 0.4) / p.htl_solids
    htl_heat = slurry * p.htl_dh_mj_kg * (1 - p.htl_heat_recovery)
    ch4 = resid_org * p.aq_cod_resid * 1000 * p.aq_ch4_nm3_kgcod * p.aq_inhibition * LHV_CH4_NM3
    el = p.el_base_mwh + htl_heat * p.htl_topping_electric / 3.6 + h2_kg * p.soec_kwh_e_kg / 1000
    heat = (etoh * p.distill_gj_per_t_etoh + htl_heat * (1 - p.htl_topping_electric)
            + h2_kg * p.soec_kwh_th_kg * 3.6e-3 + p.ad_heat_gj)
    out = dict(route="EH", ethanol_t=etoh, ethanol_gj=etoh * 1000 * LHV_ETOH, hc_gj=hc * 1000 * LHV_HC,
               jet_gj=hc * 1000 * LHV_HC * p.jet_cut, ch4_gj=ch4, el_mwh=el, heat_mwh_th=heat / 3.6,
               h2_kg=h2_kg, co2_ferm_t=etoh * 44 / 46, biocrude_t=biocrude,
               cost_eur=(p.cost_ensile + p.cost_press_hydrolysis_enzymes + p.cost_ferment_distill + p.cost_htl
                         + p.cost_ht + p.cost_ad + p.cost_nutrients))
    out.update(_fert(f, p))
    return out


def route_h(f=Feed(), p=Proc()):
    biocrude = p.htl_biocrude_whole
    hc = biocrude * p.ht_yield
    h2_kg = biocrude * p.ht_h2 * 1000
    slurry = 1 / p.htl_solids
    htl_heat = slurry * p.htl_dh_mj_kg * (1 - p.htl_heat_recovery)
    ch4 = (1 - f.ash) * p.aq_cod_whole * 1000 * p.aq_ch4_nm3_kgcod * p.aq_inhibition * LHV_CH4_NM3
    el = 0.09 + htl_heat * p.htl_topping_electric / 3.6 + h2_kg * p.soec_kwh_e_kg / 1000
    heat = htl_heat * (1 - p.htl_topping_electric) + h2_kg * p.soec_kwh_th_kg * 3.6e-3 + p.ad_heat_gj
    out = dict(route="H", ethanol_t=0.0, ethanol_gj=0.0, hc_gj=hc * 1000 * LHV_HC, jet_gj=hc * 1000 * LHV_HC * p.jet_cut,
               ch4_gj=ch4, el_mwh=el, heat_mwh_th=heat / 3.6, h2_kg=h2_kg, co2_ferm_t=0.0, biocrude_t=biocrude,
               cost_eur=p.cost_ensile + 17 + p.cost_htl_whole + p.cost_ht + p.cost_ad + p.cost_nutrients)
    out.update(_fert(f, p))
    return out


def route_a(f=Feed(), p=Proc()):
    vs = 1 - f.ash
    ch4_nm3 = vs * 1000 * p.ad_ch4_nm3_kgvs
    out = dict(route="A", ethanol_t=0.0, ethanol_gj=0.0, hc_gj=0.0, jet_gj=0.0, ch4_gj=ch4_nm3 * LHV_CH4_NM3,
               el_mwh=0.05 + ch4_nm3 * 1.82 * 0.25e-3, heat_mwh_th=0.4 / 3.6, h2_kg=0.0,
               co2_ferm_t=ch4_nm3 * 0.82 * 1.977e-3, biocrude_t=0.0,
               cost_eur=p.cost_ensile + p.cost_ad_whole + p.cost_nutrients)
    out.update(_fert(f, p))
    return out


def routes(f=Feed(), p=Proc()):
    return {r["route"]: r for r in (route_eh(f, p), route_h(f, p), route_a(f, p))}


if __name__ == "__main__":
    R = routes()
    for k, v in R.items():
        print(k, {a: round(b, 3) if isinstance(b, float) else b for a, b in v.items()})
    json.dump({"feed": asdict(Feed()), "proc": asdict(Proc()), "routes": R},
              open(OUT / "biorefinery_per_dry_tonne.json", "w"), indent=1)
