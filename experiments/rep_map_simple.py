# -*- coding: utf-8 -*-
"""最简版：左计划地块 / 右实际地块（都用 H3 六边形）.

只做一件事: 一眼看出"哪块地计划了但没去"。
- 两边同一套颜色(按周几); 计划有、实际没去的格子 → 两边都画灰底红框
- 地图上无文字; 只有两个大字 计划 / 实际; 顶部三个数: 计划N格 / 实际M格 / 没去K格
- 只有一个下拉选人(可搜索) + 上一位/下一位
数据: 更新后的8月规划 + 8月实际走访
输出: docs/reports/2026-09-22-rep-map-simple.html
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import h3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
OUT = ROOT / "docs/reports/2026-09-22-rep-map-simple.html"


def main():
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["lat"] = pd.to_numeric(plan["lat"], errors="coerce")
    plan["lng"] = pd.to_numeric(plan["lng"], errors="coerce")
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wd"] = act["call_date"].dt.dayofweek
    A = {l: g for l, g in act.groupby("salesperson_code")}
    attrib = {}
    ap = ROOT / "docs/reports/2026-09-22-attribution.csv"
    if ap.exists():
        ad = pd.read_csv(ap)
        attrib = {str(r["line"]): (r["verdict"], r["习惯规律性"], r["计划周几不同占比"]) for _, r in ad.iterrows()}
    dossier = {}
    dp = ROOT / "output/rep_behavior/dossier.json"
    if dp.exists():
        dossier = {r["line"]: r for r in json.loads(dp.read_text(encoding="utf-8"))}

    recs = []
    for lid, pl in plan.groupby("sales_line_code"):
        al = A.get(lid)
        sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
        if not len(sto) or al is None or not len(al):
            continue
        # 计划格: 每格用"服务日"(缺则计划日)作颜色
        pcell = {}
        for r in sto.itertuples():
            c = h3.latlng_to_cell(float(r.lat), float(r.lng), 7)
            sd = getattr(r, "服务日")
            wd = int(sd) - 1 if sd == sd and int(sd) > 0 else pd.Timestamp(r.plan_day).dayofweek
            pcell.setdefault(c, Counter())[wd] += 1
        plan_cells = [[c, v.most_common(1)[0][0]] for c, v in pcell.items()]
        # 实际格: 只统计"计划内门店"的实际到访(计划外不管)
        a2 = al[al["customer_code"].isin(set(sto["customer_code"]))]
        acell = {}
        for r in a2.itertuples():
            row = sto[sto["customer_code"] == r.customer_code]
            if not len(row):
                continue
            c = h3.latlng_to_cell(float(row["lat"].iloc[0]), float(row["lng"].iloc[0]), 7)
            acell.setdefault(c, Counter())[int(r.wd)] += 1
        act_cells = [[c, v.most_common(1)[0][0]] for c, v in acell.items()]
        bd = [{"b": b.get("块"), "n": b.get("计划店"), "p": b.get("服务日"), "a": b.get("实际主力")}
              for b in dossier.get(lid, {}).get("block_detail", [])]
        # 形状重合度 + 周几一致（无跑到/没跑到概念）
        Pset = set(c for c, _ in plan_cells); Aset = set(c for c, _ in act_cells)
        inter = Pset & Aset
        shape = len(inter) / max(len(Pset | Aset), 1)   # 对称重合(Jaccard)
        wdm = (sum(1 for c, w in plan_cells if c in inter and any(a[0] == c and a[1] == w for a in act_cells))
               / max(len(inter), 1)) if inter else 0.0
        kind3 = "①基本一样" if (shape >= 0.8 and wdm >= 0.7) else ("②区块基本一样·星期几不一样" if shape >= 0.8 else "③都不一样")
        vd, hb, mm = attrib.get(str(lid), ("", 0, 0))
        recs.append({"line": lid, "city": dossier.get(lid, {}).get("city", ""), "bd": bd,
                     "verdict": vd, "habit": hb, "mism": mm,
                     "shape": round(shape, 3), "wdm": round(wdm, 3), "kind3": kind3,
                     "plan": plan_cells, "act": act_cells,
                     "np": len(plan_cells), "na": len(act_cells)})
    print(f"线 {len(recs)} | 计划格合计 {sum(r['np'] for r in recs)} | 实际格合计 {sum(r['na'] for r in recs)}")

    css = Path('/tmp/leaflet.css').read_text() if Path('/tmp/leaflet.css').exists() else ''
    ljs = Path('/tmp/leaflet.js').read_text() if Path('/tmp/leaflet.js').exists() else ''
    h3js = Path('/tmp/h3js.js').read_text() if Path('/tmp/h3js.js').exists() else ''
    html = TEMPLATE.replace("__CSS__", css).replace("__LEAFLET__", ljs).replace("__H3__", h3js) \
                   .replace("__DATA__", json.dumps(recs, ensure_ascii=False, separators=(",", ":"))) \
                   .replace("__WDL__", json.dumps(["周一", "周二", "周三", "周四", "周五", "周六", "周日"], ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"写出 {OUT} ({OUT.stat().st_size/1024/1024:.1f} MB)")


TEMPLATE = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>计划 vs 实际（H3 地块）</title><style>__CSS__</style><style>
body{margin:0;background:#0f1115;color:#e6e6e6;font:14px/1.6 -apple-system,"PingFang SC",sans-serif}
header{padding:10px 16px;border-bottom:1px solid #232733;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
input,select,button{background:#1b2029;border:1px solid #2f3646;color:#e6e6e6;border-radius:6px;padding:5px 9px;font-size:13px}
input{width:220px} select{max-width:380px} button{cursor:pointer}
.big{font-size:15px;font-weight:600} .num{color:#9aa4b8} .num b{color:#fff} .miss{color:#fca5a5}
.legend{display:flex;gap:8px;align-items:center;font-size:12px;color:#aab3c5}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:8px 12px 14px}
.side{position:relative}
.tag{text-align:center;font-size:20px;font-weight:700;letter-spacing:4px;padding:6px 0}
.tag.l{color:#93c5fd} .tag.r{color:#fca5a5}
.map{height:calc(100vh - 150px);min-height:420px;background:#0b0d12;border-radius:8px;overflow:hidden}
</style></head><body>
<header>
  <input id="q" placeholder="搜线号/城市">
  <select id="kindf">
    <option value="">分类：全部</option>
    <option value="①基本一样">①基本一样</option>
    <option value="②区块基本一样·星期几不一样">②区块一样·星期几不一样</option>
    <option value="③都不一样">③都不一样</option>
  </select>
  <select id="verdictf">
    <option value="">归因：全部</option>
    <option value="执行到位">执行到位（计划与实际一致）</option>
    <option value="计划不够好">计划不够好（他有规律，计划写错天）</option>
    <option value="执行有问题">执行有问题（他自己没规律）</option>
  </select>
  <select id="pick"></select>
  <button id="prev">上一位</button><button id="next">下一位</button>
  <span class="num" id="count"></span>
  <span class="num" id="stat"></span>
  <span class="legend">__LEGEND__</span>
</header>
<div class="pair">
  <div class="side"><div class="tag l">计 划</div><div class="map" id="mL"></div></div>
  <div class="side"><div class="tag r">实 际</div><div class="map" id="mR"></div></div>
</div>
<div id="tbl" style="padding:0 12px 20px"></div>
<script>__LEAFLET__</script><script>__H3__</script>
<script>
const D = __DATA__, WDL = __WDL__;
const C = ['#e6194b','#1f77b4','#2ca02c','#ff7f0e','#9467bd','#8c564b','#64748b'];
const MISS_FILL = '#334155', MISS_EDGE = '#ef4444';
const sel=document.getElementById('pick'), q=document.getElementById('q');
const kindf=document.getElementById('kindf'), verdictf=document.getElementById('verdictf');
let i0 = +(new URLSearchParams(location.search).get('i')||0);   // 必须先于 fill() 调用
function fill(){
  const s=q.value.trim().toLowerCase();
  const keep=D.map((d,i)=>[d,i]).filter(([d])=>{
    if (s && !(d.line+' '+d.city).toLowerCase().includes(s)) return false;
    if (kindf.value && d.kind3!==kindf.value) return false;
    if (verdictf.value && !(d.verdict||'').startsWith(verdictf.value)) return false;
    return true;
  });
  sel.innerHTML=keep.map(([d,i])=>`<option value="${i}">${d.line} · ${d.city} · ${d.kind3}${d.verdict?' · '+d.verdict.split('（')[0]:''}</option>`).join('');
  document.getElementById('count').textContent = `匹配 ${keep.length} / ${D.length} 条`;
  if(keep.length && !keep.find(([,i])=>i===+sel.value)) sel.value=keep[0][1];
  if(keep.length) { i0=+sel.value; draw(); }
}
sel.onchange=()=>{i0=+sel.value; draw();};
document.getElementById('prev').onclick=()=>{if(sel.selectedIndex>0){sel.selectedIndex--; i0=+sel.value; draw();}};
document.getElementById('next').onclick=()=>{if(sel.selectedIndex<sel.options.length-1){sel.selectedIndex++; i0=+sel.value; draw();}};
let mL=null,mR=null;
function draw(){
  const d=D[i0];
  document.getElementById('stat').innerHTML =
    `<b>${d.line}</b> · ${d.city}　<span style="color:#7dd3fc">${d.kind3}</span>　` +
    (d.verdict ? `<span style="color:${d.verdict.startsWith('计划不够好')?'#fbbf24':(d.verdict.startsWith('执行有问题')?'#fca5a5':'#86efac')}">归因：${d.verdict}</span>` +
      `　他的规律性 <b>${(d.habit*100).toFixed(0)}%</b>　计划周几不同 <b>${(d.mism*100).toFixed(0)}%</b>` : '');
  if(mL){mL.remove(); mR.remove();}
  mL=L.map('mL',{zoomControl:true,attributionControl:false,zoomSnap:.5});
  mR=L.map('mR',{zoomControl:false,attributionControl:false,zoomSnap:.5});
  const tile = m => L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',{subdomains:'1234',maxZoom:18}).addTo(m);
  tile(mL); tile(mR);
  const b=[];
  d.plan.forEach(([cid,wd])=>{                       // 左: 计划周几
    const r=h3.cellToBoundary(cid).map(p=>[p[0],p[1]]);
    L.polygon(r,{color:'#0b0d12',weight:.6,fillColor:C[wd]||C[6],fillOpacity:.8}).addTo(mL);
    r.forEach(x=>b.push(x));
  });
  d.act.forEach(([cid,wd])=>{                        // 右: 实际周几
    const r=h3.cellToBoundary(cid).map(p=>[p[0],p[1]]);
    L.polygon(r,{color:'#0b0d12',weight:.6,fillColor:C[wd]||C[6],fillOpacity:.8}).addTo(mR);
    r.forEach(x=>b.push(x));
  });
  const bb=L.latLngBounds(b);
  mL.fitBounds(bb,{padding:[10,10]}); mR.fitBounds(bb,{padding:[10,10]});
  mL.setView(mR.getCenter(),mR.getZoom(),{animate:false});
  let lock=false;
  mL.on('move zoom',()=>{if(lock)return; lock=true; mR.setView(mL.getCenter(),mL.getZoom(),{animate:false}); lock=false;});
  mR.on('move zoom',()=>{if(lock)return; lock=true; mL.setView(mR.getCenter(),mR.getZoom(),{animate:false}); lock=false;});
  const same = k => WDL.indexOf(k[0]) === WDL.indexOf(k[1]);
  document.getElementById('tbl').innerHTML = (d.bd && d.bd.length) ?
    `<table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead><tr><th style="text-align:left;padding:4px 6px;color:#93a2b8">块</th>
      <th style="padding:4px 6px;color:#93a2b8">店数</th>
      <th style="padding:4px 6px;color:#93c5fd">计划周几</th>
      <th style="padding:4px 6px;color:#fca5a5">实际周几</th></tr></thead><tbody>` +
    d.bd.map(b=>`<tr>
      <td style="padding:3px 6px;border-top:1px solid #232733">${b.b}</td>
      <td style="padding:3px 6px;border-top:1px solid #232733;text-align:center">${b.n}</td>
      <td style="padding:3px 6px;border-top:1px solid #232733;text-align:center;color:#93c5fd">${b.p||''}</td>
      <td style="padding:3px 6px;border-top:1px solid #232733;text-align:center;color:${(b.a&&b.p&&b.a!==b.p)?'#fbbf24':'#a3e635'}">${b.a||''}</td></tr>`).join('') +
    `</tbody></table>` : '';
}
q.oninput=fill; kindf.onchange=fill; verdictf.onchange=fill;
fill();          // 首次筛选 + 绘制
</script></body></html>
"""


def legend_html():
    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    cols = ["#e6194b", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#64748b"]
    s = "".join(f'<span><i style="display:inline-block;width:10px;height:10px;background:{c};border-radius:2px;margin-right:4px"></i>{n}</span>'
                for n, c in zip(names, cols))
    return s


TEMPLATE = TEMPLATE.replace("__LEGEND__", legend_html())

if __name__ == "__main__":
    main()