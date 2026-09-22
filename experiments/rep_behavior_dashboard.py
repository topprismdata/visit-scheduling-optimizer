# -*- coding: utf-8 -*-
"""全量销售行为看板 — 两轴散点(地块一致度×星期一致度) + 城市汇总 + 可排序明细.

数据: output/rep_behavior/all_reps.csv (由 experiments/all_rep_behavior.py 生成)
输出: docs/reports/2026-09-22-rep-behavior-board.html (离线自包含, 数据内嵌)
用法: python experiments/rep_behavior_dashboard.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "output/rep_behavior/all_reps.csv"
OUT = ROOT / "docs/reports/2026-09-22-rep-behavior-board.html"
KIND_COLOR = {"照做型": "#22c55e", "少跑但没跑偏": "#38bdf8", "地块同步·日期松散": "#eab308",
              "地块同步·星期偏移": "#f97316", "漂移/混合": "#ef4444"}

HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>全量销售行为看板 · 2026-08</title>
<style>
 body{margin:0;background:#0f1115;color:#e6e6e6;font:13px/1.6 -apple-system,"PingFang SC",sans-serif}
 header{padding:16px 20px;border-bottom:1px solid #232733}
 h1{font-size:18px;margin:0 0 6px} .sub{color:#8b93a7;font-size:12px;line-height:1.8}
 .wrap{display:grid;grid-template-columns:minmax(520px,1.1fr) minmax(420px,1fr);gap:14px;padding:14px 20px}
 .card{background:#161a22;border:1px solid #232733;border-radius:10px;padding:12px 14px}
 .card h2{font-size:13px;margin:0 0 8px;color:#cbd5e1;font-weight:600}
 .kpi{display:flex;gap:18px;flex-wrap:wrap;margin:2px 0 10px}
 .kpi div{font-size:12px;color:#9aa4b8} .kpi b{display:block;font-size:19px;color:#e6e6e6}
 .lg{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:#aab3c5;margin-top:6px}
 .sw{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
 table{width:100%;border-collapse:collapse;font-size:12px}
 th,td{padding:4px 6px;border-bottom:1px solid #232733;text-align:right;white-space:nowrap}
 th{color:#93a2b8;cursor:pointer;user-select:none;position:sticky;top:0;background:#161a22}
 td:first-child,th:first-child{text-align:left}
 tr:hover td{background:#1b2029}
 .scroll{max-height:420px;overflow:auto;border:1px solid #232733;border-radius:8px}
 svg{background:#0b0d12;border-radius:8px;width:100%;height:420px}
 .tip{position:fixed;pointer-events:none;background:#000c;border:1px solid #334155;padding:6px 9px;border-radius:6px;font-size:12px;display:none;z-index:9}
 .note{padding:0 20px 24px;color:#8b93a7;font-size:12px}
</style></head><body>
<header><h1>全量销售行为看板 · 2026-08（<span id="n"></span> 条线）</h1>
<div class="sub">
 两把尺子都相对<b>计划</b>（版本《更新后的8月规划》）：<b>X = 地块一致度</b>（计划门店被执行的比例）；<b>Y = 星期一致度</b>（计划的"店-星期"被同星期执行的比例）。<br>
 点色 = 分型；右上角＝照做，左下角＝漂移。相关 Pearson 0.94 / Spearman 0.97 → 两轴高度耦合，"地块一样只换星期"在实践中罕见（严格 0.9%）。
</div></header>
<div class="wrap">
 <div class="card"><h2>地块一致度 × 星期一致度</h2><svg id="sc"></svg>
  <div class="lg" id="lg"></div></div>
 <div><div class="card"><h2>分型分布</h2><div class="kpi" id="kinds"></div>
   <div class="scroll"><table id="city"><thead><tr><th>城市</th><th>线数</th><th>照做%</th><th>漂移%</th><th>覆盖中位</th><th>纯度中位</th><th>星期中位</th></tr></thead><tbody></tbody></table></div>
   <div class="lg" style="color:#8b93a7">城市按漂移率降序（线≥8）</div></div>
 </div>
</div>
<div class="card" style="margin:0 20px 14px"><h2>全部线明细（点表头排序）</h2>
 <div class="scroll"><table id="tbl"><thead><tr>
   <th data-k="line">线</th><th data-k="city_name">城市</th><th data-k="kind">分型</th><th data-k="plan_stores">计划店</th><th data-k="act_stores">实际店</th>
   <th data-k="cover">覆盖</th><th data-k="purity">纯度</th><th data-k="wd_match">星期</th><th data-k="sameday">同日</th><th data-k="phase">相位</th><th data-k="qty">量比</th>
 </tr></thead><tbody></tbody></table></div></div>
<div class="note">生成：<code>experiments/rep_behavior_dashboard.py</code> ← <code>output/rep_behavior/all_reps.csv</code>。所有坐标/指标口径见脚本文档字符串。</div>
<div class="tip" id="tip"></div>
<script>
const D = __DATA__;
const KC = __KC__;
document.getElementById('n').textContent = D.length;
// KPI
const kinds = {};
D.forEach(d => kinds[d.kind] = (kinds[d.kind]||0)+1);
document.getElementById('kinds').innerHTML = Object.entries(kinds).sort((a,b)=>b[1]-a[1])
  .map(([k,v])=>`<div><b style="color:${KC[k]||'#999'}">${v}</b>${k} · ${(v/D.length*100).toFixed(1)}%</div>`).join('');
document.getElementById('lg').innerHTML = Object.keys(KC).map(k=>`<span><i class="sw" style="background:${KC[k]}"></i>${k}</span>`).join('');
// 散点
const svg = document.getElementById('sc'), W = svg.clientWidth || 560, H = 420, P = 34;
svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
const xs = v => P + v*(W-2*P), ys = v => H-P - v*(H-2*P);
let s = '';
for (let i=0;i<=10;i++){ const v=i/10;
  s += `<line x1="${xs(v)}" y1="${ys(0)}" x2="${xs(v)}" y2="${ys(1)}" stroke="#1c2230"/>`;
  s += `<line x1="${xs(0)}" y1="${ys(v)}" x2="${xs(1)}" y2="${ys(v)}" stroke="#1c2230"/>`; }
s += `<line x1="${xs(0.9)}" y1="${ys(0)}" x2="${xs(0.9)}" y2="${ys(1)}" stroke="#334155" stroke-dasharray="4,3"/>`;
s += `<line x1="${xs(0)}" y1="${ys(0.75)}" x2="${xs(1)}" y2="${ys(0.75)}" stroke="#334155" stroke-dasharray="4,3"/>`;
s += `<text x="${xs(0.5)}" y="${H-6}" fill="#8b93a7" font-size="11" text-anchor="middle">地块一致度 cover →</text>`;
s += `<text x="12" y="${ys(0.5)}" fill="#8b93a7" font-size="11" transform="rotate(-90 12 ${ys(0.5)})" text-anchor="middle">星期一致度 wd_match →</text>`;
D.forEach((d,i) => { s += `<circle data-i="${i}" cx="${xs(d.cover)}" cy="${ys(d.wd_match)}" r="3.2" fill="${KC[d.kind]||'#999'}" fill-opacity=".78" stroke="#0b0d12" stroke-width=".4"/>`; });
svg.innerHTML = s;
const tip = document.getElementById('tip');
svg.addEventListener('mousemove', e => {
  const t = e.target.closest('circle'); if (!t) { tip.style.display='none'; return; }
  const d = D[+t.dataset.i];
  tip.style.display='block'; tip.style.left = (e.clientX+12)+'px'; tip.style.top = (e.clientY+10)+'px';
  tip.innerHTML = `<b>${d.line}</b> · ${d.city_name||d.city||''} · ${d.kind}<br>覆盖 ${(d.cover*100).toFixed(1)}% · 纯度 ${(d.purity*100).toFixed(1)}%<br>星期 ${(d.wd_match*100).toFixed(1)}% · 同日 ${(d.sameday*100).toFixed(1)}% · 相位 ${(d.phase*100).toFixed(1)}%<br>计划 ${d.plan_stores} 店 → 实际 ${d.act_stores} 店 · 量比 ${d.qty}`;
});
svg.addEventListener('mouseleave', ()=> tip.style.display='none');
// 城市表
const byCity = {};
D.forEach(d => { if(!d.city) return; (byCity[d.city_name||d.city] ||= []).push(d); });
const rows = Object.entries(byCity).map(([c,arr]) => ({
  city:c, n:arr.length,
  照做: arr.filter(x=>x.kind==='照做型').length/arr.length*100,
  漂移: arr.filter(x=>x.kind==='漂移/混合').length/arr.length*100,
  cov: arr.map(x=>x.cover).sort((a,b)=>a-b)[Math.floor(arr.length/2)],
  pur: arr.map(x=>x.purity).sort((a,b)=>a-b)[Math.floor(arr.length/2)],
  wd: arr.map(x=>x.wd_match).sort((a,b)=>a-b)[Math.floor(arr.length/2)]
})).filter(r=>r.n>=8).sort((a,b)=>b.漂移-a.漂移);
document.querySelector('#city tbody').innerHTML = rows.map(r =>
  `<tr><td>${r.city}</td><td>${r.n}</td><td>${r.照做.toFixed(0)}</td><td style="color:${r.漂移>60?'#fca5a5':'#e6e6e6'}">${r.漂移.toFixed(0)}</td><td>${r.cov.toFixed(2)}</td><td>${r.pur.toFixed(2)}</td><td>${r.wd.toFixed(2)}</td></tr>`).join('');
// 明细表 + 排序
let sortK='cover', asc=true;
function render(){
  const rows=[...D].sort((a,b)=>{ const x=a[sortK], y=b[sortK]; return (x>y?1:x<y?-1:0)*(asc?1:-1); });
  document.querySelector('#tbl tbody').innerHTML = rows.map(d=>`<tr>
    <td>${d.line}</td><td>${d.city_name||d.city||''}</td><td style="color:${KC[d.kind]||'#999'}">${d.kind}</td>
    <td>${d.plan_stores}</td><td>${d.act_stores}</td>
    <td>${(d.cover*100).toFixed(1)}%</td><td>${(d.purity*100).toFixed(1)}%</td><td>${(d.wd_match*100).toFixed(1)}%</td>
    <td>${(d.sameday*100).toFixed(1)}%</td><td>${(d.phase*100).toFixed(1)}%</td><td>${d.qty}</td></tr>`).join('');
}
document.querySelectorAll('#tbl th').forEach(th => th.onclick = () => { const k=th.dataset.k; if(k===sortK) asc=!asc; else {sortK=k; asc=true;} render(); });
render();
</script></body></html>
"""


def main():
    d = pd.read_csv(CSV)
    P = pd.read_excel("/Users/ghb/UFS-demo/更新后的8月规划.xlsx",
                      usecols=lambda c: c in ("sales_line_code", "city"))
    P["sales_line_code"] = P["sales_line_code"].astype(str)
    cmap = P.drop_duplicates("sales_line_code").set_index("sales_line_code")["city"].to_dict()
    nm = pd.read_excel("/Users/ghb/Downloads/全部.xlsx", usecols=["city", "城市名称"])
    nm["city"] = nm["city"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    names = dict(zip(nm["city"], nm["城市名称"]))
    assert names, "城市名映射为空"
    print(f"城市名映射 {len(names)} 个")
    d["city"] = d["line"].map(cmap)
    d["city_name"] = d["city"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6).map(lambda c: names.get(c, c))
    recs = d[["line", "city", "city_name", "kind", "plan_stores", "act_stores", "cover", "purity",
              "wd_match", "sameday", "phase", "qty"]].round(4).to_dict("records")
    low = int((d["cover"] < 0.3).sum())
    print(f"极端错位线(覆盖<30%): {low} 条 ({low/len(d)*100:.1f}%)")
    print(f"覆盖<30% 的线里, 实际到访数中位 {d.loc[d['cover']<0.3,'act_rows'].median():.0f} | 计划行中位 {d.loc[d['cover']<0.3,'plan_rows'].median():.0f}")
    html = HTML.replace("__DATA__", json.dumps(recs, ensure_ascii=False)) \
               .replace("__KC__", json.dumps(KIND_COLOR, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"写出 {OUT} ({OUT.stat().st_size/1024:.0f} KB) | 记录 {len(recs)} 条")


if __name__ == "__main__":
    main()