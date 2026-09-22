# -*- coding: utf-8 -*-
"""TOP5 地盘图 v2 — 离线自包含 + H3 面按星期染色 + 未访店清单.

老板要求(2026-09-22): 专心解决 TOP5 地图。本版解决三件事:
  1) 离线可用: 内嵌 Leaflet(不依赖 CDN); 底图瓦片仍走高德(GCJ02, 与坐标同基准), 瓦片挂掉时降级为深色底+网格提示, 几何图形照常显示
  2) 口径分开: 面(片区)与点(门店)各自可切换 "实际 / 计划", 避免混读; 未访店统一红虚线空心
  3) 结论可见: H3 面按"实际主力星期"染色 → 一眼看出"一天只耕一片、一周固定几条街"

坐标纪律: 全部坐标 GCJ02 → 底图必须 GCJ02(高德), 不转换。
禁用: xlsx"拜访顺序"串链算距离 (AGENTS.md 铁律)。
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
ZONE_COLOR = ["#2563eb", "#dc2626", "#16a34a", "#ca8a04", "#9333ea", "#0891b2", "#be185d", "#4d7c0f", "#b45309"]

LINES = [
    ("000699979", "广州海珠", "街坊扫楼型"),
    ("000700020", "广州天河", "CBD 密集带型"),
    ("000855388", "杭州萧山", "窄走廊纵贯型"),
    ("000734621", "无锡新吴", "一主一副·会回头补"),
    ("000782642", "惠州惠阳", "大片扫荡+边角游击"),
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
    plan["wd"] = pd.to_datetime(plan["plan_day"]).dt.dayofweek
    panels = []
    for code, city, kind in LINES:
        pl = plan[plan["sales_line_code"] == code].copy()
        pl["lat"] = pd.to_numeric(pl["lat"], errors="coerce")
        pl["lng"] = pd.to_numeric(pl["lng"], errors="coerce")
        sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
        a = act[act["salesperson_code"] == code]
        vc = a.groupby("customer_code").size().to_dict()
        vwd = a.groupby("customer_code")["wd"].apply(lambda s: int(s.value_counts().index[0])).to_dict()
        # 每店: 实际访问星期集合(用于判定"计划/实际不一致")
        vset = a.groupby("customer_code")["wd"].apply(set).to_dict()
        pwd = pl.drop_duplicates("customer_code").set_index("customer_code")["wd"].to_dict()
        cells = {r.customer_code: h3.latlng_to_cell(float(r.lat), float(r.lng), 7) for r in sto.itertuples()}
        comp = components(list(cells.values()))
        zone_of = {c: comp[cells[c]] for c in cells}
        zones = sorted(set(zone_of.values()))
        zidx = {z: i for i, z in enumerate(zones)}
        # 面(H3 格): 该格内门店的实际主力星期 / 计划主力星期
        cell_act, cell_plan = {}, {}
        for r in sto.itertuples():
            c = cells[r.customer_code]
            w = vwd.get(r.customer_code)
            if w is not None:
                cell_act.setdefault(c, {}).setdefault(w, 0)
                cell_act[c][w] += int(vc.get(r.customer_code, 0))
            pw = pwd.get(r.customer_code)
            if pw is not None and pw == pw:
                cell_plan.setdefault(c, {}).setdefault(int(pw), 0)
                cell_plan[c][int(pw)] += 1
        hexes = []
        for c in sorted(set(cells.values())):
            ring = [[round(float(la), 6), round(float(lo), 6)] for la, lo in h3.cell_to_boundary(c)]
            wa = max(cell_act[c], key=cell_act[c].get) if c in cell_act else -1
            wp = max(cell_plan[c], key=cell_plan[c].get) if c in cell_plan else -1
            hexes.append({"ring": ring, "z": zidx[zone_of[next(k for k, v in cells.items() if v == c)]],
                          "wa": int(wa), "wp": int(wp)})
        stores, never = [], []
        for r in sto.itertuples():
            n = int(vc.get(r.customer_code, 0))
            wd = vwd.get(r.customer_code)
            pw = pwd.get(r.customer_code)
            pww = pwd.get(r.customer_code)
            mism = (wd is not None and pww is not None and pww == pww
                    and int(pww) not in vset.get(r.customer_code, set()))
            rec = {"c": r.customer_code, "n": str(r.customer_name), "ad": str(r.customer_address)[:60], "mismatch": bool(mism),
                   "la": round(float(r.lat), 6), "lo": round(float(r.lng), 6), "v": n,
                   "w": (wd if wd is not None else -1),
                   "pw": (int(pw) if pw is not None and pw == pw else -1),
                   "z": zidx[zone_of[r.customer_code]]}
            stores.append(rec)
            if n == 0:
                never.append({"n": rec["n"], "ad": rec["ad"], "c": rec["c"], "pw": rec["pw"]})
        # 统计: 覆盖 / 日均店数 / 计划-实际 星期不一致店数
        per_day = a.assign(d=pd.to_datetime(a["call_date"])).groupby("d").size()
        mismatch = sum(1 for r in sto.itertuples()
                       if vwd.get(r.customer_code) is not None and pwd.get(r.customer_code) is not None
                       and pwd.get(r.customer_code) == pwd.get(r.customer_code)
                       and int(pwd[r.customer_code]) not in vset.get(r.customer_code, set()))
        panels.append({
            "code": code, "city": city, "kind": kind,
            "n_store": len(sto), "n_visit": len(a), "n_zone": len(zones),
            "cover": round(len(set(a["customer_code"]) & set(sto["customer_code"])) / max(len(sto), 1) * 100, 1),
            "daily": int(per_day.median()) if len(per_day) else 0,
            "never": never, "n_never": len(never), "mismatch": mismatch,
            "stores": stores, "hexes": hexes,
        })
        print(f"{code} {city}: 店 {len(sto)} 片区 {len(zones)} 格 {len(hexes)} 未访 {len(never)} "
              f"覆盖 {panels[-1]['cover']}% 日均 {panels[-1]['daily']} 店 星期错位 {mismatch}")
    return panels


HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>TOP5 地盘图 · 计划 vs 实际 · 2026-08</title>
<style>__LEAFLET_CSS__</style>
<style>
 body{margin:0;background:#0f1115;color:#e6e6e6;font:13px/1.55 -apple-system,"PingFang SC",sans-serif}
 header{padding:14px 18px;border-bottom:1px solid #232733}
 h1{font-size:17px;margin:0 0 4px} .sub{color:#8b93a7;font-size:12px;line-height:1.75}
 .row{border-top:1px solid #232733;padding:10px 12px 6px}
 .rowhd{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}
 .rowhd b{font-size:14px} .kind{color:#7dd3fc;font-size:12px}
 .stat{color:#9aa4b8;font-size:12px} .stat b{color:#e6e6e6}
 .pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}
 .colhd{font-size:12px;padding:2px 0 4px;display:flex;justify-content:space-between}
 .colL .colhd{color:#93c5fd} .colR .colhd{color:#fca5a5}
 .map{height:430px;background:#0b0d12;border-radius:8px;overflow:hidden}
 .ctrl{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0}
 .ctrl button{padding:3px 9px;font-size:12px;background:#1f2430;color:#cbd5e1;border:1px solid #2f3646;border-radius:6px;cursor:pointer}
 .ctrl button.on{background:#2b3a55;color:#fff;border-color:#3f5680}
 .lg{display:flex;flex-wrap:wrap;gap:9px;font-size:12px;color:#aab3c5;align-items:center;padding-top:6px}
 .sw{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:-1px}
 details{font-size:12px;color:#aab3c5;padding:4px 0 8px} summary{cursor:pointer;color:#fca5a5}
 .never{max-height:170px;overflow:auto;border:1px solid #232733;border-radius:6px;margin-top:6px;padding:6px 8px;background:#12151c}
 .never div{padding:2px 0;border-bottom:1px dashed #232733} .never div:last-child{border:0}
 .noTile{position:absolute;z-index:400;margin:6px 8px;padding:3px 7px;font-size:11px;background:#7c2d12cc;color:#fff;border-radius:5px}
 .note{padding:12px 18px 26px;color:#8b93a7;font-size:12px}
</style></head><body>
<header>
 <h1>TOP5（采纳率最高）地盘图 · 同一人左右对比</h1>
 <div class="sub">
  <b>左＝计划安排</b>（面按计划星期、点按计划星期）；<b>右＝实际走访</b>（面按实际主力星期、点按实际主力星期，点大小＝到访次数）。<br>
  两侧视野联动（拖一边另一边跟着走），同一范围对位比较；<b>红虚线空心圈</b>＝本月未到访；<b>金色描边点</b>＝计划星期未被执行到的店（星期错位）。<br>
  坐标与底图同为 GCJ02（高德瓦片，不转换）；Leaflet 已内嵌，断网仍可看几何。人数：采纳率 612 线中 188 条并列 100%，5 人按 采纳率→含日期→编排量→线码 取。
 </div>
</header>
<div id="g"></div>
<div class="note">生成：<code>experiments/top5_map.py</code>（离线自包含单文件）。</div>
<script>__LEAFLET_JS__</script>
<script>
const DATA = __DATA__, WDL = __WDL__, WDC = __WDC__, ZC = __ZC__;
const g = document.getElementById('g');
DATA.forEach((p, i) => {
  const row = document.createElement('div'); row.className = 'row';
  row.innerHTML = `<div class="rowhd">
      <b>${p.code} · ${p.city}</b><span class="kind">${p.kind}</span>
      <span class="stat">门店 <b>${p.n_store}</b> · 片区 <b>${p.n_zone}</b> · 到访 <b>${p.n_visit}</b> · 覆盖 <b>${p.cover}%</b>
        · 日均 <b>${p.daily}</b> 店 · <span style="color:#fca5a5">未访 <b>${p.n_never}</b></span>
        · <span style="color:#fde68a">星期错位 <b>${p.mismatch}</b></span></span></div>
    <div class="ctrl"></div>
    <div class="pair">
      <div class="colL"><div class="colhd"><span>计划安排</span><span>${p.n_store} 店</span></div><div class="map" id="L${i}"></div></div>
      <div class="colR"><div class="colhd"><span>实际走访</span><span>${p.n_visit} 次到访</span></div><div class="map" id="R${i}"></div></div>
    </div>
    <div class="lg"></div>
    ${p.n_never ? `<details><summary>列出这 ${p.n_never} 家未到访门店</summary><div class="never">${p.never.map(x=>`<div>${x.n} · ${x.ad} <span style="color:#64748b">(${x.c})</span></div>`).join('')}</div></details>` : ''}`;
  g.appendChild(row);

  const opt = {zoomControl:true, attributionControl:false};
  const mL = L.map('L'+i, opt), mR = L.map('R'+i, opt);
  [mL, mR].forEach(m => {
    let ok=false; const tl = L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {subdomains:'1234', maxZoom:18});
    tl.on('tileload', ()=>{ok=true;}); tl.addTo(m);
    setTimeout(()=>{ if(!ok){ const d=document.createElement('div'); d.className='noTile'; d.textContent='底图未加载（离线）—— 几何照常'; m.getContainer().appendChild(d);} }, 6000);
  });
  (window.__maps = window.__maps || []).push(...[mL, mR]);
  let lock = false;
  const sync = (a, b) => a.on('move zoom', () => { if (lock) return; lock = true; b.setView(a.getCenter(), a.getZoom(), {animate:false}); lock = false; });
  sync(mL, mR); sync(mR, mL);

  const bounds = [];
  const faceL = {wd: L.layerGroup(), zone: L.layerGroup()}, faceR = {wd: L.layerGroup(), zone: L.layerGroup()};
  p.hexes.forEach(h => {
    const mk = (col, target) => target.addLayer(L.polygon(h.ring, {color:col, weight:1, opacity:.8, fillColor:col, fillOpacity:.16}));
    mk(h.wp>=0 ? WDC[h.wp] : '#475569', faceL.wd); mk(ZC[h.z % ZC.length], faceL.zone);
    mk(h.wa>=0 ? WDC[h.wa] : '#475569', faceR.wd); mk(ZC[h.z % ZC.length], faceR.zone);
    h.ring.forEach(c=>bounds.push(c));
  });
  const ptsL = L.layerGroup(), ptsR = L.layerGroup(), neverL = L.layerGroup(), neverR = L.layerGroup(), offR = L.layerGroup();
  const pop = s => `<b>${s.n}</b><br>${s.ad}<br>客户码 ${s.c}<br>` +
    (s.v>0 ? `实际到访 <b>${s.v}</b> 次 · 实际主力星期 <b>${WDL[s.w]}</b>` : '<b>本月未到访</b>') +
    (s.pw>=0 ? ` · 计划星期 ${WDL[s.pw]}` : '') + `<br>片区 ${s.z+1}`;
  p.stores.forEach(s => {
    const nev = s.v === 0;
    const off = !nev && s.pw>=0 && s.mismatch;
    const style = (col, rad, fillOp) => ({radius: rad, color: nev ? '#f87171' : (off ? '#fbbf24' : '#0b0d12'),
      weight: nev ? 1.5 : (off ? 2 : .5), dashArray: nev ? '2,2' : null, fillColor: col, fillOpacity: nev ? .12 : fillOp});
    const mkL = L.circleMarker([s.la,s.lo], style(WDC[Math.max(s.pw,0)], nev?3:4.5, nev?.12:.85)).bindPopup(pop(s));
    (nev ? neverL : ptsL).addLayer(mkL);
    const mkR = L.circleMarker([s.la,s.lo], style(WDC[Math.max(s.w,0)], nev?3:2.6+Math.min(s.v,6)*1.1, nev?.12:.95)).bindPopup(pop(s));
    (nev ? neverR : (off ? offR : ptsR)).addLayer(mkR);
    bounds.push([s.la, s.lo]);
  });
  let faceMode='wd', onlyNever=false, showOff=true;
  const apply = () => {
    [faceL.wd, faceL.zone, faceR.wd, faceR.zone, ptsL, ptsR, neverL, neverR, offR].forEach(l => { mL.removeLayer(l); mR.removeLayer(l); });
    faceL[faceMode].addTo(mL); faceR[faceMode].addTo(mR);
    if (!onlyNever) { ptsL.addTo(mL); ptsR.addTo(mR); neverL.addTo(mL); neverR.addTo(mR); if (showOff) offR.addTo(mR); }
    else { neverL.addTo(mL); neverR.addTo(mR); }
    btns.forEach(b => b.className = (b.dataset.k === faceMode) ? 'on' : '');
    nb.className = onlyNever ? 'on' : ''; ob.className = showOff ? 'on' : '';
  };
  const ctrl = row.querySelector('.ctrl');
  const mkBtn = (txt, k, fn) => { const b=document.createElement('button'); b.textContent=txt; b.dataset.k=k; b.onclick=fn; ctrl.appendChild(b); return b; };
  const btns = [mkBtn('面：星期', 'wd', ()=>{faceMode='wd'; apply();}), mkBtn('面：片区', 'zone', ()=>{faceMode='zone'; apply();})];
  const nb = mkBtn('只看未访店', 'never', ()=>{onlyNever=!onlyNever; apply();});
  const ob = mkBtn('高亮星期错位', 'off', ()=>{showOff=!showOff; apply();});
  mL.fitBounds(bounds, {padding:[12,12]}); mR.fitBounds(bounds, {padding:[12,12]});
  mL.setView(mR.getCenter(), mR.getZoom(), {animate:false}); mL.invalidateSize(); mR.invalidateSize();
  apply();
  row.querySelector('.lg').innerHTML =
    WDL.map((n,k)=>`<span><i class="sw" style="background:${WDC[k]}"></i>${n}</span>`).join('') +
    `<span style="color:#64748b">|</span><span><i class="sw" style="background:transparent;border:1px dashed #f87171"></i>未到访</span>` +
    `<span><i class="sw" style="background:#fbbf24;border:2px solid #fbbf24"></i>星期错位</span>`;
});
</script></body></html>
"""


def main():
    panels = build()
    css = Path('/tmp/leaflet.css').read_text() if Path('/tmp/leaflet.css').exists() else ''
    js = Path('/tmp/leaflet.js').read_text() if Path('/tmp/leaflet.js').exists() else ''
    html = (HTML.replace('__LEAFLET_CSS__', css).replace('__LEAFLET_JS__', js)
                .replace('__DATA__', json.dumps(panels, ensure_ascii=False))
                .replace('__WDL__', json.dumps(WD_LABEL, ensure_ascii=False))
                .replace('__WDC__', json.dumps(WD_COLOR))
                .replace('__ZC__', json.dumps(ZONE_COLOR)))
    out = ROOT / "docs/reports/2026-09-22-top5-map.html"
    out.write_text(html, encoding="utf-8")
    print(f"写出 {out} ({out.stat().st_size/1024:.0f} KB, leaflet 内嵌 {'是' if js else '否'})")


if __name__ == "__main__":
    main()