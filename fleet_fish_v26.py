#!/usr/bin/env python3
"""Costa Rica native-Sargassum co-location: large PV-roof + VAWT carriers,
solar/wind grid harvesters, native fish, utility drones and leftover geothermal heat.
EXPLORATORY USD-2026 scenario inputs, not engineered/weather-validated estimates.
Does not modify the national optimisation. Source and parameter audit are exported.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from math import ceil
from pathlib import Path
import json,csv,unittest
OUT=Path(__file__).resolve().parent
HOURS=8760.0

def crf(r,n):
    if n<=0 or r<0:raise ValueError('Invalid discount rate or lifespan')
    return (1/n if r==0 else r*(1+r)**n/((1+r)**n-1))

@dataclass(frozen=True)
class Inputs:
    farm_km2:float=10
    dry_t_per_ha_y:float=9
    dry_fraction:float=.10
    harvester_t_wet_h:float=8
    harvester_kw:float=60
    harvest_days_y:int=250
    harvest_hours_day:float=12
    harvest_availability:float=.80
    harvester_capex_usd:float=600_000
    harvester_life_y:int=15
    harvester_om_usd_y:float=20_000
    grid_solar_kw_per_unit:float=30
    grid_wind_vawt_kw_per_unit:float=20
    grid_accessible_output_fraction:float=.80  # non-hourly, accounts for mismatch/curtailment
    # Large wet-bulk barge/ship, not a drone. PV roof area <= sun-facing deck area.
    carrier_capacity_wet_t:float=1000
    carrier_roof_m2:float=1100
    carrier_roof_pv_w_m2:float=210
    carrier_vawt_units:int=2
    carrier_vawt_kw_each:float=40
    carrier_sea_speed_kmh:float=12
    carrier_round_trip_km:float=100
    carrier_port_turnaround_h:float=12
    carrier_propulsion_kw:float=700
    carrier_hotel_kw:float=40
    carrier_operating_days_y:int=250
    carrier_hours_day:float=18
    carrier_availability:float=.75
    carrier_capex_usd:float=9_000_000
    carrier_life_y:int=30
    carrier_om_usd_y:float=300_000
    carrier_min_units:int=1  # berth/pilot feasibility; optional 2-ship redundancy scenario
    carrier_pv_capture_fraction:float=.82
    carrier_vawt_capture_fraction:float=.75
    wind_drag_penalty_fraction_underway:float=.35 # proxy, NOT real performance map
    vessel_kite_enabled:bool=False  # no kite in proposed ship architecture
    # weather-free annual screening, no promise of hourly autonomous operation
    solar_kwh_kw_y:float=1400
    wind_cf:float=.25
    grid_wind_capture_fraction:float=.85
    solar_capex_usd_kw:float=1300
    vawt_capex_usd_kw:float=4000
    ren_life_y:int=20
    ren_om_fraction:float=.035
    shore_energy_usd_mwh:float=75
    marine_grid_storage_kwh_per_harvester:float=300
    marine_grid_storage_usd_kwh:float=350
    marine_grid_storage_life_y:int=10
    carrier_storage_kwh_per_ship:float=9000
    carrier_storage_usd_kwh:float=350
    carrier_storage_life_y:int=10
    battery_roundtrip_eff:float=.88
    # utility drones only for seed and supplies (not bulk cargo)
    seed_module_kg_y:float=4615.3846153846
    supplies_kg_y:float=3000
    drone_payload_kg:float=30
    drone_sorties_capacity_y:int=1000
    drone_sortie_kwh:float=8
    drone_cost_usd:float=45_000
    drone_life_y:int=5
    drone_om_usd_y:float=6000
    drone_labor_usd_sortie:float=12
    # Species-specific cages are SEPARATE from the Sargassum long-lines, no native fish capture credited
    fish_cage_ha:float=1
    fish_t_ha_y:float=15
    fish_sale_usd_t:float=5000
    fish_fcr:float=1.6
    fish_feed_usd_t:float=1400
    fish_opex_nonfeed_usd_t:float=2000
    fish_cage_capex_usd_ha:float=250000
    fish_cage_fixed_usd_ha_y:float=5000
    fish_cage_life_y:int=15
    fish_saleable_fraction:float=1.0 # yields already saleable; mortality not double counted
    # Cascading geothermal after preheat, only off-stream product gets dried
    geo_qualified_surplus_mwh_y:float=4600 # residual after preheat and temperature-qualified
    dryer_sidestream_wet_fraction:float=.05
    dryer_specific_kwh_kg_evap:float=1.15
    drying_solids_fraction:float=.90
    dryer_capex_usd:float=2_000_000
    dryer_life_y:int=15
    dryer_fixed_om_usd_y:float=50_000
    heat_reference_usd_mwh:float=78
    dryer_aux_kwh_t_evap:float=60
    rate:float=.07

def validate(p:Inputs):
    for k,v in asdict(p).items():
        if isinstance(v,(int,float)) and v<0:raise ValueError('negative '+k)
    for k in ['dry_fraction','harvest_availability','carrier_availability','grid_accessible_output_fraction','battery_roundtrip_eff','drying_solids_fraction','fish_saleable_fraction']:
        if not 0<getattr(p,k)<=1:raise ValueError(k)
    if not 0<=p.carrier_pv_capture_fraction<=1 or not 0<=p.carrier_vawt_capture_fraction<=1 or not 0<=p.grid_wind_capture_fraction<=1:raise ValueError('Capture fraction')
    if p.drying_solids_fraction<p.dry_fraction:raise ValueError('drying more wet than feed')
    for k in ['carrier_capacity_wet_t','carrier_sea_speed_kmh','harvester_t_wet_h','drone_payload_kg','carrier_roof_m2']:
        if getattr(p,k)<=0:raise ValueError(k)
    if not 0<=p.wind_cf<=1 or p.carrier_min_units<1:raise ValueError('wind CF or redundancy')

def solve(p:Inputs):
    validate(p)
    wet_t=p.farm_km2*100*p.dry_t_per_ha_y/p.dry_fraction
    dry_t=wet_t*p.dry_fraction
    harvester_total_h=wet_t/p.harvester_t_wet_h
    harvester_annual_hours=p.harvest_days_y*p.harvest_hours_day*p.harvest_availability
    n_h=ceil(harvester_total_h/harvester_annual_hours) if wet_t else 0
    harvester_kwh=harvester_total_h*p.harvester_kw
    # distinct solar and wind for grids, cap usage and curtailment
    grid_pv_kw=n_h*p.grid_solar_kw_per_unit
    grid_wind_kw=n_h*p.grid_wind_vawt_kw_per_unit
    grid_pv_gen=grid_pv_kw*p.solar_kwh_kw_y*p.grid_accessible_output_fraction
    grid_wind_gen=grid_wind_kw*HOURS*p.wind_cf*p.grid_wind_capture_fraction*p.grid_accessible_output_fraction
    grid_renewable_use=min(harvester_kwh,grid_pv_gen+grid_wind_gen)
    grid_shore_kwh=harvester_kwh-grid_renewable_use
    grid_ren_capex=grid_pv_kw*p.solar_capex_usd_kw+grid_wind_kw*p.vawt_capex_usd_kw
    grid_batt_capex=n_h*p.marine_grid_storage_kwh_per_harvester*p.marine_grid_storage_usd_kwh
    grid_fixed_cost=n_h*(p.harvester_capex_usd*crf(p.rate,p.harvester_life_y)+p.harvester_om_usd_y)
    grid_ren_cost=grid_ren_capex*(crf(p.rate,p.ren_life_y)+p.ren_om_fraction)+grid_batt_capex*crf(p.rate,p.marine_grid_storage_life_y)
    grid_gridonly_annual=grid_fixed_cost+harvester_kwh/1000*p.shore_energy_usd_mwh
    grid_hybrid_annual=grid_fixed_cost+grid_ren_cost+grid_shore_kwh/1000*p.shore_energy_usd_mwh
    # Big deck-roofed wet seaweed carrier, propulsion explicit, 0 drone bulk freight.
    trip_h=p.carrier_round_trip_km/p.carrier_sea_speed_kmh
    cycle_h=trip_h+p.carrier_port_turnaround_h
    trips=ceil(wet_t/p.carrier_capacity_wet_t) if wet_t else 0
    n_capacity=ceil(trips/(p.carrier_operating_days_y*p.carrier_hours_day*p.carrier_availability/cycle_h)) if trips else 0
    n_v=max(n_capacity,p.carrier_min_units) if trips else 0
    total_underway_h=trips*trip_h
    total_duty_h=trips*cycle_h
    # If fleet is used fewer hours annually than full year, only a fraction of annual
    # PV/wind potential is dispatch-accessible: unused sunlight cannot propel an idle ship.
    duty_factor=min(1,total_duty_h/(HOURS*max(1,n_v)))
    underway_factor=min(1,total_underway_h/(HOURS*max(1,n_v)))
    pv_kw_ship=p.carrier_roof_m2*p.carrier_roof_pv_w_m2/1000
    wind_kw_ship=p.carrier_vawt_units*p.carrier_vawt_kw_each
    total_pv_kw=n_v*pv_kw_ship
    total_wind_kw=n_v*wind_kw_ship
    pve=total_pv_kw*p.solar_kwh_kw_y*p.carrier_pv_capture_fraction*duty_factor
    wine=total_wind_kw*HOURS*p.wind_cf*p.carrier_vawt_capture_fraction*duty_factor
    # VAWT generation costs drag; proportion at sea is charged as additional propulsion.
    underway_wind_fraction=total_underway_h/total_duty_h if total_duty_h else 0
    drag_kwh=wine*underway_wind_fraction*p.wind_drag_penalty_fraction_underway
    propulsion_kwh=total_underway_h*p.carrier_propulsion_kw
    hotel_kwh=total_duty_h*p.carrier_hotel_kw
    demand_kwh=propulsion_kwh+hotel_kwh+drag_kwh
    v_ren_used=min(demand_kwh,pve+wine)
    v_shore_kwh=demand_kwh-v_ren_used
    v_pv_capex=total_pv_kw*p.solar_capex_usd_kw
    v_wind_capex=total_wind_kw*p.vawt_capex_usd_kw
    v_bat_capex=n_v*p.carrier_storage_kwh_per_ship*p.carrier_storage_usd_kwh
    v_fleet_fixed=n_v*(p.carrier_capex_usd*crf(p.rate,p.carrier_life_y)+p.carrier_om_usd_y)
    v_ren_fixed=(v_pv_capex+v_wind_capex)*(crf(p.rate,p.ren_life_y)+p.ren_om_fraction)
    # The identical traction battery is mandatory for both shore-fed and solar/wind ships.
    # Do not mischarge it solely to the solar/wind increment.
    base_battery_annual=v_bat_capex*crf(p.rate,p.carrier_storage_life_y)
    v_base_annual=v_fleet_fixed+base_battery_annual+(propulsion_kwh+hotel_kwh)/1000*p.shore_energy_usd_mwh
    v_hybrid_annual=v_fleet_fixed+base_battery_annual+v_ren_fixed+v_shore_kwh/1000*p.shore_energy_usd_mwh
    battery_usable_mwh=p.carrier_storage_kwh_per_ship*p.battery_roundtrip_eff/1000
    # Worst entire round trip: no reliable farm-side charging assumed.
    cycle_mwh=trip_h*p.carrier_propulsion_kw/1000+cycle_h*p.carrier_hotel_kw/1000+(drag_kwh/trips/1000 if trips else 0)
    # Separate utility drone mini-fleet handles no biomass freight
    drone_load_kg=p.seed_module_kg_y+p.supplies_kg_y
    sorties=ceil(drone_load_kg/p.drone_payload_kg) if drone_load_kg else 0
    drones=ceil(sorties/p.drone_sorties_capacity_y) if sorties else 0
    drone_cost=drones*(p.drone_cost_usd*crf(p.rate,p.drone_life_y)+p.drone_om_usd_y)+sorties*(p.drone_labor_usd_sortie+p.drone_sortie_kwh/1000*p.shore_energy_usd_mwh)
    # Fish: constructed financial scenarios; cage footprint is an independent quantity.
    fish_t=p.fish_cage_ha*p.fish_t_ha_y*p.fish_saleable_fraction
    feed_t=fish_t*p.fish_fcr
    fish_revenue=fish_t*p.fish_sale_usd_t
    fish_feed_cost=feed_t*p.fish_feed_usd_t
    fish_nonfeed=fish_t*p.fish_opex_nonfeed_usd_t
    fish_capex=p.fish_cage_ha*p.fish_cage_capex_usd_ha
    fish_annual_capex=fish_capex*crf(p.rate,p.fish_cage_life_y)
    fish_fixed=p.fish_cage_ha*p.fish_cage_fixed_usd_ha_y
    fish_annual_cost=fish_feed_cost+fish_nonfeed+fish_fixed+fish_annual_capex
    fish_profit=fish_revenue-fish_annual_cost
    breakeven=(fish_annual_cost/fish_t) if fish_t else None
    # Remaining qualifying heat only, dried byproduct fraction, no assumed feedstock HTL drying.
    sidestream=wet_t*p.dryer_sidestream_wet_fraction
    dried_solids=sidestream*p.dry_fraction
    evaporate_t=sidestream-dried_solids/p.drying_solids_fraction
    dryer_demand_mwh=evaporate_t*1000*p.dryer_specific_kwh_kg_evap/1000
    heat_used=min(p.geo_qualified_surplus_mwh_y,dryer_demand_mwh)
    dryer_net=(heat_used*p.heat_reference_usd_mwh-p.dryer_fixed_om_usd_y-p.dryer_capex_usd*crf(p.rate,p.dryer_life_y)
              -(heat_used/p.dryer_specific_kwh_kg_evap)*p.dryer_aux_kwh_t_evap/1000*p.shore_energy_usd_mwh) if heat_used>0 else 0
    return dict(annual_wet_t=wet_t,annual_dry_t=dry_t,
      grid_harvesters=n_h,grid_total_duty_h=harvester_total_h,grid_annual_demand_mwh=harvester_kwh/1000,
      grid_pv_capacity_kw=grid_pv_kw,grid_vawt_capacity_kw=grid_wind_kw,
      grid_solar_generated_mwh=grid_pv_gen/1000,grid_wind_generated_mwh=grid_wind_gen/1000,
      grid_renewable_used_mwh=grid_renewable_use/1000,grid_shore_mwh=grid_shore_kwh/1000,
      grid_renewable_share_pct=grid_renewable_use/harvester_kwh*100 if harvester_kwh else 0,
      grid_base_annual_usd=grid_gridonly_annual,grid_hybrid_annual_usd=grid_hybrid_annual,
      grid_hybrid_incremental_usd_y=grid_gridonly_annual-grid_hybrid_annual,
      grid_pv_vawt_storage_capex_usd=grid_ren_capex+grid_batt_capex,
      carrier_capacity_wet_t=p.carrier_capacity_wet_t,carrier_roof_m2=p.carrier_roof_m2,
      carrier_trips_y=trips,carrier_units=n_v,carrier_trip_cycle_h=cycle_h,
      carrier_operating_h_y=total_duty_h,carrier_battery_usable_mwh_per_ship=battery_usable_mwh,
      carrier_energy_per_complete_trip_mwh=cycle_mwh,carrier_roundtrip_storage_sufficiency=battery_usable_mwh>=cycle_mwh,
      carrier_propulsion_demand_mwh=propulsion_kwh/1000,
      carrier_hotel_demand_mwh=hotel_kwh/1000,carrier_vawt_drag_mwh=drag_kwh/1000,
      carrier_pv_capacity_kw=total_pv_kw,carrier_vawt_capacity_kw=total_wind_kw,
      carrier_solar_generated_mwh=pve/1000,carrier_wind_generated_mwh=wine/1000,
      carrier_renewable_used_mwh=v_ren_used/1000,carrier_shore_mwh=v_shore_kwh/1000,
      carrier_renewable_share_pct=v_ren_used/demand_kwh*100 if demand_kwh else 0,
      carrier_base_annual_usd=v_base_annual,carrier_hybrid_annual_usd=v_hybrid_annual,
      carrier_hybrid_incremental_usd_y=v_base_annual-v_hybrid_annual,
      carrier_pv_vawt_storage_capex_usd=v_pv_capex+v_wind_capex+v_bat_capex,
      drone_bulk_wet_t_y=0,drone_support_units=drones,drone_support_sorties_y=sorties,drone_support_cost_usd_y=drone_cost,
      fish_cage_ha=p.fish_cage_ha,fish_output_t_y=fish_t,fish_feed_t_y=feed_t,
      fish_revenue_usd_y=fish_revenue,fish_feed_cost_usd_y=fish_feed_cost,
      fish_nonfeed_cost_usd_y=fish_nonfeed,fish_fixed_and_annualized_capex_usd_y=fish_fixed+fish_annual_capex,
      fish_total_annual_cost_usd_y=fish_annual_cost,fish_annualized_profit_usd_y=fish_profit,
      fish_breakeven_sale_usd_t=breakeven,
      dryer_qualified_surplus_mwh=p.geo_qualified_surplus_mwh_y,dryer_demand_mwh=dryer_demand_mwh,
      dryer_heat_used_mwh=heat_used,dryer_incremental_net_usd_y=dryer_net,
      main_national_total_modified=False,renewable_hourly_firmness_verified=False)

def scenarios():
    b=Inputs()
    return {
      'Pacific_snapper_baseline_10km2':b,
      'Pacific_snapper_low_price':replace(b,fish_sale_usd_t=3500),
      'Pacific_snapper_high_price':replace(b,fish_sale_usd_t=7500),
      'Pacific_snapper_high_efficiency':replace(b,fish_sale_usd_t=7000,fish_fcr=1.35,fish_feed_usd_t=1100,fish_opex_nonfeed_usd_t=1700),
      'Pacific_snapper_5ha_cages':replace(b,fish_cage_ha=5),
      'Caribbean_cobia_pilot_unverified':replace(b,fish_t_ha_y=25,fish_sale_usd_t=5500,fish_fcr=1.8,fish_feed_usd_t=1600,fish_opex_nonfeed_usd_t=2000,fish_cage_capex_usd_ha=350000,fish_cage_fixed_usd_ha_y=10000),
      'Caribbean_cobia_high_price_unverified':replace(b,fish_t_ha_y=25,fish_sale_usd_t=7500,fish_fcr=1.65,fish_feed_usd_t=1400,fish_opex_nonfeed_usd_t=1850,fish_cage_capex_usd_ha=350000,fish_cage_fixed_usd_ha_y=10000),
      'large_ship_500t':replace(b,carrier_capacity_wet_t=500),
      'large_ship_2000t':replace(b,carrier_capacity_wet_t=2000,carrier_capex_usd=15000000,carrier_propulsion_kw=1050,carrier_roof_m2=2000,carrier_vawt_units=3),
      'large_ship_two_unit_redundancy':replace(b,carrier_min_units=2),
      'fleet_low_sun_wind':replace(b,solar_kwh_kw_y=1050,wind_cf=.1),
      'fleet_high_sun_wind':replace(b,solar_kwh_kw_y=1750,wind_cf=.40),
      'shore_energy_150usd_mwh':replace(b,shore_energy_usd_mwh=150),
      'vawt_no_net_wind_credits':replace(b,grid_wind_capture_fraction=0,carrier_vawt_capture_fraction=0),
      'dryer_no_surplus':replace(b,geo_qualified_surplus_mwh_y=0),
      'dryer_all_surplus_15pct_sidestream':replace(b,dryer_sidestream_wet_fraction=.15),
      'fish_none':replace(b,fish_cage_ha=0),
    }

class Physics(unittest.TestCase):
    def test_mass(self):self.assertEqual(solve(Inputs())['annual_wet_t'],90000)
    def test_ship_bulk(self):self.assertEqual(solve(Inputs())['drone_bulk_wet_t_y'],0)
    def test_ship_trip(self):self.assertEqual(solve(Inputs())['carrier_trips_y'],90)
    def test_ship_battery_covers_trip(self):self.assertTrue(solve(Inputs())['carrier_roundtrip_storage_sufficiency'])
    def test_two_thousand_t_requires_redesign(self):self.assertFalse(solve(Inputs(carrier_capacity_wet_t=2000,carrier_propulsion_kw=1050))['carrier_roundtrip_storage_sufficiency'])
    def test_fewer_trips_bigger_boat(self):self.assertLess(solve(Inputs(carrier_capacity_wet_t=2000))['carrier_trips_y'],solve(Inputs())['carrier_trips_y'])
    def test_grid_conserve(self):
        r=solve(Inputs());self.assertAlmostEqual(r['grid_renewable_used_mwh']+r['grid_shore_mwh'],r['grid_annual_demand_mwh'])
    def test_vessel_conserve(self):
        r=solve(Inputs());self.assertAlmostEqual(r['carrier_renewable_used_mwh']+r['carrier_shore_mwh'],r['carrier_propulsion_demand_mwh']+r['carrier_hotel_demand_mwh']+r['carrier_vawt_drag_mwh'])
    def test_vawt_drag_nonnegative(self):self.assertGreaterEqual(solve(Inputs())['carrier_vawt_drag_mwh'],0)
    def test_no_wind(self):self.assertEqual(solve(Inputs(wind_cf=0))['carrier_wind_generated_mwh'],0)
    def test_grid_no_power_overcredit(self):
        r=solve(Inputs(grid_solar_kw_per_unit=50000));self.assertLessEqual(r['grid_renewable_used_mwh'],r['grid_annual_demand_mwh'])
    def test_ship_no_power_overcredit(self):
        r=solve(Inputs(carrier_roof_pv_w_m2=100000));self.assertLessEqual(r['carrier_renewable_share_pct'],100)
    def test_high_price_improves_fish(self):self.assertGreater(solve(Inputs(fish_sale_usd_t=7000))['fish_annualized_profit_usd_y'],solve(Inputs())['fish_annualized_profit_usd_y'])
    def test_zero_fish(self):self.assertEqual(solve(Inputs(fish_cage_ha=0))['fish_annualized_profit_usd_y'],0)
    def test_feed_cost_rises(self):self.assertLess(solve(Inputs(fish_feed_usd_t=2000))['fish_annualized_profit_usd_y'],solve(Inputs())['fish_annualized_profit_usd_y'])
    def test_fish_revenue_cost(self):
        r=solve(Inputs());self.assertAlmostEqual(r['fish_annualized_profit_usd_y'],r['fish_revenue_usd_y']-r['fish_total_annual_cost_usd_y'])
    def test_dryer_no_heat(self):self.assertEqual(solve(Inputs(geo_qualified_surplus_mwh_y=0))['dryer_heat_used_mwh'],0)
    def test_dryer_surplus_cap(self):self.assertLessEqual(solve(Inputs())['dryer_heat_used_mwh'],4600)
    def test_storage_cost_included(self):self.assertGreater(solve(Inputs())['grid_pv_vawt_storage_capex_usd'],0)
    def test_no_national(self):self.assertFalse(solve(Inputs())['main_national_total_modified'])
    def test_no_firmness(self):self.assertFalse(solve(Inputs())['renewable_hourly_firmness_verified'])
    def test_negative(self):
        with self.assertRaises(ValueError):solve(Inputs(carrier_roof_m2=-1))
    def test_bad_fraction(self):
        with self.assertRaises(ValueError):solve(Inputs(dry_fraction=0))
    def test_more_grid_renewables_reduces_shore(self):self.assertLessEqual(solve(Inputs(grid_solar_kw_per_unit=60))['grid_shore_mwh'],solve(Inputs())['grid_shore_mwh'])
    def test_with_more_ship_ops_reduces_energy_surplus(self):self.assertGreaterEqual(solve(Inputs(carrier_capacity_wet_t=500))['carrier_trips_y'],solve(Inputs())['carrier_trips_y'])

def export():
    sims=scenarios()
    rows=[]
    for name,p in sims.items():rows.append({'scenario':name,**solve(p)})
    with open(OUT/'fleet_fish_v26_scenarios.csv','w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with open(OUT/'fleet_fish_v26_inputs_outputs.json','w',encoding='utf-8') as f:
        json.dump({'scope':'Illustrative pilot sensitivity only; USD 2026; no national extrapolation','inputs':{k:asdict(v) for k,v in sims.items()},'outputs':rows},f,ensure_ascii=False,indent=2)
    return rows
if __name__=='__main__':
    export()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Physics))
    raise SystemExit(not result.wasSuccessful())
