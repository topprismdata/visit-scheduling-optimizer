# -*- coding: utf-8 -*-
"""逐人左右地图 — 582 人, 每人一屏「左计划 / 右实际」+ 每块明细.

老板要求(2026-09-22): 每个人的分析都要遵循左右地图的方式, 没有地图不能立刻看懂。

用法: 打开 HTML → 搜索/下拉选一个人 → 左图=计划(面按计划星期/点按计划星期),
右图=实际(面按实际主力星期/点大小=到访次数); 两侧视野联动, 逐店对位。
红虚线=本月未到访; 金色描边=计划星期未被执行到。

数据: 《更新后的8月规划》 + 8月实际走访 + output/rep_behavior/dossier.json(分型/每块明细)
输出: docs/reports/2026-09-22-rep-maps.html (离线自包含, Leaflet 内嵌)
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.top5_portrait import components  # noqa: E402

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
OUT = ROOT / "docs/reports/2026-09-22-rep-maps.html"
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def build():
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wd"] = plan["plan_day"].dt.dayofweek
    plan["lat"] = pd.to_numeric(plan["lat"], errors="coerce")
    plan["lng"] = pd.to_numeric(plan["lng"], errors="coerce")
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wd"] = act["call_date"].dt.dayofweek
    doss = {}
    dp = ROOT / "output/rep_behavior/dossier.json"
    if dp.exists():
        doss = {r["line"]: r for r in json.loads(dp.read_text(encoding="utf-8"))}
    A = {l: g for l, g in act.groupby("salesperson_code")}

    out = []
    for lid, pl in plan.groupby("sales_line_code"):
        sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
        if not len(sto):
            continue
        a = A.get(lid)
        if a is None or not len(a):
            continue
        cv = a.groupby("customer_code").size().to_dict()
        awd = a.groupby("customer_code")["wd"].apply(lambda s: int(s.value_counts().index[0])).to_dict()
        awset = a.groupby("customer_code")["wd"].apply(set).to_dict()
        pwd = pl.drop_duplicates("customer_code").set_index("customer_code")["wd"].to_dict()
        cells = {r.customer_code: h3.latlng_to_cell(float(r.lat), float(r.lng), 7) for r in sto.itertuples()}
        comp = components(list(cells.values()))
        blk_of = {c: comp[cells[c]] for c in cells}
        d = doss.get(lid, {})
        # 每块: 门店凸包 + 计划/实际主力星期 + 执行率
        blocks = []
        blk_centers = {}
        for b, g in sto.assign(blk=[blk_of[c] for c in sto["customer_code"]]).groupby("blk"):
            pts = np.array([[float(r.lat), float(r.lng)] for r in g.itertuples()])
            blk_centers[b] = (pts[:, 0].mean(), pts[:, 1].mean())
            hull = convex_hull(pts)
            bwd_plan = Counter(pl[pl["customer_code"].isin(set(g["customer_code"]))]["wd"]).most_common(1)
            plan_wd = int(bwd_plan[0][0]) if bwd_plan else -1
            sub = a[a["customer_code"].isin(set(g["customer_code"]))]
            act_wd = int(Counter(sub["wd"]).most_common(1)[0][0]) if len(sub) else -1
            done = len(set(g["customer_code"]) & set(a["customer_code"]))
            blocks.append({"pts": [[round(float(x), 5), round(float(y), 5)] for x, y in hull],
                           "wp": plan_wd, "wa": act_wd, "n": int(g["customer_code"].nunique()),
                           "done": done, "rate": round(done / max(len(g), 1), 3),
                           "c": [round(float(pts[:, 0].mean()), 4), round(float(pts[:, 1].mean()), 4)]})
        blocks.sort(key=lambda x: -x["n"])
        stores = []
        for r in sto.itertuples():
            v = int(cv.get(r.customer_code, 0))
            pw = pwd.get(r.customer_code)
            w = awd.get(r.customer_code)
            mism = bool(v > 0 and pw is not None and pw == pw and int(pw) not in awset.get(r.customer_code, set()))
            stores.append([round(float(r.lat), 5), round(float(r.lng), 5),
                           int(pw) if pw is not None and pw == pw else -1,
                           int(w) if w is not None else -1, v, 1 if mism else 0,
                           str(r.customer_name)[:26]])
        out.append({"line": lid, "city": d.get("city", ""), "kind": d.get("kind", "?"),
                    "story": d.get("story", ""), "stats": {
                        "plan_stores": int(sto["customer_code"].nunique()), "plan_rows": int(len(pl)),
                        "act_visits": int(len(a)), "blocks": len(blocks),
                        "worked": d.get("blocks_worked", 0),
                        "exec": d.get("block_exec_median", 0), "wdrate": d.get("block_wd_rate", 0),
                        "cover": d.get("cover", 0), "sameday": d.get("sameday", 0), "qty": d.get("qty", 0)},
                    "blocks": blocks, "stores": stores,
                    "bd": d.get("block_detail", [])})
    return out


def convex_hull(pts):
    """Andrew monotone chain; pts: Nx2."""
    p = sorted(set(map(tuple, pts.tolist())))
    if len(p) <= 2:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo = []
    for x in p:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], x) <= 0:
            lo.pop()
        lo.append(x)
    up = []
    for x in reversed(p):
        while len(up) >= 2 and cross(up[-2], up[-1], x) <= 0:
            up.pop()
        up.append(x)
    return lo[:-1] + up[:-1]


HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>逐人左右地图 · 2026-08</title>
<style>__CSS__</style>
<style>
 body{margin:0;background:#0f1115;color:#e6e6e6;font:13px/1.6 -apple-system,"PingFang SC",sans-serif}
 header{padding:12px 18px;border-bottom:1px solid #232733;position:sticky;top:0;background:#0f1115;z-index:9}
 h1{font-size:16px;margin:0 0 6px}
 .bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
 input,select,button{background:#1b2029;border:1px solid #2f3646;color:#e6e6e6;border-radius:6px;padding:5px 9px;font-size:12.5px}
 input{width:230px} select{max-width:430px}
 button{cursor:pointer} button:hover{border-color:#60a5fa}
 .chip{font-size:11.5px;color:#9aa4b8;padding:2px 8px;border:1px solid #2f3646;border-radius:20px}
 .wrap{padding:12px 18px 30px}
 .pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
 .map{height:470px;background:#0b0d12;border-radius:8px;overflow:hidden}
 .colhd{font-size:12px;display:flex;justify-content:space-between;color:#93a2b8;padding:2px 2px 5px}
 .colL .colhd{color:#93c5fd} .colR .colhd{color:#fca5a5}
 .story{background:#161a22;border:1px solid #232733;border-radius:10px;padding:10px 12px;margin-top:10px;font-size:12.5px;color:#cfd6e3}
 .lg{display:flex;gap:10px;flex-wrap:wrap;font-size:11.5px;color:#aab3c5;padding:6px 2px}
 table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}
 th,td{padding:3px 6px;border-bottom:1px solid #232733;text-align:right;white-space:nowrap}
 th{color:#93a2b8;background:#161a22} td:nth-child(1),th:nth-child(1),td:nth-child(2),th:nth-child(2){text-align:left}
 .bad{color:#fca5a5} .ok{color:#86efac}
 .noTile{position:absolute;z-index:400;margin:6px 8px;padding:3px 7px;font-size:11px;background:#7c2d12cc;color:#fff;border-radius:5px}
</style></head><body>
<header>
 <h1>逐人左右地图 · 2026-08（左＝计划 / 右＝实际）</h1>
 <div class="bar">
  <input id="q" placeholder="搜线号 / 城市 / 分型">
  <select id="pick"></select>
  <button id="prev">← 上一位</button><button id="next">下一位 →</button>
  <span class="chip" id="cnt"></span>
  <span class="chip">面：<a href="#" id="fm">星期</a>/<a href="#" id="fz">片区</a></span>
  <span class="chip">点：<a href="#" id="pm">实际</a>/<a href="#" id="pp">计划</a></span>
  <span class="chip"><a href="#" id="on">只看未访</a></span>
  <span class="chip"><a href="#" id="om">高亮星期错位</a></span>
 </div>
</header>
<div class="wrap">
 <div id="head" class="story"></div>
 <div class="pair">
  <div class="colL"><div class="colhd"><span>计划安排</span><span id="lstat"></span></div><div class="map" id="mL"></div></div>
  <div class="colR"><div class="colhd"><span>实际走访</span><span id="rstat"></span></div><div class="map" id="mR"></div></div>
 </div>
 <div class="lg" id="lg"></div>
 <div id="blocks"></div>
</div>
<script>__JS__</script>
<script>
const D = __DATA__, WDL = __WDL__, WDC = __WDC__, ZC = __ZC__;
const sel = document.getElementById('pick'), q = document.getElementById('q');
sel.innerHTML = D.map((d,i)=>`<option value="${i}">${d.line} · ${d.city} · ${d.kind}</option>`).join('');
let idx = +(new URLSearchParams(location.search).get('i') || 0);
let faceMode='wd', ptMode='act', onlyNever=false, showMismatch=true, mL=null, mR=null, layers=null;
function filterOptions(){
  const s = q.value.trim().toLowerCase();
  const keep = D.map((d,i)=>[d,i]).filter(([d])=>(d.line+' '+d.city+' '+d.kind).toLowerCase().includes(s));
  sel.innerHTML = keep.map(([d,i])=>`<option value="${i}">${d.line} · ${d.city} · ${d.kind}</option>`).join('');
  document.getElementById('cnt').textContent = `匹配 ${keep.length} / ${D.length} 人`;
  if (keep.length && !keep.find(([,i])=>i===idx)) sel.value = keep[0][1];
}
q.oninput = filterOptions; filterOptions();
sel.onchange = () => { idx = +sel.value; render(); };
document.getElementById('prev').onclick = () => { const o=sel.options; const k=sel.selectedIndex; if(k>0){sel.selectedIndex=k-1; idx=+sel.value; render();} };
document.getElementById('next').onclick = () => { const o=sel.options; const k=sel.selectedIndex; if(k<o.length-1){sel.selectedIndex=k+1; idx=+sel.value; render();} };
const setLink=(id,on)=>{ const e=document.getElementById(id); e.style.color = on ? '#60a5fa':'#9aa4b8'; };
document.getElementById('fm').onclick = e => { e.preventDefault(); faceMode='wd'; render(); };
document.getElementById('fz').onclick = e => { e.preventDefault(); faceMode='zone'; render(); };
document.getElementById('pm').onclick = e => { e.preventDefault(); ptMode='act'; render(); };
document.getElementById('pp').onclick = e => { e.preventDefault(); ptMode='plan'; render(); };
document.getElementById('on').onclick = e => { e.preventDefault(); onlyNever=!onlyNever; render(); };
document.getElementById('om').onclick = e => { e.preventDefault(); showMismatch=!showMismatch; render(); };
function mkMap(el, label){
  const m = L.map(el, {zoomControl:true, attributionControl:false});
  let ok=false; const tl=L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',{subdomains:'1234',maxZoom:18});
  tl.on('tileload',()=>{ok=true;}); tl.addTo(m);
  setTimeout(()=>{ if(!ok){ const d=document.createElement('div'); d.className='noTile'; d.textContent='底图未加载（离线）— 几何照常'; m.getContainer().appendChild(d);} },6000);
  return m;
}
function render(){
  const d = D[idx];
  location.hash = 'i='+idx;
  sel.value = idx;
  setLink('fm', faceMode==='wd'); setLink('fz', faceMode==='zone');
  setLink('pm', ptMode==='act'); setLink('pp', ptMode==='plan'); setLink('on', onlyNever); setLink('om', showMismatch);
  const s = d.stats;
  document.getElementById('head').innerHTML =
    `<b>${d.line} · ${d.city}</b> · <span style="color:#7dd3fc">${d.kind}</span><br>${d.story}`;
  document.getElementById('lstat').textContent = `${s.plan_stores} 店 / ${s.plan_rows} 次（${s.blocks} 块）`;
  document.getElementById('rstat').textContent = `${s.act_visits} 次到访`;
  if (mL) { mL.remove(); mR.remove(); }
  mL = mkMap('mL'); mR = mkMap('mR');
  let lock=false; const sync=(a,b)=>a.on('move zoom',()=>{ if(lock) return; lock=true; b.setView(a.getCenter(),a.getZoom(),{animate:false}); lock=false; });
  sync(mL,mR); sync(mR,mL);
  const bounds=[]; const pop = st => `<b>${st[6]}</b><br>计划星期 ${st[2]>=0?WDL[st[2]]:'—'} · 实际主力 ${st[3]>=0?WDL[st[3]]:'—'} · 到访 ${st[4]} 次`;
  d.stores.forEach((st,i) => {
    if (onlyNever && st[4] > 0) return;
    const nev = st[4] === 0, off = st[5] === 1;
    const mk = (color, rad, fill, dash, stroke, sw) => L.circleMarker([st[0], st[1]],
      {radius:rad, color:stroke, weight:sw, dashArray:dash, fillColor:color, fillOpacity:fill}).bindPopup(pop(st));
    if (ptMode==='plan' || true) {
      // 左图: 计划口径
      const colL = nev ? '#f87171' : WDC[Math.max(st[2],0)];
      // 右图: 实际口径
      const colR = nev ? '#f87171' : WDC[Math.max(st[3],0)];
      d.__mk = d.__mk || {};
    }
    // 左图
    L.circleMarker([st[0],st[1]], {radius: nev?3:4.5, color: nev?'#f87171':(off&&showMismatch?'#fbbf24':'#0b0d12'),
      weight: nev?1.5:(off&&showMismatch?2:.5), dashArray: nev?'2,2':null,
      fillColor: nev?'#f87171':WDC[Math.max(st[2],0)], fillOpacity: nev?.12:.85}).bindPopup(pop(st)).addTo(mL);
    // 右图(点大小=到访次数; 只看未访时仅未访点)
    if (!onlyNever) {
      L.circleMarker([st[0],st[1]], {radius: nev?3:2.6+Math.min(st[4],6)*1.1, color: nev?'#f87171':(off&&showMismatch?'#fbbf24':'#0b0d12'),
        weight: nev?1.5:(off&&showMismatch?2:.5), dashArray: nev?'2,2':null,
        fillColor: nev?'#f87171':WDC[Math.max(st[3],0)], fillOpacity: nev?.12:.95}).bindPopup(pop(st)).addTo(mR);
    } else if (nev) {
      L.circleMarker([st[0],st[1]], {radius:3, color:'#f87171', weight:1.5, dashArray:'2,2', fillColor:'#f87171', fillOpacity:.12}).bindPopup(pop(st)).addTo(mR).addTo(mL);
    }
    if (!onlyNever || nev) bounds.push([st[0], st[1]]);
  });
  d.blocks.forEach((b,k) => {
    const col = faceMode==='zone' ? ZC[k % ZC.length] : (ptMode==='plan' ? WDC[Math.max(b.wp,0)] : WDC[Math.max(b.wa,0)]);
    const colL = faceMode==='zone' ? ZC[k % ZC.length] : WDC[Math.max(b.wp,0)];
    const colR = faceMode==='zone' ? ZC[k % ZC.length] : WDC[Math.max(b.wa,0)];
    L.polygon(b.pts, {color:colL, weight:1.2, opacity:.9, fillColor:colL, fillOpacity:.14}).addTo(mL);
    L.polygon(b.pts, {color:colR, weight:1.2, opacity:.9, fillColor:colR, fillOpacity:.14}).addTo(mR);
    b.pts.forEach(p=>bounds.push(p));
  });
  const c = bounds.length ? L.latLngBounds(bounds) : null;
  [mL,mR].forEach(m => { if (c) m.fitBounds(c, {padding:[14,14]}); });
  if (mL && mR) mL.setView(mR.getCenter(), mR.getZoom(), {animate:false});
  document.getElementById('lg').innerHTML =
    WDL.map((n,k)=>`<span><i style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${WDC[k]};margin-right:4px;vertical-align:-1px"></i>${n}</span>`).join('') +
    `<span style="color:#64748b">|</span><span><i style="display:inline-block;width:10px;height:10px;border:1px dashed #f87171;border-radius:50%;margin-right:4px;vertical-align:-1px"></i>未到访</span>` +
    `<span><i style="display:inline-block;width:10px;height:10px;border:2px solid #fbbf24;border-radius:50%;margin-right:4px;vertical-align:-1px"></i>星期错位</span>` +
    `<span style="color:#64748b">| 面按${faceMode==='zone'?'片区':'星期'}、点按${ptMode==='plan'?'计划':'实际'}星期；块轮廓=该块门店凸包</span>`;
  const bd = d.bd || [];
  document.getElementById('blocks').innerHTML = bd.length ? `<table><thead><tr><th>块</th><th>中心</th><th>计划店</th><th>跑到</th><th>执行率</th><th>计划星期</th><th>实际主力</th></tr></thead><tbody>` +
    bd.map(b=>`<tr><td>${b['块']}</td><td style="color:#64748b">${b['中心']}</td><td>${b['计划店']}</td><td>${b['跑到的计划店']}</td>
      <td class="${b['执行率']>=0.85?'ok':'bad'}">${(b['执行率']*100).toFixed(0)}%</td><td>${b['计划星期']}</td>
      <td>${b['实际主力星期']}${(b['计划星期']&&b['实际主力星期']&&b['计划星期']!==b['实际主力星期']&&b['实际主力星期']!=='未开工')?' ⚠':''}</td></tr>`).join('') + `</tbody></table>` : '';
}
const iv = +(location.hash.replace('#i=','') || location.search.match(/[?&]i=(\\d+)/)?.[1] || NaN);
if (!isNaN(iv) && iv < D.length) idx = iv;
render();
</script></body></html>
"""


def main():
    recs = build()
    css = Path('/tmp/leaflet.css').read_text() if Path('/tmp/leaflet.css').exists() else ''
    js = Path('/tmp/leaflet.js').read_text() if Path('/tmp/leaflet.js').exists() else ''
    html = (HTML.replace('__CSS__', css).replace('__JS__', js)
                .replace('__DATA__', json.dumps(recs, ensure_ascii=False, separators=(',', ':')))
                .replace('__WDL__', json.dumps(WD, ensure_ascii=False))
                .replace('__WDC__', json.dumps(["#e6194b", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#7f7f7f"]))
                .replace('__ZC__', json.dumps(["#2563eb", "#dc2626", "#16a34a", "#ca8a04", "#9333ea", "#0891b2", "#be185d", "#4d7c0f"])))
    OUT.write_text(html, encoding="utf-8")
    print(f"写出 {OUT} ({OUT.stat().st_size/1024/1024:.1f} MB) | 线 {len(recs)} | 门店点 {sum(len(r['stores']) for r in recs)}")
    print(f"块总数 {sum(len(r['blocks']) for r in recs)}")


if __name__ == "__main__":
    main()