"""Costa Rican marine space for native-seaweed farms: depth, coast, shipping, fishing and protected-area constraints.

Data
  Natural Earth 1:10m land, admin-0 countries and 200 m / 1,000 m bathymetry (public domain).
  Benden (2022) Global Shipping Lanes v1, doi:10.5281/zenodo.6361763 (CC BY 4.0), clipped to the study area
    (data/shiplanes/shipping_lanes_costa_rica.geojson).
  Port approaches: 8-12 km radius around the commercial and fishing ports.
  Protected areas: Isla del Coco National Park (54,844 km2) and the Seamounts Marine Management Area
    (106,286 km2), both enlarged by executive decree in December 2021, are represented as one disc around
    Isla del Coco whose radius is solved so that the excluded part of the Costa Rican EEZ equals their
    combined 161,130 km2. Coastal marine protected areas lie mostly within the 6-nm zone, which is excluded.
  Fishing: a rule-based proxy (not observed effort):
    0-6 nm from the coast         -> artisanal and small-scale fishing, mangrove and estuary use (excluded)
    6 nm to the 1,000 m isobath   -> semi-industrial shrimp, sardine purse-seine and longline grounds
    beyond 1,000 m                -> pelagic longline and tuna fisheries (low conflict for moored structures)

Method
  0.025-degree grid. Ocean cells are assigned to the nearest country (equidistance approximation) and
  limited to 200 nm from that country's coast (EEZ approximation). Distances and areas are computed in a
  Lambert azimuthal equal-area projection centred on Costa Rica. Cells with latitude > 9.0 N and longitude
  > 84.0 W are Caribbean; all others are Pacific.
"""
import json
import pickle
from pathlib import Path
import os

import numpy as np
import shapefile
import shapely
from shapely.geometry import shape, Point, box
from shapely.ops import unary_union, transform
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
NE = Path(os.environ.get("NATURAL_EARTH_DIR", str(HERE / "data" / "naturalearth")))
LANES = HERE / "data/shiplanes/shipping_lanes_costa_rica.geojson"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
NM = 1.852
BBOX = (-93.0, 1.5, -79.5, 13.5)
CRS = "+proj=laea +lat_0=8 +lon_0=-85 +datum=WGS84 +units=m"
STEP = 0.025
COCOS = (5.528, -87.057)
COCOS_PROTECTED_KM2 = 54844 + 106286
BANDS = (("0-50", 0, 50, 30), ("50-100", 50, 100, 75), ("100-200", 100, 200, 150), ("200-370", 200, 371, 285))

PORTS = {  # name: (lat, lon, approach radius km)
    "Caldera": (9.913, -84.718, 12), "Puntarenas": (9.977, -84.833, 10), "Punta Morales": (10.072, -84.966, 8),
    "Quepos": (9.420, -84.167, 8), "Golfito": (8.620, -83.180, 8), "Playas del Coco": (10.553, -85.700, 8),
    "Moin (APM Terminals)": (10.003, -83.077, 12), "Limon": (9.990, -83.020, 10),
}


def load(path, bbox):
    r = shapefile.Reader(str(path))
    flds = [f[0] for f in r.fields[1:]]
    out = []
    for sr in r.iterShapeRecords():
        g = shape(sr.shape.__geo_interface__)
        if g.intersects(bbox):
            out.append((dict(zip(flds, sr.record)), g.intersection(bbox)))
    return out


def bathymetry(name):
    for sub in ("10m_physical", "10m_physical/ne_10m_bathymetry_all"):
        stem = NE / sub / f"ne_10m_bathymetry_{name}"
        if stem.with_suffix(".shp").exists():
            return stem
    raise FileNotFoundError(f"ne_10m_bathymetry_{name}.shp not found under {NE}; run fetch_natural_earth.py")


def run():
    bb = box(*BBOX)
    to_m = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    to_ll = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
    fm = lambda g: transform(to_m.transform, g)
    fl = lambda g: transform(to_ll.transform, g)

    land = unary_union([g for _, g in load(NE / "10m_physical/ne_10m_land", bb)])
    d200 = unary_union([g for _, g in load(bathymetry("K_200"), bb)])
    d1000 = unary_union([g for _, g in load(bathymetry("J_1000"), bb)])
    ctry = [(r["ADM0_A3"], g) for r, g in load(NE / "10m_cultural/ne_10m_admin_0_countries", bb)]
    names = np.array([c for c, _ in ctry])
    cgeom_m = [fm(g.simplify(0.005)) for _, g in ctry]
    cri_m = unary_union([g for c, g in zip(names, cgeom_m) if c == "CRI"])
    coco_m = Point(*to_m.transform(COCOS[1], COCOS[0]))

    half = {"Major": 10e3, "Middle": 6e3, "Minor": 3e3}
    lanes = json.load(open(LANES))
    lane_polys = [fm(shape(f["geometry"])).buffer(half.get(f["properties"].get("Type", "Minor"), 3e3))
                  for f in lanes["features"]]
    port_m = [Point(*to_m.transform(lon, lat)).buffer(r * 1e3) for lat, lon, r in PORTS.values()]
    ship_m = unary_union(lane_polys + port_m)

    x0, y0, x1, y1 = BBOX
    lons = np.arange(x0 + STEP / 2, x1, STEP)
    lats = np.arange(y0 + STEP / 2, y1, STEP)
    LON, LAT = np.meshgrid(lons, lats)
    lon, lat = LON.ravel(), LAT.ravel()
    cell = (STEP * 111.32 * np.cos(np.radians(lat))) * (STEP * 110.57)
    ocean = ~shapely.contains_xy(land, lon, lat)
    lon, lat, cell = lon[ocean], lat[ocean], cell[ocean]
    X, Y = to_m.transform(lon, lat)
    pts = shapely.points(X, Y)
    tree = shapely.STRtree(cgeom_m)
    idx = tree.query_nearest(pts, return_distance=False, all_matches=False)
    nearest = names[idx[1][np.argsort(idx[0])]]
    dist = shapely.distance(cri_m, pts) / 1e3
    keep = (nearest == "CRI") & (dist <= 370.4)
    lon, lat, cell, X, Y, pts, dist = (a[keep] for a in (lon, lat, cell, X, Y, pts, dist))
    # distance to the mainland coast (the shipping distance to a refinery); Isla del Coco is ~530 km offshore
    main = max(shapely.get_parts(unary_union([g for c, g in zip(names, cgeom_m) if c == "CRI"])), key=lambda g: g.area)
    dist_main = shapely.distance(main, pts) / 1e3
    depth = np.where(shapely.contains_xy(d1000, lon, lat), ">1000",
                     np.where(shapely.contains_xy(d200, lon, lat), "200-1000", "0-200"))
    ship = shapely.contains_xy(ship_m, X, Y)
    inshore = dist <= 6 * NM
    fish = np.where(inshore, "artisanal_0-6nm", np.where(depth == ">1000", "deep_low", "shelf_slope_fisheries"))
    reg = np.where((lat > 9.0) & (lon > -84.0), "Caribbean", "Pacific")
    # protected disc around Isla del Coco sized to the decreed area
    dcoco = shapely.distance(coco_m, pts) / 1e3
    order = np.argsort(dcoco)
    cum = np.cumsum(cell[order])
    r_coco = float(dcoco[order][np.searchsorted(cum, COCOS_PROTECTED_KM2)])
    mpa = dcoco <= r_coco
    return dict(lon=lon, lat=lat, cell=cell, depth=depth, ship=ship, fish=fish, reg=reg, dist=dist,
                dist_main=dist_main, mpa=mpa, r_coco_km=r_coco, land=land, ship_ll=fl(ship_m),
                lanes_ll=[fl(l) for l in lane_polys], cri_ll=fl(cri_m))


def band_of(km):
    out = np.full(km.shape, "", dtype=object)
    for name, lo, hi, _ in BANDS:
        out[(km >= lo) & (km < hi)] = name
    return out


def summarise(L):
    c = L["cell"]
    s = {"eez_km2": float(c.sum()), "r_cocos_disc_km": L["r_coco_km"], "protected_cocos_km2": float(c[L["mpa"]].sum())}
    for reg in ("Pacific", "Caribbean"):
        r = L["reg"] == reg
        s[reg] = {"total_km2": float(c[r].sum()), "protected_km2": float(c[r & L["mpa"]].sum()),
                  "shipping_km2": float(c[r & L["ship"]].sum()), "artisanal_0_6nm_km2": float(c[r & (L["fish"] == "artisanal_0-6nm")].sum())}
        for dep in ("0-200", "200-1000", ">1000"):
            s[reg][f"depth_{dep}_km2"] = float(c[r & (L["depth"] == dep)].sum())
    # free area: outside lanes and ports, beyond 6 nm, outside the Cocos protected areas, by zone and band
    ok = (~L["ship"]) & (L["fish"] != "artisanal_0-6nm") & (~L["mpa"])
    band = band_of(L["dist_main"])
    zones = {}
    for reg, pre in (("Pacific", "pac"), ("Caribbean", "car")):
        for dep, suf in (("0-200", "shelf"), ("200-1000", "slope"), (">1000", "deep")):
            m = ok & (L["reg"] == reg) & (L["depth"] == dep)
            zones[f"{pre}_{suf}"] = {b: round(float(c[m & (band == b)].sum()), 0) for b, *_ in BANDS
                                    if c[m & (band == b)].sum() > 0}
    s["free_area_by_zone_and_band_km2"] = zones
    return s


if __name__ == "__main__":
    L = run()
    S = summarise(L)
    json.dump(S, open(OUT / "marine_space.json", "w"), indent=1)
    pickle.dump(L, open(OUT / "_layers.pkl", "wb"))
    print(json.dumps(S, indent=1))
