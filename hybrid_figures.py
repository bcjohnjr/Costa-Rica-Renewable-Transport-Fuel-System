"""Manuscript Figures 9 and 10 and Supplementary Figures S5, S6 and S8, English and Spanish editions.

Data: outputs/hourly_cst.json (hourly_cst.py) and outputs/hybrid_offshore_pvt.json (hybrid_offshore_pvt.py).
Figures 9 and 10 are drawn at their printed size (5.83 in, the text width), so font sizes are true point sizes.
Supplementary figures keep the pixel proportions of the supplement layout.
Usage (from the repository root): python3 manuscript_figures/hybrid_figures.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
C = json.load(open(os.path.join(ROOT, "outputs", "hourly_cst.json")))
H = json.load(open(os.path.join(ROOT, "outputs", "hybrid_offshore_pvt.json")))
BLUE, ORANGE, GREEN, GOLD, SAND = "#2E6FB7", "#E8743B", "#2BA37A", "#D4A72C", "#D9B779"
NUT = H["nutrients"]
# FAO 2020 national inorganic-fertilizer use, Costa Rica [28] (N, P2O5, K2O; tonnes)
FAO_USE = NUT["assumptions"]["fao_use_t"]
P_TO_P2O5, K_TO_K2O = 141.94 / 61.95, 94.196 / 78.196
SMALL = {"font.family": "DejaVu Sans", "font.size": 6.0, "axes.titlesize": 6.6, "axes.titleweight": "bold",
         "axes.labelsize": 6.0, "xtick.labelsize": 5.8, "ytick.labelsize": 5.8, "legend.fontsize": 5.6,
         "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2,
         "ytick.major.size": 2, "axes.spines.top": False, "axes.spines.right": False}
LARGE = {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False}


def fmt(v, es, d):
    s = f"{v:,.{d}f}"
    return s.replace(",", " ").replace(".", ",") if es else s


def fig9(es):
    rows = {(r["field_mult"], r["storage_h"], r["solar"]): r for r in C["S32"]}
    cases = [(1.0, 48), (1.7, 72), (2.0, 96), (2.25, 96)]
    lab = [("Campo anual:\n" if es else "Annual field:\n") + f"1,00×, 48 h" if es else "Annual field:\n1.00×, 48 h",
           f"{fmt(1.7, es, 2)}×, 72 h", f"{fmt(2.0, es, 2)}×, 96 h",
           ("Reforzado:\n" if es else "Upgraded:\n") + f"{fmt(2.25, es, 2)}×, 96 h"]
    with plt.rc_context(SMALL):
        fig, (a, b) = plt.subplots(1, 2, figsize=(5.83, 1.95), gridspec_kw={"width_ratios": [1.15, 1]})
        x = np.arange(4); w = 0.38
        ref = [rows[(m, s, 1.0)]["unserved_pct"] for m, s in cases]
        low = [rows[(m, s, 0.75)]["unserved_pct"] for m, s in cases]
        a.bar(x - w / 2, ref, w, color=BLUE, label="Irradiación sintética de referencia" if es else "Reference synthetic irradiance")
        a.bar(x + w / 2, low, w, color=ORANGE, label="25 % menos recurso solar" if es else "25% lower solar resource")
        for xi, v in zip(x - w / 2, ref): a.text(xi, v + 0.4, fmt(v, es, 1), ha="center", fontsize=5.4)
        for xi, v in zip(x + w / 2, low): a.text(xi, v + 0.4, fmt(v, es, 1), ha="center", fontsize=5.4)
        a.set_xticks(x); a.set_xticklabels(lab, fontsize=5.4)
        a.set_ylabel("Calor no atendido (%)" if es else "Unserved refinery heat (%)")
        a.set_ylim(0, max(low) * 1.25); a.legend(frameon=False, loc="upper right")
        a.set_title("a  Calor no atendido, prueba sintética de 8760 h" if es else "a  Unserved heat, synthetic 8,760-hour test", loc="left")
        S34 = C["S34"]; base = H["modes"]["hybrid"]["cost_busd"]
        vals = [r["hybrid_with_upgrade_busd"] for r in S34]
        b.bar(range(3), vals, 0.55, color=["#BCD3E6", "#6FA0C6", BLUE])
        for i, v in enumerate(vals): b.text(i, v + 0.004, fmt(v, es, 3), ha="center", fontsize=5.6, fontweight="bold")
        b.axhline(base, color="k", ls="--", lw=0.7, label=("Solo programa anual (híbrido)" if es else "Annual LP only (hybrid)"))
        b.set_xticks(range(3)); b.set_xticklabels([str(r["store_usd_kwh"]) for r in S34])
        b.set_ylim(base - 0.05, max(vals) + 0.04)
        b.set_xlabel("Costo del almacén térmico (US$/kWh térmico)" if es else "Thermal-store cost (US$/kWh thermal)")
        b.set_ylabel("Total anual (miles de millones US$)" if es else "Annual total (US$ billion)")
        b.legend(frameon=False, loc="upper left")
        b.set_title("b  Costo con campo y almacén ampliados" if es else "b  Cost with enlarged field and store", loc="left")
        if es: b.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v, True, 2)))
        for ax in (a, b): ax.grid(axis="y", color="#EEE", lw=0.5); ax.set_axisbelow(True)
        fig.tight_layout(pad=0.4, w_pad=1.0)
        fig.savefig(os.path.join(OUT, f"Figure_09_{'ES' if es else 'EN'}.png"), dpi=400); plt.close(fig)


def fig10(es):
    n_rec, p_rec, k_rec = (NUT["recovered_t"][k] for k in ("N", "P", "K"))
    k_cap = NUT["deliverable_t"]["K"]
    rec = {"N": n_rec, "P2O5": p_rec * P_TO_P2O5, "K2O": k_rec * K_TO_K2O}
    deliver = {"N": min(rec["N"], FAO_USE["N"]), "P2O5": min(rec["P2O5"], FAO_USE["P2O5"]), "K2O": min(rec["K2O"], FAO_USE["K2O"])}
    with plt.rc_context(SMALL):
        fig, (a, b) = plt.subplots(1, 2, figsize=(5.83, 1.80))
        names = ["N", "P₂O₅", "K₂O"]; keys = ["N", "P2O5", "K2O"]
        x = np.arange(3)
        d = [deliver[k] for k in keys]; extra = [rec[k] - deliver[k] for k in keys]
        a.bar(x, d, 0.55, color=GREEN, label="Entrega nacional potencial (antes de certificar)" if es else "Potential domestic delivery (before certification)")
        a.bar(x, extra, 0.55, bottom=d, color=SAND, label="Por encima del uso de 2020" if es else "Beyond 2020 national use")
        for xi, k in zip(x, keys):
            a.hlines(FAO_USE[k], xi - 0.34, xi + 0.34, color="k", lw=1.4, label=("Uso nacional FAO 2020" if es else "FAO 2020 national use") if k == "N" else None)
        a.set_xticks(x); a.set_xticklabels(names)
        a.set_ylabel("Toneladas por año" if es else "Tonnes per year")
        a.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v, es, 0)))
        a.legend(frameon=False, loc="upper left", fontsize=5.2)
        a.set_ylim(0, max(FAO_USE["N"], rec["K2O"]) * 1.62)
        a.set_title("a  Nutrientes recuperados y uso nacional" if es else "a  Recovered nutrients and national use", loc="left")
        f = np.array([0, 25, 50, 75, 100])
        for lab_, v, c in ((("Nitrógeno (N)" if es else "Nitrogen (N)"), n_rec, BLUE), (("Fósforo (P)" if es else "Phosphorus (P)"), p_rec, GOLD),
                           (("Potasio (K)" if es else "Potassium (K)"), k_cap, GREEN)):
            b.plot(f, v * f / 100, "-o", color=c, ms=2.5, lw=1.0, label=lab_)
        b.set_xlabel("Fracción que supera el control de calidad (%)" if es else "Fraction passing the fertilizer quality gate (%)")
        b.set_ylabel("Entrega a fincas (t/año)" if es else "Delivery to farms (t/year)")
        b.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v, es, 0)))
        b.legend(frameon=False, loc="upper left")
        b.set_title("b  Entrega condicionada a la calidad" if es else "b  Delivery conditional on verified quality", loc="left")
        for ax in (a, b): ax.grid(axis="y", color="#EEE", lw=0.5); ax.set_axisbelow(True)
        fig.tight_layout(pad=0.4, w_pad=1.0)
        fig.savefig(os.path.join(OUT, f"Figure_10_{'ES' if es else 'EN'}.png"), dpi=400); plt.close(fig)


def s5(es):
    P = C["S5_first_240h"]; t = np.arange(240) / 24
    with plt.rc_context(LARGE):
        fig, ax = plt.subplots(figsize=(9.917, 3.703))
        ax.plot(t, P["dni"], lw=2.2, label="Irradiación directa sintética (normalizada)" if es else "Synthetic direct-beam solar (normalized)")
        ax.plot(t, P["wind"], lw=2.2, label="Eólica marina sintética (normalizada)" if es else "Synthetic offshore wind (normalized)")
        ax.plot(t, P["charge"], lw=2.2, label="Recarga vehicular sintética (normalizada)" if es else "Synthetic vehicle charging (normalized)")
        ax.set_xlabel("Día del año estilizado (primeros diez días)" if es else "Day of stylized year (first ten days)")
        ax.set_ylabel("Perfil horario × 8760 (adimensional)" if es else "Hourly profile × 8,760 (dimensionless)")
        ax.set_title("Figura suplementaria S5. Perfiles horarios construidos: solo ilustración" if es else
                     "Supplementary Figure S5. Constructed hourly profiles: illustration only")
        ax.legend(frameon=False, loc="upper right"); ax.grid(color="#EEE")
        fig.tight_layout(); fig.savefig(os.path.join(OUT, f"Supplementary_Figure_S5_{'ES' if es else 'EN'}.png"), dpi=300); plt.close(fig)


def s6(es):
    rows = C["S6"]
    with plt.rc_context(LARGE):
        fig, ax = plt.subplots(figsize=(8.096, 4.843))
        for s, col in ((12, "#1f77b4"), (48, "#ff7f0e"), (168, "#2ca02c")):
            rr = [r for r in rows if r["storage_h"] == s]
            ax.plot([r["field_mult"] for r in rr], [r["unserved_pct"] for r in rr], "-o", color=col, lw=2,
                    label=(f"{s} h de almacenamiento CST" if es else f"{s} h CST storage"))
        ax.set_xlabel("Multiplicador de campo CST (frente al caso anual híbrido)" if es else "CST field capacity multiplier (relative to hybrid annual-LP case)")
        ax.set_ylabel("Calor no atendido (%)" if es else "Unserved heat (%)")
        ax.set_title("Sensibilidad a almacenamiento térmico y sobredimensión solar\n10 % de la eólica marina disponible para calor auxiliar" if es else
                     "Sensitivity to high-grade storage and solar overbuild\n10% of offshore wind output eligible for backup heat")
        if es:
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v, True, 1)))
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v, True, 2)))
        ax.legend(frameon=True); ax.grid(color="#EEE")
        fig.tight_layout(); fig.savefig(os.path.join(OUT, f"Supplementary_Figure_S6_{'ES' if es else 'EN'}.png"), dpi=230); plt.close(fig)


def s8(es):
    rows = C["S33"]; aspect = 1.7143 if es else 1.5886
    with plt.rc_context(LARGE):
        fig, ax = plt.subplots(figsize=(4.9 * aspect, 4.9))
        d = [r["dni"] for r in rows]
        ax.plot(d, [r["annual_km2"] for r in rows], "-o", label="Campo CST dimensionado solo por energía anual" if es else "Annual-energy CST field")
        ax.plot(d, [r["upgraded_km2"] for r in rows], "-s", label=("Campo CST reforzado (2,25×)" if es else "Upgraded CST field (2.25×)"))
        ax.set_xlabel("Irradiación normal directa supuesta (kWh/m²/año)" if es else "Assumed direct normal irradiance (kWh/m²/year)")
        ax.set_ylabel("Superficie del campo CST (km²)" if es else "CST collector field (km²)")
        ax.set_title("Figura suplementaria S8. Superficie de colectores CST por irradiación" if es else
                     "Supplementary Figure S8. CST collector area by irradiance")
        if es:
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: fmt(v, True, 0)))
        ax.legend(); ax.grid(color="#EEE")
        fig.tight_layout(); fig.savefig(os.path.join(OUT, f"Supplementary_Figure_S8_{'ES' if es else 'EN'}.png"), dpi=210); plt.close(fig)


if __name__ == "__main__":
    for es in (False, True):
        fig9(es); fig10(es); s5(es); s6(es); s8(es)
    print("hybrid and hourly figures written")
