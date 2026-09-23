# -*- coding: utf-8 -*-
"""沿路走廊服务 — 把"当天门店"连成沿道路走的一条线(Corridor), 供对比页面调用.

为什么需要它: 直线连点会出现折线, 而"走廊"必须沿路。本服务用路网服务(默认 FOSSGIS OSRM,
可换本地/腾讯)把当天点集作为途经点请求真实道路几何。

坐标纪律: 数据是 GCJ02 → 请求前转 WGS84, 返回几何再转回 GCJ02(与高德底图一致)。
密钥纪律: 只用环境变量; 不写入任何文件。

接口:
  GET /corridor?line=<线号>&scope=<all|1|2|3|4|5>   → {days_plan:[[dow,geom]], days_act:[[dow,geom]], cached:bool}
  GET /health
缓存: output/rep_behavior/roads/<line>_<scope>.json
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
UFS = Path("/Users/ghb/UFS-demo")
CACHE = ROOT / "output" / "rep_behavior" / "roads"
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
OSRM = os.environ.get("OSRM_URL", "https://routing.openstreetmap.de/routed-car")
PROVIDER = os.environ.get("ROAD_PROVIDER", "osrm")          # osrm | tencent
TC_KEY = os.environ.get("TENCENT_MAP_KEY", "")              # 只来自环境变量, 不写文件
PORT = int(os.environ.get("ROAD_PORT", "8770"))
LOCK = threading.Lock()

# ---------- 坐标转换 (GCJ02 <-> WGS84) ----------
_A = 6378245.0
_EE = 0.00669342162296594323


def _out_of_china(lat, lng):
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _tlat(x, y):
    r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    r += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return r


def _tlng(x, y):
    r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    r += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return r


def gcj2wgs(lat, lng):
    if _out_of_china(lat, lng):
        return lat, lng
    dlat, dlng = _tlat(lng - 105.0, lat - 35.0), _tlng(lng - 105.0, lat - 35.0)
    rlat = lat / 180.0 * math.pi
    m = math.sin(rlat)
    m = 1 - _EE * m * m
    sm = math.sqrt(m)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (m * sm) * math.pi)
    dlng = (dlng * 180.0) / (_A / sm * math.cos(rlat) * math.pi)
    return lat - dlat, lng - dlng


def wgs2gcj(lat, lng):
    if _out_of_china(lat, lng):
        return lat, lng
    dlat, dlng = _tlat(lng - 105.0, lat - 35.0), _tlng(lng - 105.0, lat - 35.0)
    rlat = lat / 180.0 * math.pi
    m = math.sin(rlat)
    m = 1 - _EE * m * m
    sm = math.sqrt(m)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (m * sm) * math.pi)
    dlng = (dlng * 180.0) / (_A / sm * math.cos(rlat) * math.pi)
    return lat + dlat, lng + dlng


# ---------- 数据 ----------
def load():
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wk"] = ((plan["plan_day"].dt.day - 1) // 7 + 1)
    plan["lat"] = pd.to_numeric(plan["lat"], errors="coerce")
    plan["lng"] = pd.to_numeric(plan["lng"], errors="coerce")
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code", "start_time",
                               "longitude", "latitude"])
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wk"] = ((act["call_date"].dt.day - 1) // 7 + 1)
    act["lat"] = pd.to_numeric(act["latitude"], errors="coerce")
    act["lng"] = pd.to_numeric(act["longitude"], errors="coerce")
    return plan, act


PLAN, ACT = load()


def nn_order(pts):
    pts = list(pts)
    if len(pts) < 2:
        return pts
    out = [pts.pop(0)]
    while pts:
        last = out[-1]
        j = min(range(len(pts)), key=lambda i: (pts[i][0] - last[0]) ** 2 + (pts[i][1] - last[1]) ** 2)
        out.append(pts.pop(j))
    return out


def tc_decode(poly):
    """腾讯 polyline: 扁平数组 [lat0,lng0, dlat1,dlng1, ...] (1e6 差分) → [[lat,lng]] GCJ02."""
    nums = [int(x) for x in poly] if isinstance(poly, (list, tuple)) else [int(x) for x in str(poly).split(",")]
    if len(nums) % 2:
        nums = nums[:-1]
    la, lo = nums[0] / 1e6, nums[1] / 1e6
    out = [[round(la, 5), round(lo, 5)]]
    for i in range(2, len(nums), 2):
        la += nums[i] / 1e6
        lo += nums[i + 1] / 1e6
        out.append([round(la, 5), round(lo, 5)])
    return out


def tencent_route(pts):
    """用腾讯驾车路径规划串当天点(每次最多 3 个途经点, 自动分段)。GCJ02 直进直出。"""
    if len(pts) < 2 or not TC_KEY:
        return None
    out = []
    i = 0
    while i < len(pts) - 1:
        chunk = pts[i:i + 5]                     # from + to + ≤3 waypoints
        if len(chunk) < 2:
            break
        frm = f"{chunk[0][0]:.6f},{chunk[0][1]:.6f}"
        to = f"{chunk[-1][0]:.6f},{chunk[-1][1]:.6f}"
        wp = ";".join(f"{a:.6f},{b:.6f}" for a, b in chunk[1:-1])
        url = (f"https://apis.map.qq.com/ws/direction/v1/driving/?from={frm}&to={to}"
               + (f"&waypoints={wp}" if wp else "") + f"&key={TC_KEY}")
        got = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=15) as r:
                    j = json.loads(r.read().decode())
                if j.get("status") == 0 and j.get("result", {}).get("routes"):
                    got = tc_decode(j["result"]["routes"][0]["polyline"])
                    break
                time.sleep(0.6 * (attempt + 1))
            except Exception:
                time.sleep(1.0 * (attempt + 1))
        if not got and len(chunk) > 2:            # 途经点不被支持 → 逐段请求
            got = []
            for k in range(len(chunk) - 1):
                seg = tencent_route([chunk[k], chunk[k + 1]])
                if not seg:
                    return None
                got += seg if not got else seg[1:]
            return (out + got[1:]) if out else got
        if not got:
            return None
        out += got if not out else got[1:]
        i += len(chunk) - 1
        time.sleep(0.35)                          # 限流: ≥60ms, 这里更保守
    return out or None


def osrm_route(pts):
    """pts: [[lat,lng], ...] GCJ02 → 沿路几何 GCJ02。"""
    if len(pts) < 2:
        return pts
    coords = []
    for la, lo in pts:
        wla, wlo = gcj2wgs(la, lo)
        coords.append(f"{wlo:.6f},{wla:.6f}")
    url = f"{OSRM}/route/v1/driving/" + ";".join(coords) + "?overview=simplified&geometries=geojson"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                j = json.loads(r.read().decode())
            if j.get("code") != "Ok":
                break
            line = j["routes"][0]["geometry"]["coordinates"]
            return [[round(la, 5), round(lng, 5)] for lng, la in (wgs2gcj(p[1], p[0]) for p in line)]
        except Exception:
            time.sleep(1.2 * (attempt + 1))
    return None


def build(line, scope):
    key = f"{line}_{scope}"
    f = CACHE / f"{key}.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        d["cached"] = True
        return d
    pl = PLAN[PLAN["sales_line_code"] == line]
    xy = (pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
            .set_index("customer_code")[["lat", "lng"]].rename(columns={"lat": "plat", "lng": "plng"}))
    al = ACT[(ACT["salesperson_code"] == line) & (ACT["customer_code"].isin(set(xy.index)))].join(xy, on="customer_code")
    if scope != "all":
        pl = pl[pl["wk"] == int(scope)]
        al = al[al["wk"] == int(scope)]

    def days(df, datecol, pts_of):
        out = []
        for d, g in df.groupby(df[datecol]):
            pts = [p for p in (pts_of(r) for r in g.itertuples()) if p]
            if len(pts) < 2:
                continue
            seq = nn_order(pts)
            geom = tencent_route(seq) if PROVIDER == "tencent" else osrm_route(seq)
            time.sleep(0.25)
            out.append([int(pd.Timestamp(d).dayofweek), geom if geom else [[round(a, 5), round(b, 5)] for a, b in nn_order(pts)],
                        "road" if geom else "straight"])
        return out

    res = {"line": line, "scope": scope, "cached": False,
           "days_plan": days(pl, "plan_day", lambda r: (float(r.lat), float(r.lng)) if r.lat == r.lat else None),
           "days_act": days(al, "call_date", lambda r: (float(r.plat), float(r.plng)) if r.plat == r.plat else None)}
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res


class H(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/health":
            return self._send({"ok": True, "osrm": OSRM})
        if u.path == "/corridor":
            line = (q.get("line") or [""])[0]
            scope = (q.get("scope") or ["all"])[0]
            if not line:
                return self._send({"error": "line required"}, 400)
            try:
                with LOCK:
                    return self._send(build(line, scope))
            except Exception as e:
                return self._send({"error": f"{type(e).__name__}: {e}"}, 500)
        return self._send({"error": "not found"}, 404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"沿路走廊服务 :{PORT} | OSRM={OSRM} | 缓存 {CACHE}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()