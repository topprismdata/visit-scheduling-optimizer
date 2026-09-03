# -*- coding: utf-8 -*-
"""Zone graph: 路网区块 → 聚类 + 约束提取.
- 从 GeoJSON 加载区块，分配门店到区块
- 相邻检测 (多边形边共享)
- 参考: Cook, Held, Helsgaun (2022) "Constrained Local Search for Last-Mile Routing"
"""
import json, math


class ZoneGraph:
    """区块图: 加载、落块、相邻."""

    def __init__(self, geojson_path: str, keep_codes: set = None):
        self.zones = {}  # zone_id -> {poly, xmin, xmax, ymin, ymax, centroid}
        self.adj = {}    # zone_id -> set[zone_id] (相邻)
        self._load(geojson_path, keep_codes)

    def _load(self, path, keep_codes):
        gj = json.load(open(path))
        for i, f in enumerate(gj["features"]):
            p = f["properties"]
            if keep_codes and p.get("区县编码") not in keep_codes:
                continue
            poly = f["geometry"]["coordinates"][0]
            xs = [c[0] for c in poly]; ys = [c[1] for c in poly]
            zid = str(i)
            self.zones[zid] = {
                "poly": poly,
                "xmin": min(xs), "xmax": max(xs),
                "ymin": min(ys), "ymax": max(ys),
                "centroid": ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2),
            }
        zids = list(self.zones.keys())
        self.adj = {z: set() for z in zids}
        for i, zi in enumerate(zids):
            for zj in zids[i+1:]:
                if self._edges_share(self.zones[zi]["poly"], self.zones[zj]["poly"]):
                    self.adj[zi].add(zj); self.adj[zj].add(zi)

    @staticmethod
    def _edges_share(p1, p2):
        e1 = set()
        for i in range(len(p1)-1):
            t = (round(p1[i][0],6),round(p1[i][1],6),round(p1[i+1][0],6),round(p1[i+1][1],6))
            t2 = (t[0],t[1],t[2],t[3]) if (t[0],t[1])<(t[2],t[3]) else (t[2],t[3],t[0],t[1])
            e1.add(t2)
        for i in range(len(p2)-1):
            t = (round(p2[i][0],6),round(p2[i][1],6),round(p2[i+1][0],6),round(p2[i+1][1],6))
            t2 = (t[0],t[1],t[2],t[3]) if (t[0],t[1])<(t[2],t[3]) else (t[2],t[3],t[0],t[1])
            if t2 in e1: return True
        return False

    @staticmethod
    def _pip(lng, lat, poly):
        inside = False; j = len(poly)-1
        for i in range(len(poly)):
            xi, yi = poly[i]; xj, yj = poly[j]
            if ((yi>lat)!=(yj>lat)) and (lng<(xj-xi)*(lat-yi)/(yj-yi)+xi): inside = not inside
            j = i
        return inside

    def assign_stores(self, lons, lats):
        """Return [zone_id] for each store index."""
        result = []
        for lo, la in zip(lons, lats):
            cands = [z for z in self.zones if self.zones[z]["xmin"]<=lo<=self.zones[z]["xmax"]
                     and self.zones[z]["ymin"]<=la<=self.zones[z]["ymax"]]
            found = None
            for z in cands:
                if self._pip(lo, la, self.zones[z]["poly"]): found = z; break
            if not found and cands:
                found = min(cands, key=lambda z: (self.zones[z]["centroid"][0]-lo)**2
                           + (self.zones[z]["centroid"][1]-la)**2)
            if not found:
                found = min(self.zones, key=lambda z: (self.zones[z]["centroid"][0]-lo)**2
                           + (self.zones[z]["centroid"][1]-la)**2)
            result.append(found)
        return result


def _load_blocks(path: str, keep_codes: set):
    gj = json.load(open(path))
    out = []
    for i, f in enumerate(gj["features"]):
        if keep_codes and f["properties"].get("区县编码") not in keep_codes:
            continue
        poly = f["geometry"]["coordinates"][0]
        xs = [c[0] for c in poly]; ys = [c[1] for c in poly]
        out.append((str(i), poly, min(xs), max(xs), min(ys), max(ys),
                    ((min(xs)+max(xs))/2, (min(ys)+max(ys))/2)))
    return out


def assign_zones_only(path: str, lons, lats, keep_codes: set) -> list:
    """轻量落块: 仅逐点 PIP, 不做多边形两两邻接 (v3/几何抓取用). 避免 1667² 邻接的卡死."""
    blocks = _load_blocks(path, keep_codes)
    result = []
    for lo, la in zip(lons, lats):
        found = None
        for z, poly, xmin, xmax, ymin, ymax, _ in blocks:
            if xmin <= lo <= xmax and ymin <= la <= ymax and ZoneGraph._pip(lo, la, poly):
                found = z; break
        if found is None:
            cands = [b for b in blocks if b[2] <= lo <= b[3] and b[4] <= la <= b[5]]
            found = (min(cands, key=lambda b: (b[6][0]-lo)**2 + (b[6][1]-la)**2)[0]
                     if cands else min(blocks, key=lambda b: (b[6][0]-lo)**2 + (b[6][1]-la)**2)[0])
        result.append(found)
    return result
