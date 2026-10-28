#!/usr/bin/env python3
"""V32 spotted rose snapper (Lutjanus guttatus) price/food sensitivity.
Hypothetical Pacific sea-cage production independent of national energy optimization;
imports preserved fleet_fish_v26 engine; no environmental carrying capacity claim.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import csv, json
from fleet_fish_v26 import Inputs, solve
OUT = Path(__file__).resolve().parent
P = Inputs()
SCENARIOS = {
    'Low price': dict(fish_sale_usd_t=5000),
    'Mid price': dict(fish_sale_usd_t=7000),
    'Premium price': dict(fish_sale_usd_t=7500),
    'Very high price': dict(fish_sale_usd_t=9000),
    'Premium + feed FCR 1.44': dict(fish_sale_usd_t=7500,fish_fcr=1.44),
    'Premium + feed 20pct cheaper (unverified)': dict(fish_sale_usd_t=7500,fish_feed_usd_t=1120),
}

def run():
    rows=[]
    for label,kw in SCENARIOS.items():
        p=replace(P,fish_cage_ha=1,**kw)
        r=solve(p)
        rows.append(dict(scenario=label,fish_species='Lutjanus guttatus (Pacific)',
          price_usd_kg=p.fish_sale_usd_t/1000,
          harvest_t_per_cage_ha_year=r['fish_output_t_y'],
          fcr=p.fish_fcr, feed_t_per_cage_ha_year=r['fish_feed_t_y'],
          variable_feed_usd_kg=p.fish_feed_usd_t/1000,
          annualized_total_cost_usd_per_cage_ha=r['fish_total_annual_cost_usd_y'],
          breakeven_usd_kg=r['fish_breakeven_sale_usd_t']/1000,
          revenue_usd_per_cage_ha_year=r['fish_revenue_usd_y'],
          annualized_profit_usd_per_cage_ha_year=r['fish_annualized_profit_usd_y']))
    area=[]
    seaweed_area_km2=2474
    for pct in (0.1,0.5,1.0):
        cage_ha=seaweed_area_km2*100*pct/100
        harvest_t=cage_ha*P.fish_t_ha_y
        area.append(dict(seaweed_area_km2=seaweed_area_km2, hypothetical_cage_area_pct=pct,
                         cage_ha=cage_ha, annual_saleable_fish_t=harvest_t,
                         annual_feed_t=harvest_t*P.fish_fcr,
                         note='Geometric sensitivity only; not a permitted or ecologically validated cage deployment'))
    with open(OUT/'snapper_cocolture_v32_price_cases.csv','w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with open(OUT/'snapper_cocolture_v32_footprint_cases.csv','w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(area[0]));w.writeheader();w.writerows(area)
    with open(OUT/'snapper_cocolture_v32_parameters.json','w',encoding='utf-8') as f:
        json.dump({'model_scope':'Exploratory market-price and sea-cage footprint sensitivity only; USD-2026 assumed, not farm gate quotes',
          'species':'Lutjanus guttatus / pargo mancha / spotted rose snapper','coast':'Pacific, Costa Rica',
          'price_assumptions_not_observed':list(SCENARIOS),'price_scenarios':rows,
          'footprint_scenarios':area,'source_studies':['doi:10.1111/jwas.12253','doi:10.1080/15222055.2015.1032458'],
          'exclusions':['regional demand cap','salinity','oxygen transfer','site carrying capacity','disease','juvenile supply','market verification','environmental licensing','price elasticity','waste suitability','whole marine infrastructure scaling'],
          'national_optimum_modified':False},f,indent=2,ensure_ascii=False)
    assert abs(rows[2]['annualized_profit_usd_per_cage_ha_year']-16451.34382474837)<.01
    assert abs(rows[2]['breakeven_usd_kg']-6.403243745)<.0001
    assert [round(x['annual_saleable_fish_t']) for x in area]==[3711,18555,37110]
    return rows,area
if __name__=='__main__':
    rows,areas=run()
    for x in rows: print(f"{x['scenario']:<39} ${x['price_usd_kg']:.2f}/kg  annualized_profit=${x['annualized_profit_usd_per_cage_ha_year']:,.2f} / cage-ha")
