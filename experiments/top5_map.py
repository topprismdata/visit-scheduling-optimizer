# -*- coding: utf-8 -*-
"""TOP5 地盘图 — H3 片区 + 店点按星期染色 (单文件 HTML, 可缩放).

坐标纪律: 全部坐标是 GCJ02 → 底图必须用 GCJ02 瓦片(高德), 否则整体偏移 ~500m。
空间口径: H3 res7 相邻格连通块 = 片区; 六边形按片区着色。
店点颜色 = 该店 8 月"实际到访最多的星期"; 点大小 = 实际到访次数。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import h3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WD_LABEL = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WD_COLOR = ["#e6194b", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#7f7f7f"]
ZONE_COLOR = ["#2563eb", "#dc2626", "#16a34a", "#ca8a04", "#9333ea", "#0891b2", "#be185d"]

LINES = [
    ("000699979", "广州海珠", "街坊扫楼型", "33 km² 一整块，店距 75 m，日半径 0.84 km，零缺访"),
    ("000700020", "广州天河", "CBD 密集带型", "东西 10.4 km 窄带，店距 42 m（最密），缺 1 家不补"),
    ("000855388", "杭州萧山", "窄走廊纵贯型", "东西仅 6.7 km × 南北 15.1 km 走廊，缺 12 家不补"),
    ("000734621", "无锡新吴", "一主一副·会回头补", "副片 15.2 km 外，W1 缺 16 补 12，相位 72.8%（最低）"),
    ("000782642", "惠州惠阳", "大片扫荡+边角游击", "34×38 km、6 片含飞地最远 34 km，覆盖 85.9%（最差）"),
]


def components(cells):
    cs = set(cells)
    comp = {}
    for c in cs:
        if c in comp:
            continue
        stack, grp = [c], set()
        while stack:
            x = stack.pop()
            if x in grp:
                continue
            grp.add(x)
            stack += [nb for nb in h3.grid_disk(x, 1) if nb in cs and nb not in grp]
        g = min(grp)
        for x in grp:
            comp[x] = g
    return comp


def build():
    plan = pd.read_excel("/Users/ghb/UFS-demo/8月规划结果-调整.xlsx")
    act = pd.read_csv("/Users/ghb/UFS-demo/8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    plan["customer_code"] = plan["customer_code"].astype(str)
    act["customer_code"] = act["customer_code"].astype(str)
    act["wd"] = pd.to_datetime(act["call_date"]).dt.dayofweek
    panels = []
    for code, city, kind, blurb in LINES:
        pl = plan[plan["sales_line_code"] == code].copy()
        pl["lat"] = pd.to_numeric(pl["lat"], errors="coerce")
        pl["lng"] = pd.to_numeric(pl["lng"], errors="coerce")
        sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
        a = act[act["salesperson_code"] == code]
        vc = a.groupby("customer_code").size().to_dict()
        vwd = a.groupby("customer_code")["wd"].apply(lambda s: int(s.value_counts().index[0])).to_dict()
        pwd = {r.customer_code: (pd.Timestamp(r.plan_day).dayofweek if pd.notna(r.plan_day) else None)
               for r in pl.drop_duplicates("customer_code").itertuples()}
        cells = {r.customer_code: h3.latlng_to_cell(float(r.lat), float(r.lng), 7) for r in sto.itertuples()}
        comp = components(list(cells.values()))
        zone_of = {c: comp[cells[c]] for c in cells}
        zones = sorted(set(zone_of.values()))
        zidx = {z: i for i, z in enumerate(zones)}
        hexes = {}
        for c in set(cells.values()):
            z = zidx[comp[c]]
            b = [[round(float(la), 6), round(float(lo), 6)] for la, lo in h3.cell_to_boundary(c)]
            hexes.setdefault(z, []).append(b)
        stores = []
        for r in sto.itertuples():
            n = int(vc.get(r.customer_code, 0))
            wd = vwd.get(r.customer_code, pwd.get(r.customer_code))
            stores.append({"c": r.customer_code, "n": str(r.customer_name),
                           "ad": str(r.customer_address)[:60],
                           "la": round(float(r.lat), 6), "lo": round(float(r.lng), 6),
                           "v": n, "w": (wd if wd is not None else 0),
                           "plan_wd": (pwd.get(r.customer_code) if pwd.get(r.customer_code) is not None else -1),
                           "z": zidx[zone_of[r.customer_code]]})
        panels.append({"code": code, "city": city, "kind": kind, "blurb": blurb,
                       "stores": stores, "zones": [hexes[i] for i in range(len(zones))],
                       "n_zone": len(zones), "n_store": len(sto), "n_visit": len(a)})
        print(f"{code} {city}: 店 {len(sto)} 片区 {len(zones)} 六边格 {sum(len(v) for v in hexes.values())} 实际到访 {len(a)}")
    return panels


HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>TOP5 地盘图 · 2026-08</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
 body{margin:0;background:#0f1115;color:#e6e6e6;font:13px/1.5 -apple-system,"PingFang SC",sans-serif}
 header{padding:14px 18px;border-bottom:1px solid #232733}
 h1{font-size:17px;margin:0 0 4px} .sub{color:#8b93a7;font-size:12px}
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(520px,1fr));gap:12px;padding:12px}
 .card{background:#161a22;border:1px solid #232733;border-radius:10px;overflow:hidden}
 .hd{padding:10px 12px;display:flex;justify-content:space-between;align-items:baseline;gap:8px}
 .hd b{font-size:14px} .kind{color:#7dd3fc;font-size:12px}
 .blurb{color:#8b93a7;font-size:12px;padding:0 12px 8px}
 .map{height:460px;background:#0b0d12}
 .lg{padding:8px 12px;display:flex;flex-wrap:wrap;gap:10px;font-size:12px;color:#aab3c5;border-top:1px solid #232733}
 .sw{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:-1px}
 .zn{display:inline-block;width:10px;height:10px;margin-right:4px;vertical-align:-1px;opacity:.55}
 .note{padding:10px 18px 24px;color:#8b93a7;font-size:12px}
</style></head><body>
<header>
 <h1>TOP5（采纳率最高）地盘图 · 2026-08</h1>
 <div class="sub">底图：高德 GCJ02 瓦片（与门店坐标同基准，不转换）。六边形=H3 res7 格，同色相邻格=一个「片区」；圆点=门店，颜色=8 月实际到访最多的星期，大小=到访次数。</div>
</header>
<div class="grid" id="g"></div>
<div class="note">口径：采纳率 612 线中 188 条并列 100%，本页 5 人按 采纳率→含日期→编排量→线码 取。生成脚本 <code>experiments/top5_map.py</code>。</div>
<script>
const DATA = __DATA__;
const WDL = __WDL__, WDC = __WDC__, ZC = __ZC__;
const g = document.getElementById('g');
DATA.forEach((p, i) => {
  const card = document.createElement('div'); card.className = 'card';
  card.innerHTML = `<div class="hd"><b>${p.code} · ${p.city}</b><span class="kind">${p.kind}</span></div>
   <div class="blurb">${p.blurb}<br>店 ${p.n_store} · 片区 ${p.n_zone} · 实际到访 ${p.n_visit}</div>
   <div class="map" id="m${i}"></div>
   <div class="lg">${WDL.map((n,k)=>`<span><i class="sw" style="background:${WDC[k]}"></i>${n}</span>`).join('')}
   <span>| 片区: ${p.zones.map((_,k)=>`<i class="zn" style="background:${ZC[k%ZC.length]}"></i>${k+1}`).join('')}</span></div>`;
  g.appendChild(card);
  const map = L.map('m'+i, {zoomControl:true, attributionControl:false});
  L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
              {subdomains:'1234', maxZoom:18}).addTo(map);
  const bounds = [];
  p.zones.forEach((hs, k) => hs.forEach(h => {
    L.polygon(h, {color:ZC[k%ZC.length], weight:1, opacity:.85, fillColor:ZC[k%ZC.length], fillOpacity:.10}).addTo(map);
    h.forEach(c => bounds.push(c));
  }));
  p.stores.forEach(s => {
    L.circleMarker([s.la, s.lo], {radius: 2.6 + Math.min(s.v,6)*1.1, color:'#0b0d12', weight:.5,
      fillColor: WDC[s.w], fillOpacity:.95})
      .bindPopup(`<b>${s.n}</b><br>${s.ad}<br>客户码 ${s.c}<br>实际到访 ${s.v} 次 · 主力星期 ${WDL[s.w]}${s.plan_wd>=0?` · 计划星期 ${WDL[s.plan_wd]}`:''}<br>片区 ${s.z+1}`)
      .addTo(map);
    bounds.push([s.la, s.lo]);
  });
  map.fitBounds(bounds, {padding:[12,12]});
});
</script></body></html>
"""


def main():
    panels = build()
    html = (HTML.replace("__DATA__", json.dumps(panels, ensure_ascii=False))
                .replace("__WDL__", json.dumps(WD_LABEL, ensure_ascii=False))
                .replace("__WDC__", json.dumps(WD_COLOR))
                .replace("__ZC__", json.dumps(ZONE_COLOR)))
    out = ROOT / "docs/reports/2026-09-22-top5-map.html"
    out.write_text(html, encoding="utf-8")
    print(f"写出 {out} ({out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()