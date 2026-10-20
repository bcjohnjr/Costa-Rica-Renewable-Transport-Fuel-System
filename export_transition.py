"""Costa Rican land-based concentrating-solar-thermal biorefinery and *conditional* export screen.

Method: solve the published national LP with the Hacienda 2025 corrected road fuels and
100% of modeled biorefinery heat from CST. Freeze its hydrocarbon OUTPUT envelope at the
2035 full-substitution operating point; progressively electrify HDV/off-road uses, while
holding transport services and international aviation bunker volumes at 2025-equivalent
levels. Surplus can be sold by product subject to ASSUMED destination offtake caps.
This is NOT an empirical forecast of Panama/Nicaragua demand, a dispatch proof, or ASTM
qualification evidence. See README and methodological notes for interpretation.
"""
import csv
import json
import math
from pathlib import Path
import numpy as np
import optimise as o
import transition_scenarios as ts

OUT=Path(__file__).resolve().parent/'outputs'
SRC={
 'hacienda_2025_road_fuel':'https://www.hacienda.go.cr/docs/MH-DGPN-DG-INF-0005-2026_YER.pdf',
 'aresep_2025_totals':'https://aresep.go.cr/noticias/aresep-realizo-663-inspecciones-para-garantizar-calidad-de-combustibles/',
 'astm':'https://store.astm.org/d7566-25a.html',
 'easa_100percent':'https://www.easa.europa.eu/en/domains/environment/eaer/sustainable-aviation-fuels/what-are-sustainable-aviation-fuels',
 'caafi':'https://www.caafi.org/fuel-qualifications',
 'solar_gis':'https://datacatalog.worldbank.org/search/dataset/0042068/costa-rica-solar-irradiation-and-pv-power-potential-map',
 'land_protected':'https://data.worldbank.org/indicator/ER.LND.PTLD.ZS?locations=CR',
 'nrel_tower':'https://research-hub.nlr.gov/en/publications/re-designing-the-csp-thermal-energy-storage-system-to-enable-high/',
}
# User-configurable EXPLICIT scenario assumptions, not market measurement or site GIS.
ASSUMPTIONS={
 'site_country_land_km2':51100.0, 'protected_fraction_2025':0.266,
 'DNI_kwh_m2_y':[1000,1200,1400,1700,2000],
 'annual_net_field_to_process_efficiency':0.42, # illustrative high-grade thermal net
 'optical_aperture_packing_per_land':0.42, # aperture/land ratio; losses already in eff
 'assumed_unprotected_land_screen_km2':10.0, # NOT identified parcels
 'CST_storage_hours_at_avg_process_heat_load':12.0,
 'offshore_heat_cost_premium_usd_mwh':[40,80,130],
 'offshore_footprint_factor':1.5,
 'market_max_twh_y':{'Panama':2.1,'Nicaragua':1.8},
 'market_shares':{'Panama':0.60,'Nicaragua':0.40},
 'export_logistics_usd_mwh':{'Panama':14.0,'Nicaragua':18.0},
 'jet_upgrade_cost_usd_mwh':20.0,
 'jet_upgrading_yield':0.90,
 'incremental_supply_cost_usd_mwh':[30,70,115],
 'diesel_price_usd_mwh':[75,100,130],
 'jet_price_usd_mwh':[90,120,155],
 'certified_jet_reallocation_max_of_seaweed_hc':0.20,
 'jet_export_certified_flag':False, # only true in CONDITIONAL futuristic test
 'fleet_service_demand_growth':0.0, # 2025-equivalent service constant, no added demand
 'years':{
  '2035':{'HDV_battery_fossil_equivalent_share':0.50,'offroad_electric_share':0.00},
  '2040':{'HDV_battery_fossil_equivalent_share':0.65,'offroad_electric_share':0.20},
  '2045':{'HDV_battery_fossil_equivalent_share':0.80,'offroad_electric_share':0.30},
  '2050':{'HDV_battery_fossil_equivalent_share':0.90,'offroad_electric_share':0.40},
 },
}


def calc():
 # Independent solves avoid reusing stale stored totals after baseline change.
 p=ts.case('dropin', {'force_csp_heat':True,'csp_refinery_power':False})
 anchor=o.solve(p)
 best=o.solve(ts.case('maxel', {'force_csp_heat':True,'csp_refinery_power':False}))
 d=anchor['demand_twh']; en=anchor['end_use_twh']
 jet_demand=d['aviation']
 hc_supply=(anchor['seaweed_hc_twh']+anchor['fuels_twh']['eFT_liquids']+
            anchor['fuels_twh']['HEFA_waste_lipids']+anchor['fuels_twh']['residue_FT']+
            anchor['fuels_twh']['ATJ_jet_from_ethanol'])
 # Careful! 'use' variable is fossil-equivalent, ratio varies by option.
 hdv_hc=en.get('hdv|liq',0.0)
 ed95=en.get('hdv|ed95',0.0)
 off_hc=en.get('offroad|liq',0.0)
 hydrocarbon_use=jet_demand+hdv_hc+off_hc
 assert abs(hc_supply-hydrocarbon_use)<1e-6,(hc_supply,hydrocarbon_use)
 assert abs(en.get('hdv|bet',0)+hdv_hc+ed95-d['hdv'])<1e-6
 print('Anchor output hydrocarbons',hc_supply,'jet',jet_demand,'HDV',hdv_hc,'offroad',off_hc)
 heat=anchor['heat_twh_th']['CSP steam']
 fields=[]
 for dni in ASSUMPTIONS['DNI_kwh_m2_y']:
  density = dni * ASSUMPTIONS['annual_net_field_to_process_efficiency'] * ASSUMPTIONS['optical_aperture_packing_per_land'] / 1000
  land=heat/density
  fields.append(dict(DNI_kwh_m2_y=dni,net_heat_TWh_km2_y=density,field_land_km2=land,
        share_total_land_pct=land/ASSUMPTIONS['site_country_land_km2']*100,
        share_unprotected_land_pct=land/(ASSUMPTIONS['site_country_land_km2']*(1-ASSUMPTIONS['protected_fraction_2025']))*100,
        below_assumed_screen_10km2=land<=ASSUMPTIONS['assumed_unprotected_land_screen_km2'],
        illustrative_offshore_footprint_km2=land*ASSUMPTIONS['offshore_footprint_factor']))

 stages=[]
 for yy,z in ASSUMPTIONS['years'].items():
  hdv_b=z['HDV_battery_fossil_equivalent_share']
  off_e=z['offroad_electric_share']
  # Freeze the hydrocarbon output installed by 2035; HDV ED95 share declines with
  # the same ratio as liquid HDV. Sunk installed assets remain operating; no new
  # greenfield exports or EV fleet CAPEX in this accounting module.
  rem_liq_share=(1-hdv_b)/0.50
  hdv_rem=hdv_hc*rem_liq_share
  ed95_rem=ed95*rem_liq_share
  off_rem=off_hc*(1-off_e)
  diesel_need=hdv_rem+off_rem
  diesel_available=hc_supply-jet_demand
  freed=diesel_available-diesel_need
  assert freed>-1e-6, freed
  extra_vehicle_el=(d['hdv']*(hdv_b-0.50)*o.OPTIONS['hdv']['bet'][1] +
                    d['offroad']*off_e*o.OPTIONS['offroad']['el'][1])
  stages.append(dict(year=int(yy),HDV_battery_share=hdv_b,offroad_electric_share=off_e,
      fixed_hydrocarbons_twh=hc_supply,domestic_jet_twh=jet_demand,domestic_diesel_twh=diesel_need,
      domestic_ED95_fossil_equivalent_twh=ed95_rem,physically_freed_hydrocarbons_twh=freed,
      additional_vehicle_electricity_twh=extra_vehicle_el,
      fuel_imports_twh=0.0,
      full_substitution_conditional_on_certification=True,
      note='Physical potential from a frozen 2035 supply envelope; no new refineries assumed'))
 # A constant fuel output envelope is an assumption. At each year export optional;
 # buyer caps & logistics applied per market and product. Conservative dispatch at
 # given export unit sales > logistics + assigned incremental operating cost.
 trade=[]
 for st in stages:
  y=st['year']; free=st['physically_freed_hydrocarbons_twh']
  for cert in [False,True]:
   for price_label,dp,jp in [('low',75,90),('central',100,120),('high',130,155)]:
    for cost in ASSUMPTIONS['incremental_supply_cost_usd_mwh']:
     # scenario allocation first by market share; unsold if per-market cap hit.
     remaining=free
     rows=[]
     desired_jet=0 if not cert else min(free*0.35,
        anchor['seaweed_hc_twh']*ASSUMPTIONS['certified_jet_reallocation_max_of_seaweed_hc']*
        ASSUMPTIONS['jet_upgrading_yield'])
     jet_balance=0
     for country in ('Panama','Nicaragua'):
      quota=min(free*ASSUMPTIONS['market_shares'][country],ASSUMPTIONS['market_max_twh_y'][country])
      take=min(quota,remaining)
      logistics=ASSUMPTIONS['export_logistics_usd_mwh'][country]
      # jet exports restricted by hypothetical certification, further conversion, and
      # only if incremental netback exceeds diesel, where appropriate.
      planned_jet=min(take,desired_jet*ASSUMPTIONS['market_shares'][country])
      if jp-logistics-ASSUMPTIONS['jet_upgrade_cost_usd_mwh']-cost <= 0:
       planned_jet=0
      # Rational max-contribution dispatch gives highest margin product priority.
      if jp-logistics-ASSUMPTIONS['jet_upgrade_cost_usd_mwh'] < dp-logistics:
       planned_jet=0
      take_diesel=(take-planned_jet) if dp-logistics-cost>0 else 0
      take_jet=planned_jet if jp-logistics-ASSUMPTIONS['jet_upgrade_cost_usd_mwh']-cost>0 else 0
      # if diesel not profitable, allow jet to use more of the country's quota
      if not take_diesel and take_jet and cert:
       take_jet=min(take,desired_jet-jet_balance)
      jet_balance+=take_jet
      remaining-=take_jet+take_diesel
      rev=(take_jet*jp+take_diesel*dp)/1000
      logistics_busd=((take_jet+take_diesel)*logistics+take_jet*ASSUMPTIONS['jet_upgrade_cost_usd_mwh'])/1000
      variable_busd=(take_diesel+take_jet)*cost/1000
      rows.append(dict(country=country,diesel_twh=take_diesel,jet_twh=take_jet,export_twh=take_diesel+take_jet,
          revenue_busd=rev,logistics_and_upgrade_busd=logistics_busd,
          imputed_variable_cost_busd=variable_busd,contribution_busd=rev-logistics_busd-variable_busd))
     trade.append(dict(year=y,price_case=price_label,variable_cost_usd_mwh=cost,
        certification_scenario='hypothetically_certified_100pct' if cert else 'not_certified',
        exporters=rows,total_export_twh=sum(z['export_twh'] for z in rows),
        total_revenue_busd=sum(z['revenue_busd'] for z in rows),
        total_contribution_busd=sum(z['contribution_busd'] for z in rows),
        unexported_twh=free-sum(z['export_twh'] for z in rows)))
 res=dict(method='Frozen-output counterfactual; not hourly investment optimization',
       sources=SRC,assumptions=ASSUMPTIONS,
       demand_actual_2025_Ml=o.VOL_2025_ML,
       demand_twh=d,
       anchor={k:anchor[k] for k in ['total_cost_busd','electricity_delivered_twh','seaweed_total_km2','seaweed_dry_mt','seaweed_wet_mt','seaweed_hc_twh','seaweed_jet_twh','seaweed_ethanol_twh','electricity_vehicles_rail_twh','heat_twh_th','capacity_gw','fossil_cost_busd','lifecycle']},
       max_electrification={k:best[k] for k in ['total_cost_busd','electricity_delivered_twh','seaweed_total_km2','seaweed_jet_twh','heat_twh_th','electricity_vehicles_rail_twh','lifecycle']},
       jet_baseline_twh=jet_demand,hydrocarbons_fixed_twh=hc_supply,
       heavy_and_offroad_initial_hc_twh=hdv_hc+off_hc,
       initial_supply_reconciliation_twh=hc_supply-hydrocarbon_use,
       cst_thermal_storage_mwh=heat*1e6/8760*ASSUMPTIONS['CST_storage_hours_at_avg_process_heat_load'],
       field_screen=fields,stages=stages,trade=trade,
       limitations=['Costa Rica jet figure is a December-2025 planning estimate, not final audited sale',
                    'Marine and off-road shares not independently verified',
                    'No independent national industrial land GIS or parcel investigation: 10 km2 site-screen is illustrative only',
                    'Annual CST thermal energy is NOT hourly supply reliability; no wet-season firm heat model',
                    'Seaweed-derived 100% jet is NOT certified: conditional jet-only exports require certification',
                    'No verified Panama or Nicaragua fuel import orders or product markets; caps and prices assumptions',
                    'A fixed output envelope presumes sunk assets and constant operating cost; cost figures exclude new site-specific infrastructure',
                    'No supply chain, tax restoration or battery embodied emissions calculation',
                    'Transport demand held constant at 2025 equivalent; does not model future growth or induced demand'])
 OUT.mkdir(exist_ok=True)
 with open(OUT/'export_transition.json','w') as f: json.dump(res,f,indent=2,default=float)
 for key,ls in [('export_stages.csv',stages),('CST_land_screen.csv',fields)]:
  with open(OUT/key,'w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(ls[0])); w.writeheader(); w.writerows(ls)
 with open(OUT/'trade_scenarios.csv','w',newline='') as f:
  rows=[{k:v for k,v in tr.items() if k!='exporters'} for tr in trade]
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 return res

if __name__=='__main__':
 r=calc()
 for t in r['stages']:print(t['year'],'physical export',round(t['physically_freed_hydrocarbons_twh'],3),'TWh')
 print('CST heat',r['anchor']['heat_twh_th']['CSP steam'],'TWh')
