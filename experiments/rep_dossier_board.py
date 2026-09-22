# -*- coding: utf-8 -*-
"""逐人档案看板 — 可搜索/排序, 一人一卡, 只看区块口径.

数据: output/rep_behavior/dossier.json (experiments/rep_dossier.py 生成)
输出: docs/reports/2026-09-22-rep-dossier.html
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "output/rep_behavior/dossier.json"
OUT = ROOT / "docs/reports/2026-09-22-rep-dossier.html"
KIND_COLOR = {"区块全开·星期照做": "#22c55e", "区块全开·区块内欠访": "#38bdf8", "区块缺了没开": "#fb923c",
              "区块全开·店和星期都有欠": "#eab308", "区块全开·星期自己定": "#a78bfa",
              "区块大面积没开工": "#f97316", "计划与实际几乎不相交": "#ef4444", "待人工看": "#94a3b8"}

HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>逐人行为档案 · 2026-08</title>
<style>
 body{margin:0;background:#0f1115;color:#e6e6e6;font:13px/1.65 -apple-system,"PingFang SC",sans-serif}
 header{padding:14px 20px;border-bottom:1px solid #232733;position:sticky;top:0;background:#0f1115;z-index:5}
 h1{font-size:17px;margin:0 0 4px} .sub{color:#8b93a7;font-size:12px}
 .bar{display:flex;gap:10px;align-items:center;margin-top:8px;flex-wrap:wrap}
 input,select{background:#1b2029;border:1px solid #2f3646;color:#e6e6e6;border-radius:6px;padding:5px 8px;font-size:12px}
 input{width:260px}
 .kinds{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:#aab3c5;margin-top:8px}
 .kindbadge{cursor:pointer;padding:2px 7px;border:1px solid #2f3646;border-radius:20px}
 .kindbadge.on{border-color:#60a5fa}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:12px;padding:14px 20px}
 .card{background:#161a22;border:1px solid #232733;border-radius:10px;padding:10px 12px}
 .card h3{margin:0 0 4px;font-size:13.5px;display:flex;justify-content:space-between;gap:8px}
 .k{font-size:11.5px;padding:1px 7px;border-radius:20px;border:1px solid #2f3646;white-space:nowrap}
 .story{font-size:12.5px;color:#cfd6e3;margin:6px 0 8px}
 .gauges{display:flex;gap:10px;flex-wrap:wrap;font-size:11.5px;color:#9aa4b8}
 .g{min-width:118px}
 .gbar{height:5px;background:#232733;border-radius:3px;margin-top:3px;overflow:hidden}
 .gbar i{display:block;height:5px}
 .wk{display:flex;gap:3px;align-items:flex-end;height:26px;margin-top:6px}
 .wk div{width:12px;background:#334155;border-radius:2px 2px 0 0}
 .wkrow{display:flex;gap:3px;font-size:10px;color:#64748b;margin-top:2px}
 .wkrow span{width:12px;text-align:center}
 .foot{color:#64748b;font-size:11px;margin-top:6px}
 .n{padding:6px 20px;color:#8b93a7;font-size:12px}
</style></head><body>
<header>
 <h1>逐人行为档案 · 2026-08（只看区块）</h1>
 <div class="sub">三把尺子全部只针对<b>计划内</b>的店：① 区块开工率（计划划分的区块他开工了几块）② 区块内执行率（区块里计划门店跑了几成，取各区块中位）③ 区块星期一致（区块的计划主力星期被实际执行的比例）。计划外门店不参与判定。</div>
 <div class="bar">
  <input id="q" placeholder="搜线号 / 城市 / 分型 / 区县">
  <select id="sort">
   <option value="block_exec_median">按 区块内执行率</option>
   <option value="block_worked_rate">按 区块开工率</option>
   <option value="block_wd_rate">按 区块星期一致</option>
   <option value="cover">按 覆盖</option>
   <option value="sameday">按 同日</option>
   <option value="qty">按 量比</option>
  </select>
  <span id="cnt" class="sub"></span>
 </div>
 <div class="kinds" id="kinds"></div>
</header>
<div class="grid" id="g"></div>
<div class="n" id="more"></div>
<script>
const D = __DATA__, KC = __KC__;
const qs = new URLSearchParams(location.search);
let kindFilter = qs.get('kind') || '', sortK = qs.get('sort') || 'block_exec_median', limit = +(qs.get('limit')||400);
const kinds = {}; D.forEach(d => kinds[d.kind] = (kinds[d.kind]||0)+1);
document.getElementById('kinds').innerHTML = Object.entries(kinds).sort((a,b)=>b[1]-a[1]).map(([k,v])=>
  `<span class="kindbadge${kindFilter===k?' on':''}" data-k="${k}"><i style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${KC[k]||'#999'};margin-right:5px"></i>${k} ${v}</span>`).join('');
document.querySelectorAll('.kindbadge').forEach(b => b.onclick = () => { kindFilter = (kindFilter===b.dataset.k)?'':b.dataset.k; location.search = `?kind=${encodeURIComponent(kindFilter)}&sort=${sortK}`; });
document.getElementById('sort').value = sortK;
document.getElementById('sort').onchange = e => { sortK = e.target.value; location.search = `?kind=${encodeURIComponent(kindFilter)}&sort=${sortK}`; };
document.getElementById('q').value = qs.get('q')||'';
document.getElementById('q').oninput = e => { const v=e.target.value; const u=new URL(location); u.searchParams.set('q',v); history.replaceState(0,'',u); render(v); };
function pct(v){ return (v*100).toFixed(0)+'%'; }
function gauge(label, v, color){ return `<div class="g">${label} <b style="color:${color}">${pct(v)}</b><div class="gbar"><i style="width:${Math.max(2,v*100)}%;background:${color}"></i></div></div>`; }
function render(q=''){
  const s=(q||'').toLowerCase();
  let arr = D.filter(d => (!kindFilter || d.kind===kindFilter) &&
    (!s || (d.line+' '+d.city+' '+d.kind+' '+d.districts).toLowerCase().includes(s)));
  arr.sort((a,b)=> (b[sortK]||0)-(a[sortK]||0));
  document.getElementById('cnt').textContent = `匹配 ${arr.length} 人（显示前 ${Math.min(limit,arr.length)}）`;
  const wk = d => `同 ${d.wd_visits[0]}/周 ${d.wd_visits[1]}/${d.wd_visits[2]}/${d.wd_visits[3]}/${d.wd_visits[4]}/六 ${d.wd_visits[5]}/日 ${d.wd_visits[6]}`;
  document.getElementById('g').innerHTML = arr.slice(0,limit).map(d => {
    const mx = Math.max(...d.wd_visits, 1);
    return `<div class="card">
      <h3><span>${d.line} · ${d.city}</span><span class="k" style="color:${KC[d.kind]||'#999'}">${d.kind}</span></h3>
      <div class="story">${d.story}</div>
      <div class="gauges">
        ${gauge('区块开工', d.block_worked_rate, '#22c55e')}
        ${gauge('区块内执行', d.block_exec_median, '#38bdf8')}
        ${gauge('区块星期', d.block_wd_rate, '#a78bfa')}
      </div>
      <div class="wk">${d.wd_visits.map(v=>`<div style="height:${Math.max(2,v/mx*26)}px" title="${v}"></div>`).join('')}</div>
      <div class="wkrow">${['一','二','三','四','五','六','日'].map(x=>`<span>${x}</span>`).join('')}</div>
      <div class="foot">区块 ${d.blocks_worked}/${d.blocks} 开工 · 计划 ${d.plan_stores} 店 → 实际 ${d.act_stores} 店 / ${d.act_visits} 次 · 工作日 ${d.workdays} 天 · 日均 ${d.daily_avg} 店 · 量比 ${d.qty}</div>
    </div>`;}).join('');
}
document.getElementById('more').textContent = '数据: output/rep_behavior/dossier.json（experiments/rep_dossier.py 生成；可用 URL 参数 ?kind= / ?sort= / ?q= 过滤）';
render(document.getElementById('q').value);
</script></body></html>
"""


def main():
    recs = json.loads(SRC.read_text(encoding="utf-8"))
    keep = [{k: v for k, v in r.items() if k != "never"} for r in recs]
    html = HTML.replace("__DATA__", json.dumps(keep, ensure_ascii=False)).replace("__KC__", json.dumps(KIND_COLOR, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"写出 {OUT} ({OUT.stat().st_size/1024:.0f} KB) | {len(keep)} 人")


if __name__ == "__main__":
    main()