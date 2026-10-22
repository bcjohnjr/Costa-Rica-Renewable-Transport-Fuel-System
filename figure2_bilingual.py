"""Manuscript Figure 2, English and Spanish editions, in a wide two-row layout.

Panels a, b and d reuse the original illustrations (Spanish edition: Spanish labels set over the
English ones); panels c and e are plotted from outputs/harvester_turns.json and
outputs/harvester_sargassum.json.
Usage (from the repository root): python3 manuscript_figures/figure2_bilingual.py
       writes manuscript_figures/out/Figure_02_EN.png and Figure_02_ES.png
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
repo = os.path.dirname(HERE)
src = os.path.join(repo, "illustrations", "Figure_2_composite_EN.png")
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
sys.path.insert(0, repo); os.chdir(repo)
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import figures as F                        # model outputs (HT, HS) and house style
from figstyle import C, MM

TTF = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data/fonts/ttf/STIXGeneral.ttf")
im = Image.open(src).convert("RGB")


def relabel(img, boxes, dark):
    """Cover each English label box and write the Spanish text, centred on the box."""
    base = img.convert("RGBA"); layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (x0, y0, x1, y1), txt, size in boxes:
        f = ImageFont.truetype(TTF, size)
        lines = txt.split("\n")
        w = max(d.textlength(l, font=f) for l in lines); lh = size * 1.02; h = lh * len(lines)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        bx0, bx1 = min(x0, cx - w / 2) - 10, max(x1, cx + w / 2) + 10
        by0, by1 = min(y0, cy - h / 2) - (10 if dark else 3), max(y1, cy + h / 2) + (8 if dark else 3)
        if dark:
            reg = np.asarray(img.crop((int(bx0), int(by0), int(bx1), int(by1)))).reshape(-1, 3).mean(0)
            fill = tuple(int(v * 0.45) for v in reg) + (255,)
            d.rounded_rectangle((bx0, by0, bx1, by1), radius=6, fill=fill)
        else:
            d.rectangle((bx0, by0, bx1, by1), fill=(255, 255, 255, 255))
        for i, l in enumerate(lines):
            d.text((cx - d.textlength(l, font=f) / 2, cy - h / 2 + i * lh), l, font=f,
                   fill=(255, 255, 255, 255) if dark else (20, 20, 20, 255))
    return Image.alpha_composite(base, layer).convert("RGB")


S = 25   # label size in pixels at the source resolution
A = [((182, 284, 272, 330), "red de\ncultivo", S),
     ((388, 236, 480, 304), "embarcación\nprincipal", S),
     ((540, 284, 604, 328), "junta giratoria\nde 360°", S),
     ((860, 304, 926, 328), "boyas", S),
     ((520, 404, 600, 450), "manguera\nde succión", S),
     ((180, 422, 290, 470), "cable de\ntransporte", S),
     ((290, 526, 352, 574), "rodillo\nde vía", S),
     ((484, 526, 545, 574), "rodillo\nde vía", S),
     ((602, 526, 724, 574), "cabezal\nde cosecha", S),
     ((774, 506, 1012, 576), "control de flotabilidad\ncon sistema de control\npor reacción (RCS)", S)]
B = [((1722, 312, 1980, 338), "trayectoria del cabezal", S),
     ((1430, 350, 1496, 392), "junta giratoria\nde 360°", S),
     ((1138, 370, 1370, 438), "control de flotabilidad\ncon sistema de control\npor reacción (RCS)", S),
     ((1662, 394, 1742, 440), "manguera\nde succión", S),
     ((1815, 396, 1908, 442), "red de\ncultivo", S),
     ((1358, 444, 1474, 490), "cabezal\nde cosecha", S),
     ((1674, 514, 1762, 580), "embarcación\nprincipal", S),
     ((1815, 510, 1882, 536), "boyas", S),
     ((1356, 536, 1458, 580), "cable de\ntransporte", S)]
D = [((1740, 820, 2000, 845), "área omitida sin LMM", 27),
     ((1754, 892, 1980, 945), "el cabezal gira\nen estos 2 puntos", 27),
     ((1740, 985, 2000, 1013), "área omitida sin LMM", 27),
     ((1372, 1025, 1688, 1052), "área cosechada dos veces con LMM", 27)]
for LANG in ("EN", "ES"):
    ES = LANG == "ES"
    out = os.path.join(HERE, "out", f"Figure_02_{LANG}.png")
    lab = relabel(relabel(im, A + B, dark=True), D, dark=False) if ES else im
    pa = np.asarray(lab.crop((164, 95, 1060, 604)))
    pb = np.asarray(lab.crop((1113, 99, 2009, 600)))
    pd = np.asarray(lab.crop((1100, 762, 2010, 1056)))



    def num(v, d):
        s = f"{v:.{d}f}"
        return s.replace(".", ",") if ES else s


    T = dict(
        a=("a  Vista lateral", "a  Side view"),
        b=("b  Vista superior y trayectoria del cabezal", "b  Top view and head path"),
        c=("c  Embarcación convencional:\n    trayectoria en espiral", "c  Conventional vessel:\n    spiral path"),
        d=("d  Grid Harvester: giro de 180°\n    en posición fija", "d  Grid Harvester:\n    stationary 180° turn"),
        e=("e  Energía por ciclo de 1,44 ha\n    (Sargassum, 3 kg m⁻², 43,2 t húmedas)",
           "e  Energy per 1.44-ha cycle\n    (Sargassum, 3 kg m⁻², 43.2 t wet)"),
        corners=("esquinas omitidas\nen giros de 90°", "corners missed\nin 90° turns"),
        missed=("{} % del área\ndel ciclo omitida", "{}% of the\ncycle area missed"),
        dnote=("{} % omitida sin LMM;\n{} % cosechada dos veces con LMM",
               "{}% missed without LMM;\n{}% harvested twice with LMM"),
        xe=("MJ por ciclo", "MJ per cycle"),
        bars=(["Embarcación convencional", "Grid Harvester, manguera sin carenar", "Grid Harvester, manguera carenada (85 %)",
               "Manguera carenada + trituración gruesa", "Manguera carenada + maceración fina"],
              ["Conventional vessel", "Grid Harvester, bare hose", "Grid Harvester, faired hose (85%)",
               "Faired hose + coarse chopping", "Faired hose + fine maceration"]),
    )
    L = {k: (v[0] if ES else v[1]) for k, v in T.items()}

    plt.rcParams.update({"axes.titlesize": 6.8, "font.size": 6.3})
    fig = plt.figure(figsize=(128 * MM, 98 * MM))
    outer = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.25], hspace=0.20, left=0.012, right=0.985, top=0.955, bottom=0.085)
    top = outer[0].subgridspec(1, 2, wspace=0.03)
    for pos, arr, t in ((top[0], pa, L["a"]), (top[1], pb, L["b"])):
        ax = fig.add_subplot(pos); ax.imshow(arr); ax.axis("off"); ax.set_title(t, loc="left")
    bot = outer[1].subgridspec(1, 2, wspace=0.08, width_ratios=[1.0, 0.86])
    left = bot[0].subgridspec(2, 1, hspace=0.55, height_ratios=[0.8, 1.0])
    ax = fig.add_subplot(left[0]); F._spiral(ax)
    for t in list(ax.texts):
        s = t.get_text()
        if s.startswith("corners"):
            t.set_text(L["corners"]); t.set_position((250, 62))
        elif "of the" in s:
            t.set_text(L["missed"].format(num(F.HT["conventional"]["missed_pct"], 2))); t.set_position((250, 30))
    ax.set_xlim(-25, 345); ax.set_title(L["c"], loc="left")
    ax = fig.add_subplot(left[1]); ax.imshow(pd); ax.axis("off"); ax.set_title(L["d"], loc="left")
    st = F.HT["grid"]["stationary"]
    ax.text(0.0, -0.04, L["dnote"].replace("\n", " ") if False else L["dnote"].format(num(st["missed_pct"], 2), num(st["lmm_twice_pct"], 2)),
            transform=ax.transAxes, fontsize=5.6, color=F.INK2, va="top")
    ax = fig.add_subplot(bot[1])
    cs = F.HS["cases"]; conv = F.HS["assumptions"]["conventional_cycle_energy_MJ"]
    vals = [conv, cs["bare hose"]["total_MJ"], cs["faired 85% (reference)"]["total_MJ"],
            cs["faired 85% + coarse chopping 0.2 kWh/t"]["total_MJ"], cs["faired 85% + fine maceration 1.0 kWh/t"]["total_MJ"]]
    cols = [F.MUTED, C["blue"], C["blue"], C["yellow"], C["red"]]
    y = np.arange(5)[::-1]
    ax.barh(y, vals, 0.42, color=cols)
    for yy, n in zip(y, L["bars"]):
        ax.text(1, yy + 0.27, n, va="bottom", ha="left", fontsize=5.9, color=F.INK)
    for yy, v in zip(y, vals):
        pct = "" if v == conv else (f" (−{num((1 - v / conv) * 100, 0)} %)" if v < conv else f" (+{num((v / conv - 1) * 100, 0)} %)")
        if not ES: pct = pct.replace(" %", "%")
        ax.text(v + 3, yy, f"{num(v, 1)}{pct}", va="center", fontsize=5.6, color=F.INK2)
    ax.axvline(conv, color=F.MUTED, lw=0.6, ls="--")
    ax.set_yticks([]); ax.set_ylim(-0.5, 4.75)
    ax.set_xlim(0, 260); ax.set_xlabel(L["xe"]); ax.set_title(L["e"], loc="left")
    ax.grid(axis="x", color="#e6e6e6", lw=0.5); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    fig.savefig(out, dpi=600); plt.close(fig)
    print("written", out)
