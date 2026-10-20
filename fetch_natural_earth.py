"""Download the Natural Earth 1:10m layers used by spatial.py (public domain) into data/naturalearth/."""
from pathlib import Path
from urllib.request import urlretrieve

HERE = Path(__file__).resolve().parent
BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
SETS = [("10m_physical", "ne_10m_land"), ("10m_cultural", "ne_10m_admin_0_countries"),
        ("10m_physical/ne_10m_bathymetry_all", "ne_10m_bathymetry_K_200"),
        ("10m_physical/ne_10m_bathymetry_all", "ne_10m_bathymetry_J_1000")]
for group, name in SETS:
    d = HERE / "data" / "naturalearth" / group
    d.mkdir(parents=True, exist_ok=True)
    for ext in ("shp", "shx", "dbf", "prj"):
        f = d / f"{name}.{ext}"
        if not f.exists():
            urlretrieve(f"{BASE}{group}/{name}.{ext}", f)
    print("installed", name)
