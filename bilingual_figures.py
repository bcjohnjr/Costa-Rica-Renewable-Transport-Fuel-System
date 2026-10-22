"""Manuscript Figures 3, 6, 7, 8 and 11, English and Spanish editions.

Plotted values are transcribed from model outputs and are checked against a fresh run by
verify_manuscript.py:
  Figure 3  <- outputs/harvester_sargassum.json, outputs/harvester_slurry.json
  Figure 6  <- outputs/levers.json (cumulative costs)
  Figure 7  <- outputs/robustness.json (delta_busd)
  Figure 8  <- outputs/monte_carlo_summary.json
  Figure 11 <- outputs/export_transition.json, outputs/export_stages.csv
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, os
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"out"); os.makedirs(OUT,exist_ok=True)
DPI=400
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.titlesize":10,
 "axes.titleweight":"bold","axes.labelsize":9,"xtick.labelsize":8.5,"ytick.labelsize":8.5,
 "legend.fontsize":8,"axes.spines.top":False,"axes.spines.right":False,
 "figure.facecolor":"white","savefig.facecolor":"white"})
def f(v,es,d=2):
    s=f"{v:,.{d}f}"
    return s.replace(","," ").replace(".",",") if es else s
def save(fig,n): fig.savefig(os.path.join(OUT,n),dpi=DPI,bbox_inches="tight",pad_inches=0.08); plt.close(fig)

# ---------- Fig 3: Grid Harvester configuration sensitivity (Table S20)
def fig_gh(es):
    cfg_en=["Conventional 10-m vessel","Kelp reference, faired 1.20-m hose","Bare hose, 0.59 m",
            "Faired 80%","Faired 85% (reference)","Faired 90%","Faired 85%, 30% slurry",
            "Faired 85%, 1.20-m hose","Faired 85% + coarse chopping","Faired 85% + fine maceration"]
    cfg_es=["Embarcación convencional de 10 m","Referencia kelp, manguera carenada 1,20 m","Manguera sin carenar, 0,59 m",
            "Carenado 80 %","Carenado 85 % (referencia)","Carenado 90 %","Carenado 85 %, lodo 30 %",
            "Carenado 85 %, manguera 1,20 m","Carenado 85 % + trituración gruesa","Carenado 85 % + maceración fina"]
    e=[90.9,33.92,28.9,18.8,18.2,17.6,14.3,19.2,49.3,173.7]
    r=[1.00,2.68,3.15,4.82,4.99,5.17,6.34,4.74,1.84,0.52]
    L=dict(t=("a  Energía por ciclo de 1,44 ha" if es else "a  Energy per 1.44-ha cycle"),
           t2=("b  Relación convencional / Grid Harvester" if es else "b  Conventional / Grid Harvester ratio"),
           x=("Energía por ciclo (MJ)" if es else "Energy per cycle (MJ)"),
           x2=("Relación (–)" if es else "Ratio (–)"),
           ref=("Embarcación convencional" if es else "Conventional vessel"))
    # Drawn at its printed size (5.8 in wide) so that text sizes are true point sizes on the page.
    rc={"font.size":6.0,"axes.titlesize":6.6,"axes.labelsize":6.0,"xtick.labelsize":5.8,"ytick.labelsize":5.8,
        "axes.linewidth":0.5,"xtick.major.width":0.5,"ytick.major.width":0.5,"xtick.major.size":2,"ytick.major.size":2}
    with plt.rc_context(rc):
        fig,axs=plt.subplots(1,2,figsize=(4.95,1.62),gridspec_kw={"width_ratios":[1.55,1]})
        cfg=cfg_es if es else cfg_en
        y=np.arange(len(e))[::-1]
        cols=["#8A8A8A","#7FA8D0"]+["#2E6FB7"]*6+["#E8A33D","#C2462F"]
        ax=axs[0]; ax.barh(y,e,color=cols,height=0.72)
        for yy,v in zip(y,e): ax.text(v+2.5,yy,f(v,es,1),va="center",fontsize=5.6)
        ax.axvline(90.9,ls="--",color="#555",lw=0.6)
        ax.set_yticks(y); ax.set_yticklabels(cfg)
        ax.set_xlabel(L["x"],labelpad=1.5); ax.set_title(L["t"],loc="left",pad=3); ax.set_xlim(0,200)
        ax.grid(axis="x",color="#EEE",lw=0.5); ax.set_axisbelow(True)
        ax=axs[1]; ax.barh(y,r,color=cols,height=0.72)
        for yy,v in zip(y,r): ax.text(v+0.08,yy,f(v,es,2),va="center",fontsize=5.6)
        ax.axvline(1.0,ls="--",color="#555",lw=0.6)
        ax.set_yticks(y); ax.set_yticklabels([]); ax.set_xlim(0,7.4)
        ax.set_xlabel(L["x2"],labelpad=1.5); ax.set_title(L["t2"],loc="left",pad=3)
        ax.grid(axis="x",color="#EEE",lw=0.5); ax.set_axisbelow(True)
        fig.tight_layout(pad=0.4,w_pad=0.6); save(fig,f"Figure_03_{'ES' if es else 'EN'}.png")

# ---------- Fig 6: learning waterfall (Table S15)
def fig_learn(es):
    steps_en=["Today's costs (7%)","Cheaper farming\n$340→$225/dry t","Higher yield\n9→12 t/ha/y",
              "Cheaper deep-water\nstructures","Better conversion","Biorefinery cost −30%",
              "Electrofuels/DAC −25%","Capital 7%→4%","Grid Harvester\nenergy"]
    steps_es=["Costos actuales (7 %)","Cultivo más barato\n$340→$225/t seca","Mayor rendimiento\n9→12 t/ha/año",
              "Estructuras profundas\nmás baratas","Mejor conversión","Biorrefinería −30 %",
              "Electrocombustibles/DAC −25 %","Capital 7 %→4 %","Energía del\nGrid Harvester"]
    tot=[4.758,4.647,4.503,4.414,4.197,3.940,3.939,3.382,3.374]
    L=dict(t=("Descomposición acumulativa de las palancas de aprendizaje" if es else
              "Cumulative decomposition of technology-learning levers"),
           y=("Costo anual del sistema (miles de millones US$/año)" if es else
              "Annual system cost (US$ billion per year)"),
           n=("Los efectos son acumulativos y no deben leerse como ahorros independientes." if es else
              "Effects are cumulative and must not be read as independent additive savings."))
    fig,ax=plt.subplots(figsize=(11.4,5.2))
    x=np.arange(len(tot))
    ax.bar(x[0],tot[0],color="#8A8A8A",width=0.62)
    ax.text(x[0],tot[0]+0.03,f(tot[0],es,3),ha="center",fontweight="bold",fontsize=8.6)
    for i in range(1,len(tot)):
        d=tot[i]-tot[i-1]
        ax.bar(x[i],abs(d),bottom=min(tot[i],tot[i-1]),color="#2BA37A" if d<0 else "#C2462F",width=0.62)
        ax.plot([x[i-1]-0.31,x[i]+0.31],[tot[i-1],tot[i-1]],color="#999",lw=0.8,ls=":")
        ax.text(x[i],max(tot[i],tot[i-1])+0.03,("−" if d<0 else "+")+f(abs(d),es,3),
                ha="center",fontsize=8,color="#2BA37A" if d<0 else "#C2462F",fontweight="bold")
        ax.text(x[i],min(tot[i],tot[i-1])-0.075,f(tot[i],es,3),ha="center",fontsize=8.2)
    ax.set_xticks(x); ax.set_xticklabels([t.replace("\n"," ") for t in (steps_es if es else steps_en)],
                       fontsize=7.6, rotation=32, ha="right", rotation_mode="anchor")
    ax.set_ylim(3.1,4.95); ax.set_ylabel(L["y"]); ax.set_title(L["t"],loc="left")
    ax.grid(axis="y",color="#EEE",lw=0.7); ax.set_axisbelow(True)
    ax.text(0.0,-0.46,L["n"],transform=ax.transAxes,fontsize=7.8,style="italic",color="#5a6b78")
    save(fig,f"Figure_06_{'ES' if es else 'EN'}.png")

# ---------- Fig 7: robustness tornado (Table S16)
def fig_rob(es):
    cases_en=["Integration and network adders ×2","No seaweed and PV ≤4 GW","No seaweed",
              "Seaweed yield 4 t/ha/y","Seaweed yield 6 t/ha/y","Finance at 7%","Vehicle premia high",
              "No fertilizer credit","Offshore pressing before shipping","No electrofuels",
              "Onshore wind ≤1.5 GW","No depth cycling","Candidate marine area 5%",
              "Whole-seaweed HTL yield 0.12","Conventional harvesting energy","PV limited to 4 GW",
              "LNG/CNG vehicles allowed","Domestic aviation and shipping only"]
    cases_es=["Adicionales de integración y red ×2","Sin macroalgas y FV ≤4 GW","Sin macroalgas",
              "Rendimiento 4 t/ha/año","Rendimiento 6 t/ha/año","Financiamiento al 7 %","Prima vehicular alta",
              "Sin crédito de fertilizantes","Prensado en mar antes del transporte","Sin electrocombustibles",
              "Eólica terrestre ≤1,5 GW","Sin ciclado de profundidad","Área marina candidata 5 %",
              "Rendimiento HTL 0,12","Energía de cosecha convencional","FV limitada a 4 GW",
              "Vehículos GNL/GNC permitidos","Solo aviación y navegación nacional"]
    d=[0.333,0.887,0.338,0.338,0.304,0.576,0.425,0.085,0.043,0.031,0.024,0.026,0.049,0.013,0.010,0.000,-0.005,-0.957]
    order=np.argsort(d)
    L=dict(t=("Sensibilidad del costo anual del sistema a restricciones impuestas" if es else
              "Sensitivity of annual system cost to imposed constraints"),
           x=("Cambio frente al caso de referencia (miles de millones US$/año)" if es else
              "Change from the reference case (US$ billion per year)"),
           n=("Referencia: regla de combustibles compatibles con calor CST, US$3423 millones/año." if es else
              "Reference: drop-in rule with CST heat, US$3.423 billion per year."))
    fig,ax=plt.subplots(figsize=(11.0,5.4))
    cs=cases_es if es else cases_en
    y=np.arange(len(d))
    vals=[d[i] for i in order]; labs=[cs[i] for i in order]
    ax.barh(y,vals,color=["#2BA37A" if v<0 else "#C2462F" for v in vals])
    for yy,v in zip(y,vals):
        ax.text(v+(0.018 if v>=0 else -0.018),yy,("+" if v>0 else "")+f(v,es,3),
                va="center",ha="left" if v>=0 else "right",fontsize=8)
    ax.axvline(0,color="#333",lw=1.0)
    ax.set_yticks(y); ax.set_yticklabels(labs,fontsize=8)
    ax.set_xlim(-1.18,1.12); ax.set_xlabel(L["x"]); ax.set_title(L["t"],loc="left")
    ax.grid(axis="x",color="#EEE",lw=0.7); ax.set_axisbelow(True)
    ax.text(0.0,-0.13,L["n"],transform=ax.transAxes,fontsize=7.8,style="italic",color="#5a6b78")
    save(fig,f"Figure_07_{'ES' if es else 'EN'}.png")

# ---------- Fig 8: Monte Carlo (Table S18)
def fig_mc(es):
    names_en=["Drop-in rule","Fleet-compatible\nsolar bridge","Maximum\nelectrification"]
    names_es=["Combustibles\ncompatibles","Transición solar\ncompatible","Electrificación\nmáxima"]
    med=[4.01,7.15,2.98]; lo=[3.63,5.89,2.70]; hi=[4.48,9.14,3.33]; det=[3.42,4.99,2.71]
    bem=[1.67,2.97,1.24]; bl=[1.51,2.45,1.12]; bh=[1.86,3.80,1.38]
    ab=[177,553,62]; al=[135,403,32]; ah=[230,781,100]
    L=dict(ta=("a  Costo anual del sistema" if es else "a  Annual system cost"),
           tb=("b  Multiplicador de equilibrio\nsobre precios fósiles de 2025" if es else
               "b  Break-even multiplier\non 2025 fossil prices"),
           tc=("c  Costo de abatimiento" if es else "c  Abatement cost"),
           ya=("Miles de millones US$/año" if es else "US$ billion per year"),
           yc=("US$ por tCO₂e" if es else "US$ per tCO₂e"),
           med=("Mediana Monte Carlo (percentiles 5–95)" if es else "Monte Carlo median (5th–95th percentile)"),
           det=("Caso determinista favorable" if es else "Favorable deterministic case"))
    fig,axs=plt.subplots(1,3,figsize=(12.8,4.5))
    nm=names_es if es else names_en
    x=np.arange(3)
    ax=axs[0]
    ax.errorbar(x,med,yerr=[np.array(med)-np.array(lo),np.array(hi)-np.array(med)],fmt="o",
                color="#2E6FB7",ms=9,capsize=7,lw=2,label=L["med"])
    ax.plot(x,det,"D",color="#C2462F",ms=8,label=L["det"])
    for xi,(m,dt) in enumerate(zip(med,det)):
        ax.text(xi+0.12,m,f(m,es,2),fontsize=8.4,va="center")
        ax.text(xi+0.12,dt,f(dt,es,2),fontsize=8.4,va="center",color="#C2462F")
    ax.set_xticks(x); ax.set_xticklabels(nm,fontsize=8); ax.set_ylabel(L["ya"])
    ax.set_title(L["ta"],loc="left"); ax.set_xlim(-0.5,2.7); ax.legend(frameon=False,fontsize=7.6,loc="upper center")
    ax.grid(axis="y",color="#EEE",lw=0.7); ax.set_axisbelow(True); ax.set_ylim(2,10.6)
    ax=axs[1]
    ax.errorbar(x,bem,yerr=[np.array(bem)-np.array(bl),np.array(bh)-np.array(bem)],fmt="o",
                color="#2BA37A",ms=9,capsize=7,lw=2)
    ax.axhline(1.0,ls="--",color="#333",lw=1.1)
    for xi,m in enumerate(bem): ax.text(xi+0.12,m,f(m,es,2),fontsize=8.4,va="center")
    ax.set_xticks(x); ax.set_xticklabels(nm,fontsize=8); ax.set_title(L["tb"],loc="left")
    ax.set_xlim(-0.5,2.7); ax.grid(axis="y",color="#EEE",lw=0.7); ax.set_axisbelow(True)
    ax=axs[2]
    ax.errorbar(x,ab,yerr=[np.array(ab)-np.array(al),np.array(ah)-np.array(ab)],fmt="o",
                color="#7B5EA7",ms=9,capsize=7,lw=2)
    for xi,m in enumerate(ab): ax.text(xi+0.12,m,f(m,es,0),fontsize=8.4,va="center")
    ax.set_xticks(x); ax.set_xticklabels(nm,fontsize=8); ax.set_ylabel(L["yc"])
    ax.set_title(L["tc"],loc="left"); ax.set_xlim(-0.5,2.7)
    ax.grid(axis="y",color="#EEE",lw=0.7); ax.set_axisbelow(True)
    fig.tight_layout(); save(fig,f"Figure_08_{'ES' if es else 'EN'}.png")

# ---------- Fig 11: export economics (Tables S23 + S25)
def fig_exp(es):
    yrs=[2035,2040,2045,2050]; sur=[0.00,1.39,2.58,3.44]
    L=dict(ta=("a  Excedente físico liberado" if es else "a  Physical surplus freed"),
           tb=("b  Contribución operativa condicional en 2050" if es else
               "b  Conditional operating contribution in 2050"),
           ya=("TWh/año de combustible líquido" if es else "TWh of liquid fuel per year"),
           yb=("Contribución (miles de millones US$/año)" if es else "Contribution (US$ billion per year)"),
           xa=("Año de transición ilustrativo" if es else "Illustrative phase year"),
           xb=("Costo variable de producción (US$/MWh)" if es else "Variable production cost (US$/MWh)"),
           pl=("Precio bajo" if es else "Low price"),pc=("Precio central" if es else "Central price"),
           ph=("Precio alto" if es else "High price"),
           n=("Excluye financiamiento, terminales nuevas, aduanas e impuestos." if es else
              "Excludes financing, new terminals, customs and taxes."))
    fig,axs=plt.subplots(1,2,figsize=(11.6,4.3))
    ax=axs[0]
    ax.bar(yrs,sur,width=2.6,color="#5B8FC9",zorder=2)
    for xx,v in zip(yrs,sur): ax.text(xx,v+0.09,f(v,es,2),ha="center",fontsize=9,fontweight="bold")
    ax.set_xticks(yrs); ax.set_ylim(0,4.0); ax.set_ylabel(L["ya"]); ax.set_xlabel(L["xa"])
    ax.set_title(L["ta"],loc="left"); ax.grid(axis="y",color="#DDD",lw=0.7,zorder=0); ax.set_axisbelow(True)
    ax=axs[1]
    vc=[30,70,115]
    low=[0.101,0.000,0.000]; cen=[0.187,0.049,0.000]; high=[0.290,0.153,0.002]
    w=0.26; x=np.arange(3)
    for i,(d,c,lab) in enumerate([(low,"#BCD4E6",L["pl"]),(cen,"#6E9FC4",L["pc"]),(high,"#2E6FB7",L["ph"])]):
        b=ax.bar(x+(i-1)*w,d,w,color=c,label=lab)
        for bb,v in zip(b,d):
            ax.text(bb.get_x()+bb.get_width()/2,v+0.006,f(v,es,3),ha="center",fontsize=7.4)
    ax.set_xticks(x); ax.set_xticklabels([f(v,es,0) for v in vc])
    ax.set_xlabel(L["xb"]); ax.set_ylabel(L["yb"]); ax.set_title(L["tb"],loc="left")
    ax.legend(frameon=False,fontsize=8); ax.set_ylim(0,0.34)
    ax.grid(axis="y",color="#EEE",lw=0.7); ax.set_axisbelow(True)
    fig.tight_layout()
    fig.text(0.02,-0.04,L["n"],fontsize=7.8,style="italic",color="#5a6b78")
    save(fig,f"Figure_11_{'ES' if es else 'EN'}.png")

for es in (False,True):
    fig_gh(es); fig_learn(es); fig_rob(es); fig_mc(es); fig_exp(es)
print("new figures written")
