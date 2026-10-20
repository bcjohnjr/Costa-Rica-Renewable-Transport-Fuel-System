"""Additional publication figures for national export counterfactual and CST site screen."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT=Path(__file__).resolve().parent/'outputs'; FIG=Path(__file__).resolve().parent/'paper_figures'
FIG.mkdir(exist_ok=True)
r=json.load(open(OUT/'export_transition.json'))

def save(fig,name):
 for ext in ('pdf','png'):
  fig.savefig(FIG/(name+'.'+ext),bbox_inches='tight',dpi=300)
 plt.close(fig)

def make():
 S=r['stages']; xs=np.array([v['year'] for v in S]); sur=np.array([v['physically_freed_hydrocarbons_twh'] for v in S]);
 T=[q for q in r['trade'] if q['price_case']=='central' and q['variable_cost_usd_mwh']==70 and q['certification_scenario']=='not_certified'];
 tmap={v['year']:v for v in T};
 fig,ax=plt.subplots(figsize=(8.0,4.3));
 ax.plot(xs,sur,'o-',lw=2,label='Theoretical unused installed diesel-compatible output')
 ax.plot(xs,[tmap[x]['total_export_twh'] for x in xs],'s--',lw=1.8,label='Conditional sales: $100/MWh, $70/MWh variable supply cost')
 ax.set_ylabel('TWh of liquid fuel per year');ax.set_xlabel('Illustrative phase year');ax.set_xticks(xs)
 ax.set_ylim(-0.15,4.2);ax.grid(alpha=0.24);ax.legend(loc='upper left',fontsize=8)
 ax.set_title('Regional export opportunity after domestic fuel substitution')
 fig.tight_layout();save(fig,'Figure_8_Export_Transition')

 L=r['field_screen'];fig,ax=plt.subplots(figsize=(8.0,4.3))
 ax.plot([x['DNI_kwh_m2_y'] for x in L],[x['field_land_km2'] for x in L],marker='o',lw=2,label='Onshore CST field footprint')
 ax.plot([x['DNI_kwh_m2_y'] for x in L],[x['illustrative_offshore_footprint_km2'] for x in L],marker='s',ls='--',label='Offshore illustration (1.5× space)')
 ax.axhline(10,ls=':',c='#9b4d42',label='Illustrative 10 km² unprotected-land screen (not surveyed)')
 ax.set_xlabel('Hypothetical annual direct-normal irradiation (kWh/m²/year)');ax.set_ylabel('Solar collector site footprint (km²)')
 ax.set_title('CST process heat: land-screen sensitivity, 1.275 TWh/year')
 ax.grid(alpha=0.24);ax.legend(fontsize=8);fig.tight_layout();save(fig,'Figure_9_CST_Land')

 sc=[q for q in r['trade'] if q['year']==2050 and q['certification_scenario']=='not_certified']
 labels=['$75/MWh',' $100/MWh','$130/MWh'];
 costs=[30,70,115]
 fig,ax=plt.subplots(figsize=(8.2,4.5));a=np.zeros((3,3))
 for j,(name,dp) in enumerate([('low',75),('central',100),('high',130)]):
  for i,cost in enumerate(costs):
   a[i,j]=next(z['total_contribution_busd'] for z in sc if z['price_case']==name and z['variable_cost_usd_mwh']==cost)*1000
 im=ax.imshow(a,cmap='Blues',vmin=0,vmax=max(a.max(),0.01),aspect='auto')
 for i in range(3):
  for j in range(3):ax.text(j,i,f'{a[i,j]:.1f}',ha='center',va='center',color='white' if a[i,j]>.52*a.max() else 'black',fontsize=12)
 ax.set_xticks(range(3),labels);ax.set_yticks(range(3),[f'${n}/MWh' for n in costs]);ax.set_xlabel('Wholesale export price for diesel-equivalent fuel');ax.set_ylabel('Imputed variable production cost');
 ax.set_title('2050 conditional trade contribution (US$ million/year)')
 cbar=fig.colorbar(im,ax=ax);cbar.set_label('Contribution, US$ million/year')
 fig.tight_layout();save(fig,'Supplementary_Figure_S4_Export_Sensitivity')
 source=OUT/'source_data';source.mkdir(exist_ok=True)
 payloads={
 'Figure_8':{'Export_time_series':{'columns':['Year','Unused hydrocarbons TWh/year','Central-case eligible exports TWh/year','Extra vehicle electricity TWh/year'], 'rows':[[v['year'],v['physically_freed_hydrocarbons_twh'],tmap[v['year']]['total_export_twh'],v['additional_vehicle_electricity_twh']] for v in S], 'note':'Frozen 2035 production envelope; nominal sales prices and costs; no aviation export certification or verified offtake.'}},
 'Figure_9':{'CST_land_screen':{'columns':['Assumed DNI kWh/m2/year','Solar field land km2','Illustrative offshore km2'], 'rows':[[v['DNI_kwh_m2_y'],v['field_land_km2'],v['illustrative_offshore_footprint_km2']] for v in L], 'note':'Solar-only physical screen without confirmed DNI or available site.'}},
 'Supplementary_Figure_S4':{'2050_trade_contribution':{'columns':['Price scenario','Variable cost USD/MWh','Profit contribution US$ million/year'], 'rows':[[v['price_case'],v['variable_cost_usd_mwh'],1000*v['total_contribution_busd']] for v in sc], 'note':'Contributions before fixed CAPEX, permits, taxes; assumed market caps.'}}
 }
 for name,data in payloads.items():
  with open(source/(name+'.json'),'w') as jf:json.dump(data,jf,indent=2)
if __name__=='__main__':make()
