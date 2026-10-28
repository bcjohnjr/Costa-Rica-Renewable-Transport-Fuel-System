#!/usr/bin/env python3
"""V35 independent nutrient-replacement valuation. No desalination/distillation model.
Illustrative gross value, not verified fertilizer market income or optimized fuel-system savings.
"""
import csv, json
from pathlib import Path
out=Path(__file__).resolve().parent
p={
 'accepted_nitrogen_t_yr':9227,
 'accepted_phosphorus_t_yr':1933,
 'accepted_potassium_t_yr':18554,
 'nutrient_price_cases_USD_kg':{
 'low':[0.5,1,0.4], 'base':[1,2,0.8], 'high':[1.5,3,1.2]
 },
 'notes':['Elemental nutrient mass, after illustrative demand cap and 50 percent acceptance.',
          'No costs for separation, pollution controls, fertilizer formulation, distribution or certification.',
          'Not additive to national optimized renewable transport savings.']
}
rows=[]
for name,prices in p['nutrient_price_cases_USD_kg'].items():
 m=[p['accepted_nitrogen_t_yr'],p['accepted_phosphorus_t_yr'],p['accepted_potassium_t_yr']]
 v=[int(x*1000*y) for x,y in zip(m,prices)]
 rows.append({'case':name,'N_USD_kg':prices[0],'P_USD_kg':prices[1],'K_USD_kg':prices[2],
   'N_value_USD_y':v[0],'P_value_USD_y':v[1],'K_value_USD_y':v[2],
   'gross_nutrient_replacement_value_USD_y':sum(v)})
with (out/'fertilizer_value_v33_scenarios.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(out/'fertilizer_value_v35_assumptions.json').write_text(json.dumps({'inputs':p,'scenarios':rows},indent=2),encoding='utf-8')
assert next(x for x in rows if x['case']=='base')['gross_nutrient_replacement_value_USD_y']==27936200
print('V35 fertilizer-only model PASS',rows)
