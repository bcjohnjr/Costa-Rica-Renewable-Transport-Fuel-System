#!/usr/bin/env python3
"""V35 snapper-feed sensitivity for sanitized camarones by-product meal.
Replaces share of fishmeal-derived PROTEIN, not share of complete feed mass.
Screening assumptions only; no feeding trial or market quotes.
"""
from pathlib import Path
import csv,json
out=Path(__file__).resolve().parent
p={'annual_market_fish_kg_per_cage_ha':15000,'FCR':1.6,
   'fishmeal_fraction_of_complete_diet':0.30,'fishmeal_protein_fraction':0.65,
   'camarones_meal_protein_fraction':0.50,
   'fishmeal_price_USD_kg':1.9,'processed_camarones_meal_price_USD_kg':0.9,
   'fish_cost_baseline_USD_kg':6.403243745}
rows=[]
for fraction in (0,.1,.2,.3):
 fishmeal_removed=p['fishmeal_fraction_of_complete_diet']*fraction
 camarones_added=fishmeal_removed*p['fishmeal_protein_fraction']/p['camarones_meal_protein_fraction']
 saving=fishmeal_removed*p['fishmeal_price_USD_kg']-camarones_added*p['processed_camarones_meal_price_USD_kg']
 rows.append(dict(fishmeal_protein_substitution_pct=round(fraction*100),fishmeal_fraction_complete_feed=0.3,fishmeal_protein_fraction=0.65,processed_camarones_meal_protein_fraction=0.5,fishmeal_replaced_kg_feed=round(fishmeal_removed,5),processed_camarones_meal_added_kg_feed=round(camarones_added,5),fishmeal_price_USD_kg=1.9,processed_camarones_meal_landed_USD_kg=.9,feed_cost_reduction_USD_per_kg_complete_feed=round(saving,4),feed_savings_USD_cage_ha_year=round(saving*15000*1.6,2),breakeven_fish_cost_USD_kg=round(p['fish_cost_baseline_USD_kg']-saving*1.6,3),limitations='No growth/FCR benefit; local supply, safety, nutrition and processing costs unverified'))
with (out/'camarones_byproduct_snapper_feed_v34_scenarios.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(out/'camarones_snapper_feed_v35_assumptions.json').write_text(json.dumps({'inputs':p,'scenarios':rows},indent=2),encoding='utf-8')
assert next(x for x in rows if x['fishmeal_protein_substitution_pct']==30)['feed_savings_USD_cage_ha_year']==1576.8
print('V35 camarones/snapper feed model PASS',rows)
