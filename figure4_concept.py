"""Manuscript Figure 4 (conceptual architecture), English and Spanish editions. Not data-driven."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
DPI = 400
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.labelsize": 9, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})
C = {"pv":"#E8A33D","wind":"#2E6FB7","veh":"#D1495B","bio":"#1B7A3E","efuel":"#7B5EA7",
     "jet":"#2BAE8B","res":"#E8743B","teal":"#2BAE8B","grey":"#8A8A8A",
     "n":"#2E6FB7","p":"#D4A72C","k":"#1F9E78","ref":"#2E6FB7","low":"#E8743B"}

def fnum(v, es, dec=2):
    s = f"{v:,.{dec}f}"
    if es:
        s = s.replace(",", " ").replace(".", ",")
    return s

def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=DPI, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)

# ---------------------------------------------------------------- Figure 3
def fig4(es):
    L = dict(
        title=("Integración ilustrativa: eólica marina y macroalgas con biorrefinería PVT–CST terrestre"
               if es else "Illustrative offshore wind–seaweed and onshore PVT–CST refinery integration"),
        marine="Concepto marino Punta Descartes / La Cruz" if es else "Punta Descartes / La Cruz marine concept",
        cult=("Cultivo de sargazo en zonas evaluadas entre turbinas" if es else
              "Sargassum cultivation in screened inter-turbine zones"),
        prod="Producción marina + energía eólica" if es else "Marine production + wind",
        prodb=(["Etapa inicial potencial de 540 MW (ICE)",
                "Cultivo solo donde nutrientes, permisos,",
                "fondeo y ecología sean adecuados"] if es else
               ["540 MW potential first stage (ICE)",
                "Cultivation only where nutrients, permits,",
                "mooring clearance and ecology are suitable"]),
        pvt="Campo/techo híbrido PVT" if es else "Hybrid PVT roof/field",
        pvtb=(["Circuito limpio de colectores","+ intercambiador, 25–65 °C",
               "Electricidad fotovoltaica adicional"] if es else
              ["Clean collector loop","+ exchanger, 25–65 °C","PV electricity coproduct"]),
        cst="Receptor CST + almacenamiento" if es else "CST receiver + storage",
        cstb=(["Calor de alta temperatura para HTL","300–370 °C, tras recuperación"] if es else
              ["High-grade duty toward HTL","300–370 °C, after recovery"]),
        htl="HTL húmeda / hidrotratamiento / recuperación de nutrientes" if es else "Wet HTL / hydrotreating / nutrient recovery",
        htlb=(["Combustibles condicionados a calidad y calificación ASTM",
               "Las sales de N, P y K requieren ensayos de impurezas independientes"] if es else
              ["Fuel outputs conditional on quality and ASTM qualification",
               "Separated N, P, K salts require independent impurity tests"]),
        low="Calor de baja temperatura" if es else "Low-grade heat",
        high="Calor de alta temperatura" if es else "High-temperature heat",
        elec="Exportación eléctrica" if es else "Electrical export",
        algae="Algas húmedas" if es else "Wet algae",
        foot=("Dimensiones y posiciones conceptuales; no es un diseño de proyecto ni un sitio autorizado."
              if es else
              "All diagram dimensions and positions are conceptual; not a project layout or permitted site."),
    )
    fig, ax = plt.subplots(figsize=(11.0, 4.6)); ax.set_xlim(0,100); ax.set_ylim(28,100); ax.axis("off")
    ax.text(2, 99, L["title"], fontsize=12, fontweight="bold", va="top")

    def box(x,y,w,h,fc,ec,title,body=None,tfs=10,bfs=8.4):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.6,rounding_size=1.2",
                                    fc=fc,ec=ec,lw=1.3))
        ax.text(x+w/2, y+h-(3.0 if body else h/2-1.4), title, ha="center",
                va="top" if body else "center", fontsize=tfs, fontweight="bold", color="#17364d")
        if body:
            for i,ln in enumerate(body):
                ax.text(x+w/2, y+h-8.2-i*4.3, ln, ha="center", va="top", fontsize=bfs, color="#24404f")

    # marine panel
    ax.add_patch(Rectangle((2,61),33,28, fc="#DCEBF5", ec="none"))
    ax.text(3.2, 87.6, L["marine"].replace(" / ", "\n"), fontsize=9.2, fontweight="bold",
            color="#1C5F8F", va="top", linespacing=1.25)
    for cx in (10,19,28):
        ax.plot([cx,cx],[68,77.0], color="#44586b", lw=1.5)
        ax.plot([cx-3.6,cx+3.6],[75.4,75.4], color="#44586b", lw=1.5)
        ax.plot([cx,cx+2.7],[75.4,72.6], color="#44586b", lw=1.5)
    for bx in np.linspace(5,30,6):
        ax.add_patch(Rectangle((bx,65.8),3.2,1.2, fc="#1B7A3E", ec="none"))
    ax.text(18.5, 63.2, L["cult"], ha="center", fontsize=7.8, color="#24404f")

    box(2,35,33,21,"#EAF5EE","#4E7E63",L["prod"],L["prodb"],tfs=9.6,bfs=8.0)
    box(41,68,26,19,"#FDF1D6","#C79A3C",L["pvt"],L["pvtb"],tfs=9.6,bfs=8.2)
    box(71,68,27,19,"#FBE3E3","#C06B6B",L["cst"],L["cstb"],tfs=9.6,bfs=8.2)
    box(41,37,57,19,"#E8E9F7","#5B63A5",L["htl"],L["htlb"],tfs=9.8,bfs=8.2)

    ax.add_patch(FancyArrowPatch((53,67.0),(53,57.2),arrowstyle="-|>",mutation_scale=12,color="#44586b",lw=1.2))
    ax.add_patch(FancyArrowPatch((84,67.0),(84,57.2),arrowstyle="-|>",mutation_scale=12,color="#44586b",lw=1.2))
    ax.text(54.2,62.6,L["low"],fontsize=8.0,color="#24404f",va="center")
    ax.text(85.2,62.6,L["high"],fontsize=8.0,color="#24404f",va="center")
    ax.add_patch(FancyArrowPatch((35.5,61.5),(40.2,51.5),arrowstyle="-|>",mutation_scale=12,color="#44586b",lw=1.2))
    ax.text(28.8,59.8,L["elec"],fontsize=8.0,color="#24404f",ha="left")
    ax.add_patch(FancyArrowPatch((35.5,45.5),(40.2,45.5),arrowstyle="-|>",mutation_scale=12,color="#44586b",lw=1.2))
    ax.text(35.6,43.3,L["algae"],fontsize=8.0,color="#24404f",ha="left")
    ax.text(41,32.6,L["foot"],fontsize=8.0,style="italic",color="#5a6b78",ha="left")
    save(fig, f"Figure_04_{'ES' if es else 'EN'}.png")

# ---------------------------------------------------------------- Figure 5

for es in (False, True):
    fig4(es)
print("Figure 4 written (EN, ES)")
