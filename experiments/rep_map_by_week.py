# -*- coding: utf-8 -*-
"""计划 vs 实际（H3 地块）· 可按周切换.

每人：左=计划地块 / 右=实际地块（H3 res7 六边形，按周几着色）
可切换范围：全部 / 第1周 / 第2周 / 第3周 / 第4周（有数据的第5周也列）
每个范围各自给出：分类(①/②/③) · 归因(计划不够好/执行有问题) · 紧凑度(计划 vs 实际)
筛选项：分类 × 归因 × 紧凑度（可叠加）+ 搜索
输出: docs/reports/2026-09-22-rep-map-simple.html
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
OUT = ROOT / "docs/reports/2026-09-22-rep-map-simple.html"


import re

ADMIN_RE = re.compile(r"^([\u4e00-\u9fa5]{2,8}(?:省|自治区|市|区|县|镇|乡|街道|社区))")
BAD = set("路巷弄号栋幢室楼")


def corridor_of(addr):
    """从地址抽"物理道路走廊"名(沿街走廊)。过度剥离已修: 含 路/巷/弄/号 的段不再当行政区剥掉。"""
    a = re.sub(r"[（(][^）)]*[）)]", "", str(addr))
    for _ in range(8):
        m = ADMIN_RE.match(a)
        if not m:
            break
        tok = m.group(1)
        if any(ch in tok for ch in BAD):     # 不是纯行政区(带路/号) → 停
            break
        a = a[m.end():]
    m = re.match(r"([\u4e00-\u9fa5A-Za-z0-9]{2,12}?(?:大道|大街|公路|路|街|道|巷|弄))", a)
    if m:
        return m.group(1)
    m2 = re.match(r"([\u4e00-\u9fa5]{2,8}?(?:花园|广场|大厦|城|苑|小区|市场|商贸))", a)
    return m2.group(1) if m2 else ""


def wk(d):
    return (d.day - 1) // 7 + 1


def compactness(cells):
    """紧凑度 = 等效半径 / 平均半径 (1.5=完美圆, 越大越集中)"""
    if not cells:
        return 0.0, 0.0
    pts = np.array([h3.cell_to_latlng(c) for c in cells])
    if len(pts) < 2:
        return 0.0, 0.0
    lat0, lng0 = pts[:, 0].mean(), pts[:, 1].mean()
    d = np.sqrt(((pts[:, 0] - lat0) * 111.0) ** 2 + ((pts[:, 1] - lng0) * 111.0 * math.cos(math.radians(lat0))) ** 2)
    area = sum(h3.cell_area(c, unit="km^2") for c in cells)
    return (math.sqrt(area / math.pi) / float(d.mean()) if d.mean() > 0 else 0.0), float(d.mean())


def scope_metrics(pcell, acell, store_plan_wd, store_act_wd):
    """pcell/acell: {cell: Counter(周几→次数)}; 返回该范围的对比指标。"""
    P = {c: v.most_common(1)[0][0] for c, v in pcell.items()}
    A = {c: v.most_common(1)[0][0] for c, v in acell.items()}
    inter = set(P) & set(A)
    shape = len(inter) / max(len(set(P) | set(A)), 1)
    wdm = (sum(1 for c in inter if P[c] == A[c]) / len(inter)) if inter else 0.0
    cp, rp = compactness(set(P))
    ca, ra = compactness(set(A))
    kind3 = "①基本一样" if (shape >= 0.8 and wdm >= 0.7) else ("②区块基本一样·星期几不一样" if shape >= 0.8 else "③都不一样")
    # 门店级规律性 & 计划周几不同
    tot = len(store_act_wd)
    habit = float(np.mean([v[1] / v[2] for v in store_act_wd.values()])) if tot else 0.0
    mism = (sum(1 for s, v in store_act_wd.items() if s in store_plan_wd and v[0] != store_plan_wd[s]) / tot) if tot else 0.0
    plan_bad = bool(habit >= 0.60 and mism >= 0.25)
    exe_bad = bool(habit < 0.60 and tot > 0)
    verdict = ("两者都有" if plan_bad and exe_bad else
               "计划不够好（他有规律，计划写错天）" if plan_bad else
               "执行有问题（他自己没规律）" if exe_bad else
               "执行到位（计划与实际一致）" if (mism < 0.25 and habit >= 0.60) else "待定")
    cpflag = "相当" if abs(ca - cp) < 0.01 else ("实际更紧凑" if ca > cp else "计划更紧凑")
    return {"plan": [[c, P[c]] for c in P], "act": [[c, A[c]] for c in A],
            "np": len(P), "na": len(A), "shape": round(shape, 3), "wdm": round(wdm, 3),
            "kind3": kind3, "habit": round(habit, 3), "mism": round(mism, 3),
            "cp": round(cp, 2), "ca": round(ca, 2), "rp": round(rp, 2), "ra": round(ra, 2),
            "cpflag": cpflag, "verdict": verdict,
            "wdp": [sum(1 for _, w in P.values() and P.items() if w == k) for k in range(7)],
            "wda": [sum(1 for _, w in A.items() if w == k) for k in range(7)]}


def main():
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wk"] = plan["plan_day"].apply(wk)
    plan["lat"] = pd.to_numeric(plan["lat"], errors="coerce")
    plan["lng"] = pd.to_numeric(plan["lng"], errors="coerce")
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code", "start_time",
                               "longitude", "latitude"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wk"] = act["call_date"].apply(wk)
    act["wd"] = act["call_date"].dt.dayofweek
    act["start_time"] = pd.to_datetime(act["start_time"], errors="coerce")
    act["lat_a"] = pd.to_numeric(act["latitude"], errors="coerce")
    act["lng_a"] = pd.to_numeric(act["longitude"], errors="coerce")
    A = {l: g for l, g in act.groupby("salesperson_code")}
    doss = {}
    dp = ROOT / "output/rep_behavior/dossier.json"
    if dp.exists():
        doss = {r["line"]: r for r in json.loads(dp.read_text(encoding="utf-8"))}

    recs = []
    for lid, pl in plan.groupby("sales_line_code"):
        al = A.get(lid)
        sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
        if not len(sto) or al is None or not len(al):
            continue
        svc = {}
        for r in sto.itertuples():
            sd = getattr(r, "服务日")
            svc[r.customer_code] = int(sd) - 1 if sd == sd and int(sd) > 0 else pd.Timestamp(r.plan_day).dayofweek
        pos = {r.customer_code: (float(r.lat), float(r.lng)) for r in sto.itertuples()}
        xy = []
        idx_of = {}
        for r in sto.itertuples():
            idx_of[r.customer_code] = len(xy)
            xy.append([round(float(r.lat), 5), round(float(r.lng), 5)])
        corr_of = {}
        for r in sto.itertuples():
            corr_of[r.customer_code] = corridor_of(getattr(r, "customer_address", ""))
        act_in = al[al["customer_code"].isin(set(pos))]
        scopes = {}
        for w in ["all", 1, 2, 3, 4, 5]:
            pw = pl if w == "all" else pl[pl["wk"] == w]
            aw = act_in if w == "all" else act_in[act_in["wk"] == w]
            if w != "all" and (len(pw) == 0 or len(aw) == 0):
                continue
            pcell, acell = {}, {}
            store_plan_wd, store_act_wd = {}, {}
            for r in pw.itertuples():
                c = h3.latlng_to_cell(*pos[r.customer_code], 7)
                pcell.setdefault(c, Counter())[svc[r.customer_code]] += 1
                store_plan_wd[r.customer_code] = svc[r.customer_code]
            for c, g in aw.groupby("customer_code"):
                cell = h3.latlng_to_cell(*pos[c], 7)
                vc = Counter(g["wd"])
                acell.setdefault(cell, Counter()).update(vc)
                modal, cnt = vc.most_common(1)[0]
                store_act_wd[c] = (int(modal), cnt, len(g))   # (主力周几, 该周几次数, 总次数)
            m = scope_metrics(pcell, acell, store_plan_wd, store_act_wd)
            pc_corr, ac_corr = {}, {}
            pc_s, ac_s = {}, {}
            for r in pw.itertuples():
                k = corr_of.get(r.customer_code, "")
                if k:
                    pc_corr[k] = pc_corr.get(k, 0) + 1
                    pc_s.setdefault(k, []).append(idx_of.get(r.customer_code, -1))
            for c in aw["customer_code"].unique():
                k = corr_of.get(c, "")
                if k:
                    ac_corr[k] = ac_corr.get(k, 0) + 1
                    ac_s.setdefault(k, []).append(idx_of.get(c, -1))
            common = set(pc_corr) & set(ac_corr)
            # ---- 每天一条连续线: 左=计划(NN序) 右=实际(打卡时间序) ----
            def nn_order(pts):
                pts = list(pts)
                if len(pts) < 2:
                    return pts
                out = [pts.pop(0)]
                while pts:
                    last = out[-1]
                    j = min(range(len(pts)), key=lambda i: (pts[i][0]-last[0])**2 + (pts[i][1]-last[1])**2)
                    out.append(pts.pop(j))
                return out
            daysP, daysA = [], []
            if len(pw):
                for d, g in pw.groupby(pw["plan_day"]):
                    pts = [(float(r.lat), float(r.lng)) for r in g.itertuples() if r.lat == r.lat]
                    if len(pts) >= 2:
                        daysP.append([int(pd.Timestamp(d).dayofweek), [[round(a,5), round(b,5)] for a, b in nn_order(pts)]])
            if len(aw):
                for d, g in aw.groupby(aw["call_date"]):
                    g2 = g.dropna(subset=["lat_a", "lng_a"])
                    pts = [(float(r.lat_a), float(r.lng_a)) for r in g2.itertuples()]
                    if len(pts) >= 2:
                        daysA.append([int(pd.Timestamp(d).dayofweek), [[round(a,5), round(b,5)] for a, b in nn_order(pts)]])
            m["daysP"], m["daysA"] = daysP, daysA
            m["geom_p"] = [[k, [i for i in pc_s.get(k, []) if i >= 0]] for k, _ in sorted(pc_corr.items(), key=lambda kv: -kv[1])]
            m["geom_a"] = [[k, [i for i in ac_s.get(k, []) if i >= 0]] for k, _ in sorted(ac_corr.items(), key=lambda kv: -kv[1])]
            m["corridors_plan"] = sorted(pc_corr.items(), key=lambda kv: -kv[1])[:40]
            m["corridors_act"] = sorted(ac_corr.items(), key=lambda kv: -kv[1])[:40]
            m["n_corr_plan"], m["n_corr_act"] = len(pc_corr), len(ac_corr)
            m["corr_match"] = round(len(common) / max(len(pc_corr), 1), 3)
            m["corr_missing"] = [k for k, _ in sorted(pc_corr.items(), key=lambda kv: -kv[1]) if k not in common][:12]
            pd_cnt = pw.groupby(pw["plan_day"].dt.day).size().to_dict()
            ad_cnt = aw.groupby(aw["call_date"].dt.day).size().to_dict()
            days = sorted(set(pd_cnt) | set(ad_cnt))
            m["days"] = days
            m["dcnt_p"] = [int(pd_cnt.get(d, 0)) for d in days]
            m["dcnt_a"] = [int(ad_cnt.get(d, 0)) for d in days]
            scopes[str(w)] = m
        if "all" not in scopes:
            continue
        recs.append({"line": lid, "city": doss.get(lid, {}).get("city", ""), "xy": xy, "scopes": scopes})
    print(f"线 {len(recs)} | 每线周数据: {sorted(set(k for r in recs for k in r['scopes']))}")

    css = Path('/tmp/leaflet.css').read_text() if Path('/tmp/leaflet.css').exists() else ''
    ljs = Path('/tmp/leaflet.js').read_text() if Path('/tmp/leaflet.js').exists() else ''
    h3js = Path('/tmp/h3js.js').read_text() if Path('/tmp/h3js.js').exists() else ''
    html = (TEMPLATE.replace("__CSS__", css).replace("__LEAFLET__", ljs).replace("__H3__", h3js)
            .replace("__DATA__", json.dumps(recs, ensure_ascii=False, separators=(",", ":")))
            .replace("__WDL__", json.dumps(["周一", "周二", "周三", "周四", "周五", "周六", "周日"], ensure_ascii=False))
            .replace("__LEGEND__", legend_html()))
    OUT.write_text(html, encoding="utf-8")
    print(f"写出 {OUT} ({OUT.stat().st_size/1024/1024:.1f} MB)")
    allsc = [r["scopes"]["all"] for r in recs]
    print(f"全月: 实际更紧凑 {sum(1 for s in allsc if s['cpflag']=='实际更紧凑')} | 计划更紧凑 {sum(1 for s in allsc if s['cpflag']=='计划更紧凑')} | 相当 {sum(1 for s in allsc if s['cpflag']=='相当')}")
    print(f"全月: ① {sum(1 for s in allsc if s['kind3'].startswith('①'))} | ② {sum(1 for s in allsc if s['kind3'].startswith('②'))} | ③ {sum(1 for s in allsc if s['kind3'].startswith('③'))}")
    print(f"道路走廊一致度 中位 {np.median([s['corr_match'] for s in allsc])*100:.0f}%")
    print(f"全月: 计划不够好 {sum(1 for s in allsc if s['verdict'].startswith('计划不够好'))} | 执行有问题 {sum(1 for s in allsc if s['verdict'].startswith('执行有问题'))}")


def legend_html():
    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    cols = ["#e6194b", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#64748b"]
    return "".join(f'<span><i style="display:inline-block;width:10px;height:10px;background:{c};border-radius:2px;margin-right:4px"></i>{n}</span>'
                   for n, c in zip(names, cols))


TEMPLATE = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>计划 vs 实际（H3 地块）· 按周</title><style>__CSS__</style><style>
body{margin:0;background:#0f1115;color:#e6e6e6;font:14px/1.6 -apple-system,"PingFang SC",sans-serif}
header{padding:10px 16px;border-bottom:1px solid #232733;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
input,select,button{background:#1b2029;border:1px solid #2f3646;color:#e6e6e6;border-radius:6px;padding:5px 9px;font-size:13px}
input{width:200px} select{max-width:330px} button{cursor:pointer}
.num{color:#9aa4b8;font-size:13px}
.legend{display:flex;gap:8px;align-items:center;font-size:12px;color:#aab3c5}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:8px 12px 0}
.tag{text-align:center;font-size:20px;font-weight:700;letter-spacing:4px;padding:6px 0}
.tag.l{color:#93c5fd} .tag.r{color:#fca5a5}
.map{height:calc(100vh - 210px);min-height:400px;background:#0b0d12;border-radius:8px;overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
th,td{padding:3px 6px;border-bottom:1px solid #232733;text-align:center;white-space:nowrap}
th{color:#93a2b8}
</style></head><body>
<header>
  <input id="q" placeholder="搜线号/城市">
  <select id="modef"><option value="map">地块模式</option><option value="corridor">走廊模式</option></select>
  <select id="weekf"><option value="all">范围：全月</option><option value="1">第1周</option><option value="2">第2周</option><option value="3">第3周</option><option value="4">第4周</option><option value="5">第5周</option></select>
  <select id="kindf"><option value="">分类：全部</option><option value="①基本一样">①基本一样</option><option value="②区块基本一样·星期几不一样">②区块一样·星期几不一样</option><option value="③都不一样">③都不一样</option></select>
  <select id="verdictf"><option value="">归因：全部</option><option value="执行到位">执行到位</option><option value="计划不够好">计划不够好</option><option value="执行有问题">执行有问题</option></select>
  <select id="cpf"><option value="">紧凑度：全部</option><option value="实际更紧凑">实际更紧凑</option><option value="计划更紧凑">计划更紧凑</option><option value="相当">相当</option></select>
  <select id="pick"></select>
  <button id="prev">上一位</button><button id="next">下一位</button>
  <span class="num" id="count"></span>
  <span class="legend">__LEGEND__</span>
</header>
<div class="num" id="stat" style="padding:6px 16px 0"></div>
<div class="num" style="padding:2px 16px 0;color:#8b93a7;font-size:12px">提示：单周对比受"月度轮访"影响——计划安排在某周的店，业代可能实际在别的周去；判断"计划 vs 实际"以<b>全月</b>为准，单周用来看节奏。</div>
<div class="pair" id="mapPair">
  <div><div class="tag l">计 划</div><div class="map" id="mL"></div></div>
  <div><div class="tag r">实 际</div><div class="map" id="mR"></div></div>
</div>
<div class="pair" id="corrPair" style="display:none">
  <div><div class="tag l">计 划 每日店数</div><div id="cL"></div></div>
  <div><div class="tag r">实 际 每日店数</div><div id="cR"></div></div>
</div>
<div id="tbl" style="padding:0 12px 20px"></div>
<script>__LEAFLET__</script><script>__H3__</script>
<script>
const D = __DATA__, WDL = __WDL__;
const C = ['#e6194b','#1f77b4','#2ca02c','#ff7f0e','#9467bd','#8c564b','#64748b'];
const modef=document.getElementById('modef'), q=document.getElementById('q'), weekf=document.getElementById('weekf'), kindf=document.getElementById('kindf'),
      verdictf=document.getElementById('verdictf'), cpf=document.getElementById('cpf'), sel=document.getElementById('pick');
let i0 = +(new URLSearchParams(location.search).get('i')||0);
function cur(d){ return d.scopes[weekf.value] || d.scopes['all']; }
function fill(){
  const s=q.value.trim().toLowerCase();
  const keep=D.map((d,i)=>[d,i]).filter(([d])=>{
    if(s && !(d.line+' '+d.city).toLowerCase().includes(s)) return false;
    const m=cur(d); if(!m) return false;
    if(kindf.value && m.kind3!==kindf.value) return false;
    if(verdictf.value && !(m.verdict||'').startsWith(verdictf.value)) return false;
    if(cpf.value && m.cpflag!==cpf.value) return false;
    return true;
  });
  sel.innerHTML=keep.map(([d,i])=>{const m=cur(d);return `<option value="${i}">${d.line} · ${d.city} · ${m.kind3.split('·')[0]} · ${(m.verdict||'').split('（')[0]} · ${m.cpflag}</option>`;}).join('');
  document.getElementById('count').textContent=`匹配 ${keep.length} / ${D.length} 条`;
  if(keep.length && !keep.find(([,i])=>i===+sel.value)) sel.value=keep[0][1];
  if(keep.length){ i0=+sel.value; draw(); }
}
let mL=null,mR=null;
function draw(){
  const d=D[i0], m=cur(d), w=weekf.value;
  const wn = w==='all' ? '全月' : ('第'+w+'周');
  document.getElementById('stat').innerHTML =
    `<b>${d.line}</b> · ${d.city} · <b>${wn}</b>　<span style="color:#7dd3fc">${m.kind3}</span>　` +
    `<span style="color:${m.verdict.startsWith('计划不够好')?'#fbbf24':(m.verdict.startsWith('执行有问题')?'#fca5a5':'#86efac')}">${m.verdict}</span>` +
    `　规律性 <b>${(m.habit*100).toFixed(0)}%</b>　计划周几不同 <b>${(m.mism*100).toFixed(0)}%</b>` +
    `　｜计划 <b>${m.np}</b> 格（${m.rp}km）　实际 <b>${m.na}</b> 格（${m.ra}km）　紧凑度 计划 <b>${m.cp}</b> / 实际 <b>${m.ca}</b>` +
    `　<span style="color:${Math.abs(m.ca-m.cp)<0.01?'#94a3b8':(m.ca>m.cp?'#86efac':'#fca5a5')}">${m.cpflag}</span>`;
  const corrMode = (modef.value==='corridor');
  document.getElementById('mapPair').style.display = 'grid';     // 两种模式都用地图
  document.getElementById('corrPair').style.display = 'none';    // 不再用文字清单
  if (corrMode) {
    document.getElementById('stat').innerHTML +=
      `　｜<b>走廊线</b>：计划 <b>${(m.daysP||[]).length}</b> 天、实际 <b>${(m.daysA||[]).length}</b> 天` +
      `　<span style="color:#8b93a7">左=计划线、右=实际线（都按"当天门店最近邻串联"），颜色=周几</span>`;
    renderCorridor(d, m); return;
  }
  if(mL){mL.remove(); mR.remove();}
  mL=L.map('mL',{zoomControl:true,attributionControl:false});
  mR=L.map('mR',{zoomControl:false,attributionControl:false});
  const tile=x=>L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',{subdomains:'1234',maxZoom:18}).addTo(x);
  tile(mL); tile(mR);
  const b=[];
  m.plan.forEach(([cid,wd])=>{const r=h3.cellToBoundary(cid).map(p=>[p[0],p[1]]);
    L.polygon(r,{color:'#0b0d12',weight:.6,fillColor:C[wd]||C[6],fillOpacity:.85}).addTo(mL); r.forEach(x=>b.push(x));});
  m.act.forEach(([cid,wd])=>{const r=h3.cellToBoundary(cid).map(p=>[p[0],p[1]]);
    L.polygon(r,{color:'#0b0d12',weight:.6,fillColor:C[wd]||C[6],fillOpacity:.85}).addTo(mR); r.forEach(x=>b.push(x));});
  const bb=L.latLngBounds(b); mL.fitBounds(bb,{padding:[10,10]}); mR.fitBounds(bb,{padding:[10,10]});
  mL.setView(mR.getCenter(),mR.getZoom(),{animate:false});
  let lock=false;
  mL.on('move zoom',()=>{if(lock)return;lock=true;mR.setView(mL.getCenter(),mL.getZoom(),{animate:false});lock=false;});
  mR.on('move zoom',()=>{if(lock)return;lock=true;mL.setView(mR.getCenter(),mR.getZoom(),{animate:false});lock=false;});
  const rows = WDL.map((n,k)=>`<tr><td>${n}</td><td style="color:#93c5fd">${m.wdp[k]}</td><td style="color:#fca5a5">${m.wda[k]}</td></tr>`).join('');
  document.getElementById('tbl').innerHTML =
    `<table><thead><tr><th>周几</th><th>计划格数</th><th>实际格数</th></tr></thead><tbody>${rows}</tbody></table>`;
}
function orderAlong(xy, ids){            // 按"沿路方向"排序(主轴投影)
  const P=ids.map(i=>xy[i]);
  if(P.length<3) return P;
  const mx=P.reduce((a,p)=>a+p[0],0)/P.length, my=P.reduce((a,p)=>a+p[1],0)/P.length;
  let sxx=0,sxy=0,syy=0;
  P.forEach(p=>{const dx=p[0]-mx, dy=p[1]-my; sxx+=dx*dx; sxy+=dx*dy; syy+=dy*dy;});
  const th=0.5*Math.atan2(2*sxy, sxx-syy);
  const ux=Math.cos(th), uy=Math.sin(th);
  return P.slice().sort((a,b)=>((a[0]-mx)*ux+(a[1]-my)*uy)-((b[0]-mx)*ux+(b[1]-my)*uy));
}
function renderCorridor(d, m){
  // 每天一条连续线: 左=计划(最近邻序) 右=实际(打卡时间序)
  if(mL){mL.remove(); mR.remove();}
  mL=L.map('mL',{zoomControl:true,attributionControl:false});
  mR=L.map('mR',{zoomControl:false,attributionControl:false});
  const tile=x=>L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',{subdomains:'1234',maxZoom:18}).addTo(x);
  tile(mL); tile(mR);
  const b=[];
  const drawDays=(layer, days)=>{
    days.forEach(([dow, pts])=>{
      const col=C[dow]||C[6];
      L.polyline(pts,{color:col,weight:2.5,opacity:.9}).addTo(layer);
      pts.forEach(p=>{ L.circleMarker(p,{radius:2.4,color:'#0b0d12',weight:.4,fillColor:col,fillOpacity:.9}).addTo(layer); b.push(p); });
    });
  };
  drawDays(mL, m.daysP||[]);
  drawDays(mR, m.daysA||[]);
  if(!b.length){ L.polyline([[0,0],[0,0]]).addTo(mL); }
  const bb=L.latLngBounds(b); mL.fitBounds(bb,{padding:[10,10]}); mR.fitBounds(bb,{padding:[10,10]});
  mL.setView(mR.getCenter(),mR.getZoom(),{animate:false});
  let lock=false;
  mL.on('move zoom',()=>{if(lock)return;lock=true;mR.setView(mL.getCenter(),mL.getZoom(),{animate:false});lock=false;});
  mR.on('move zoom',()=>{if(lock)return;lock=true;mL.setView(mR.getCenter(),mR.getZoom(),{animate:false});lock=false;});
}
sel.onchange=()=>{i0=+sel.value; draw();};
modef.onchange=draw; weekf.onchange=fill; kindf.onchange=fill; verdictf.onchange=fill; cpf.onchange=fill; q.oninput=fill;
document.getElementById('prev').onclick=()=>{if(sel.selectedIndex>0){sel.selectedIndex--;i0=+sel.value;draw();}};
document.getElementById('next').onclick=()=>{if(sel.selectedIndex<sel.options.length-1){sel.selectedIndex++;i0=+sel.value;draw();}};
fill();
</script></body></html>
"""

if __name__ == "__main__":
    main()