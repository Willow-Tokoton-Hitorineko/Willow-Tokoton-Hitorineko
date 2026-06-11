"""HTML 看板生成引擎 — 通用化，适用于任意城市。"""
from __future__ import annotations

import json
from datetime import datetime as dt
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd


from .config import CORE8, CORE8_LABELS, DASHBOARDS_DIR


def build_dashboard_html(gap_data: dict, candidates: list[dict] = None, candidate_source: str = "") -> str:
    """
    从缺口诊断数据 + 候选列表生成独立 HTML 看板。
    返回完整 HTML 字符串。
    """
    candidates = candidates or []
    payload = {
        **gap_data,
        "core8_fields": CORE8,
        "core8_labels": CORE8_LABELS,
        "candidates": candidates,
        "candidate_source": candidate_source,
        "generated": dt.now().strftime("%Y-%m-%d %H:%M"),
    }
    # 确保 JSON 可序列化（numpy bool/int → python native）
    def _make_serializable(obj):
        if isinstance(obj, dict):
            return {k: _make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_make_serializable(v) for v in obj]
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        return obj
    payload = _make_serializable(payload)
    payload_json = json.dumps(payload, ensure_ascii=False)
    s = payload["summary"]
    city_n = s["city_level_n"]
    dist_n = s["district_n"]
    n_cand = len(candidates)
    pending_n = len(gap_data.get("pending_files", []))
    pending_html = f'<div class="kpi amber"><div class="kpi-label">待入库</div><div class="kpi-value">{pending_n} 个</div><div class="kpi-sub">本地已采集未结构化</div></div>' if pending_n else ""
    gap_font = "1.6rem" if s.get("has_gap") else "1rem"
    gap_label = "无制度文本" if s.get("has_gap") else "年份连续"
    prov_n = s.get("provincial_n", 0)
    prov_tab_html = f'<button class="tab-btn" data-tab="provincial">省级 · {prov_n}</button>' if prov_n > 0 else ""

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{gap_data["city"]} · 制度文本缺口看板</title>
<style>
:root{{--bg:#f5f5f7;--card:#fff;--text:#1d1d1f;--muted:#86868b;--border:#e5e5ea;--shadow:0 1px 3px rgba(0,0,0,.04),0 1px 2px rgba(0,0,0,.06);--shadow-lg:0 10px 15px rgba(0,0,0,.04),0 4px 6px rgba(0,0,0,.05);--blue:#0071e3;--blue-bg:#f0f7ff;--red:#e03a3a;--red-bg:#fff5f5;--green:#30b55a;--green-bg:#f2fbf5;--amber:#e09d00;--amber-bg:#fffcf0;--radius:12px;--font:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC","Microsoft YaHei",sans-serif;--font-mono:"SF Mono","Cascadia Code",Consolas,monospace}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.55;-webkit-font-smoothing:antialiased}}
header{{background:#1d1d1f;color:#f5f5f7;padding:1.5rem 2rem;box-shadow:0 2px 20px rgba(0,0,0,.15);position:sticky;top:0;z-index:100}}
header h1{{font-size:1.35rem;font-weight:700;letter-spacing:-.02em}}
header .sub{{font-size:.8rem;color:#a1a1aa;margin-top:.25rem}}
.wrap{{max-width:1340px;margin:0 auto;padding:2rem 2rem 3rem}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:.85rem;margin-bottom:1.5rem}}
.kpi{{background:var(--card);border-radius:var(--radius);padding:1rem 1.15rem;box-shadow:var(--shadow);border:1px solid var(--border);position:relative;overflow:hidden;transition:transform .2s,box-shadow .2s}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:var(--radius) var(--radius) 0 0}}
.kpi.warn::before{{background:var(--red)}}.kpi.ok::before{{background:var(--green)}}.kpi.info::before{{background:var(--blue)}}.kpi.amber::before{{background:var(--amber)}}
.kpi:hover{{transform:translateY(-3px);box-shadow:var(--shadow-lg)}}
.kpi .kpi-label{{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:600}}
.kpi .kpi-value{{font-size:1.6rem;font-weight:700;margin-top:.1rem;letter-spacing:-.02em}}
.kpi .kpi-sub{{font-size:.7rem;color:var(--muted);margin-top:.1rem}}
.kpi.warn .kpi-value{{color:var(--red)}}.kpi.ok .kpi-value{{color:var(--green)}}.kpi.info .kpi-value{{color:var(--blue)}}.kpi.amber .kpi-value{{color:var(--amber)}}
.tab-bar{{display:flex;gap:.15rem;margin-bottom:1.25rem;background:var(--card);border-radius:var(--radius);padding:.3rem;box-shadow:var(--shadow);border:1px solid var(--border)}}
.tab-btn{{flex:1;padding:.6rem 1rem;border:none;background:transparent;border-radius:9px;cursor:pointer;font-size:.82rem;font-weight:500;color:var(--muted);transition:all .2s;font-family:var(--font);white-space:nowrap}}
.tab-btn:hover{{background:#f0f0f5;color:var(--text)}}
.tab-btn.active{{background:#1d1d1f;color:#fff;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,.12)}}
.tab-pane{{display:none;animation:fadeIn .3s ease}}
.tab-pane.active{{display:block}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:translateY(0)}}}}
.panel{{background:var(--card);border-radius:var(--radius);padding:1.25rem 1.5rem;box-shadow:var(--shadow);border:1px solid var(--border);margin-bottom:1rem}}
.panel h2{{font-size:.95rem;font-weight:700;margin-bottom:.85rem;display:flex;align-items:center;gap:.5rem}}
.alert{{padding:.85rem 1.1rem;border-radius:8px;margin-bottom:1rem;font-size:.8rem;line-height:1.55}}
.alert-danger{{background:var(--red-bg);border:1px solid #ffd4d4;color:#991b1b}}
.alert-info{{background:var(--blue-bg);border:1px solid #c2e0ff;color:#1e3a5f}}
.alert-warn{{background:var(--amber-bg);border:1px solid #ffe8a0;color:#6b4d00}}
.tbl-wrap{{overflow-x:auto;border-radius:8px;border:1px solid var(--border)}}
table{{width:100%;border-collapse:collapse;font-size:.72rem}}
thead th{{background:#fafafa;font-weight:600;padding:.55rem .5rem;text-align:left;border-bottom:2px solid #eaeaef;position:sticky;top:0;z-index:1;font-size:.7rem;color:var(--muted);white-space:nowrap}}
tbody td{{padding:.45rem .5rem;border-bottom:1px solid #f3f3f7;vertical-align:middle}}
tbody tr:nth-child(even){{background:#fafafa}}
tbody tr:hover{{background:#f0f7ff}}
.f-hit{{display:inline-block;background:#dcfce7;color:#166534;padding:.12rem .4rem;border-radius:5px;font-size:.68rem;font-weight:600}}
.f-no{{display:inline-block;background:#fee2e2;color:#991b1b;padding:.12rem .4rem;border-radius:5px;font-size:.68rem}}
.f-nan{{display:inline-block;background:#f3f4f6;color:#9ca3af;padding:.12rem .4rem;border-radius:5px;font-size:.68rem;font-style:italic}}
.tag{{display:inline-block;padding:.1rem .45rem;border-radius:5px;font-size:.68rem;font-weight:600}}
.tag-red{{background:#fee2e2;color:#991b1b}}.tag-green{{background:#dcfce7;color:#166534}}.tag-amber{{background:#fef3c7;color:#92400e}}.tag-blue{{background:#dbeafe;color:#1e40af}}.tag-gray{{background:#f3f4f6;color:#6b7280}}
.chart-wrap{{position:relative;height:280px;margin-top:.5rem}}
.legend{{display:flex;gap:1rem;flex-wrap:wrap;font-size:.73rem;margin:.5rem 0}}
.legend-item{{display:flex;align-items:center;gap:.35rem}}
.legend-swatch{{width:14px;height:14px;border-radius:4px}}
.heatmap-table td{{text-align:center;padding:.3rem .4rem;font-size:.68rem;min-width:28px}}
.heatmap-table th{{text-align:center;font-size:.65rem;padding:.3rem .4rem}}
a{{color:var(--blue);text-decoration:none;font-weight:500}}a:hover{{color:#0058b0;text-decoration:underline}}
@media(max-width:768px){{.wrap{{padding:1rem}}.kpi-grid{{grid-template-columns:repeat(2,1fr)}}.tab-btn{{font-size:.72rem;padding:.5rem .55rem}}.tl-n{{display:none}}}}
@media(max-width:480px){{.kpi-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header>
<h1>{gap_data["city"]} · 制度文本缺口看板</h1>
<div class="sub">生成于 {payload["generated"]} · {gap_data["province"]}</div>
</header>
<div class="wrap">
<div class="kpi-grid">
<div class="kpi {'warn' if s['city_level_n'] < 3 else 'ok'}"><div class="kpi-label">市级制度文本</div><div class="kpi-value">{s["city_level_n"]} 条</div><div class="kpi-sub">{s["year_range_city"]}{' (含省级)' if s.get('is_municipality') else ''}</div></div>
<div class="kpi {'warn' if s['district_n'] < 2 else 'ok'}"><div class="kpi-label">区级制度文本</div><div class="kpi-value">{s["district_n"]} 条</div><div class="kpi-sub">{s["year_range_district"]}</div></div>
<div class="kpi {'warn' if s.get('provincial_n',0) == 0 else 'ok'}"><div class="kpi-label">省级制度文本</div><div class="kpi-value">{s.get('provincial_n',0)} 条</div><div class="kpi-sub">{gap_data['province']}</div></div>
<div class="kpi amber"><div class="kpi-label">市级断层</div><div class="kpi-value" style="font-size:{gap_font}">{s["gap_years"]}</div><div class="kpi-sub">{gap_label}</div></div>
<div class="kpi info"><div class="kpi-label">已入库</div><div class="kpi-value">{s['city_level_n'] + s['district_n'] + s.get('provincial_n',0)} 条</div><div class="kpi-sub">市{s['city_level_n']}+区{s['district_n']}+省{s.get('provincial_n',0)}</div></div>
<div class="kpi info"><div class="kpi-label">采集候选</div><div class="kpi-value">{n_cand} 条</div><div class="kpi-sub">搜狗微信搜索</div></div>
{pending_html}
</div>
<div class="tab-bar" id="tabBar">
<button class="tab-btn active" data-tab="city">市级文本 · {s["city_level_n"]}</button>
<button class="tab-btn" data-tab="district">区级文本 · {s["district_n"]}</button>
<button class="tab-btn" data-tab="timeline">时间线</button>
<button class="tab-btn" data-tab="heatmap">热力图</button>
{prov_tab_html}
<button class="tab-btn" data-tab="candidates">采集候选 · {len(candidates)}</button>
</div>
<div id="tab-city" class="tab-pane active"></div>
<div id="tab-district" class="tab-pane"></div>
<div id="tab-provincial" class="tab-pane"></div>
<div id="tab-timeline" class="tab-pane"></div>
<div id="tab-heatmap" class="tab-pane"></div>
<div id="tab-candidates" class="tab-pane"></div>
</div>
<script>
(function(){{
var P={payload_json};
document.getElementById("tabBar").addEventListener("click",function(e){{
var b=e.target.closest(".tab-btn");if(!b)return;
document.querySelectorAll(".tab-btn").forEach(function(t){{t.classList.remove("active")}});
document.querySelectorAll(".tab-pane").forEach(function(p){{p.classList.remove("active")}});
b.classList.add("active");document.getElementById("tab-"+b.dataset.tab).classList.add("active");
}});
function fc(d){{if(!d)return'<span class="f-nan">-</span>';if(d.hit)return'<span class="f-hit">'+d.value+'</span>';var v=d.value;if(v==='nan'||v===''||v==='None')return'<span class="f-nan">-</span>';if(v==='no'||v==='0')return'<span class="f-no">无</span>';return'<span class="f-no">'+v+'</span>'}}
function it(is){{if(!is.length)return'<span class="tag tag-gray">-</span>';return is.map(function(i){{return'<span class="tag '+(i.indexOf("分类")>=0?"tag-red":"tag-amber")+'">'+i+'</span>'}}).join(" ")}}
function rt(ts,fs,ls){{
if(!ts.length)return'<div class="panel"><p style="color:var(--muted)">无数据</p></div>';
var h='<div class="panel"><div class="tbl-wrap"><table><thead><tr><th>ID</th><th>标题</th><th>年</th><th>层级</th><th>文种</th><th>命中</th>';
fs.forEach(function(f,i){{h+='<th title="'+f+'">'+ls[i]+'</th>'}});
h+='<th>标注</th></tr></thead><tbody>';
ts.forEach(function(r){{
h+='<tr><td>'+(r.source_id||"-")+'</td><td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+r.title.replace(/"/g,"&quot;")+'">'+r.title.substring(0,65)+'</td><td>'+(r.year||"-")+'</td><td><span class="tag '+(r.source_level===\"省级\"?\"tag-amber\":\"tag-gray\")+'">'+r.source_level+'</span></td><td>'+r.doc_type+'</td><td><b>'+r.hits+'/8</b></td>';
fs.forEach(function(f){{h+='<td>'+fc(r.fields[f])+'</td>'}});
h+='<td>'+it(r.issues)+'</td></tr>';
}});
return h+'</tbody></table></div></div>';
}}

var fs=P.core8_fields,ls=P.core8_labels;
document.getElementById("tab-city").innerHTML=
(P.city_texts.length&&P.city_texts.every(function(t){{return t.year<2012&&t.hits===0}})?
'<div class="alert alert-danger"><b>[!]</b> 市级制度文本均来自2012年以前，全部8核心字段零命中或未提取。2012年后存在制度文本断层。</div>'
:'<div class="alert alert-info">市级制度文本'+(P.summary.is_municipality?' (含省级文本，已在「层级」列标注来源)':'')+'</div>')
+(P.pending_files&&P.pending_files.length?'<div class="alert alert-warn"><b>待入库</b>: '+P.pending_files.length+' 个本地文件（已采集未结构化） — <b>不在下方统计内</b></div>':'')
+(P.pending_files&&P.pending_files.length?'<div class="panel"><h2>待结构化文件列表 ('+P.pending_files.length+')</h2><div class="tbl-wrap"><table><thead><tr><th>#</th><th>文件名</th><th>路径</th><th>预览</th></tr></thead><tbody>'+P.pending_files.map(function(f,i){{return'<tr><td>'+(i+1)+'</td><td>'+f.filename.substring(0,60)+'</td><td style=\"font-size:.68rem;color:var(--muted)\">'+f.path+'</td><td style=\"font-size:.7rem;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap\">'+f.preview.substring(0,80)+'</td></tr>'}}).join('')+'</tbody></table></div></div>':'')
+rt(P.city_texts,fs,ls);
document.getElementById("tab-district").innerHTML=
(P.district_texts.length>0?'<div class="alert alert-info">区级制度文本</div>':'<div class="alert alert-warn">该城市暂无区级制度文本入库</div>')
+rt(P.district_texts,fs,ls);
document.getElementById("tab-provincial").innerHTML=
(P.provincial_texts&&P.provincial_texts.length>0?'<div class="alert alert-info">省级制度文本 ('+P.province+')</div>':'<div class="alert alert-warn">该省暂无省级制度文本入库</div>')
+rt(P.provincial_texts||[],fs,ls);
(function(){{
var tl=P.year_timeline;
if(!tl.length){{document.getElementById("tab-timeline").innerHTML='<div class="panel"><p style="color:var(--muted)">无数据</p></div>';return}}
var years=tl.map(function(y){{return y.year}});
var yMin=Math.min.apply(null,years),yMax=Math.max.apply(null,years);
var vMax=0;tl.forEach(function(y){{vMax=Math.max(vMax,y["市级"]||0,y["区县级"]||0)}});
vMax=Math.max(vMax,1);
var W=920,H=240,padL=50,padR=30,padT=20,padB=40;
var xScale=function(yr){{return padL+(yr-yMin)/(yMax-yMin||1)*(W-padL-padR)}};
var yScale=function(v){{return H-padB-(v/vMax)*(H-padT-padB)}};
var cityPts=[],distPts=[],yTicks=[];
var tlMap={{}};tl.forEach(function(y){{tlMap[y.year]=y}});
for(var yr=yMin;yr<=yMax;yr++){{
var y=tlMap[yr]||{{"市级":0,"区县级":0}};
cityPts.push(xScale(yr)+','+yScale(y["市级"]||0));
distPts.push(xScale(yr)+','+yScale(y["区县级"]||0));
if(yr===yMin||yr===yMax||(yr-yMin)%Math.max(1,Math.floor((yMax-yMin+1)/10))===0)
    yTicks.push({{x:xScale(yr),label:String(yr).substring(2)}});
}}

var h='<div class="panel"><h2>年份分布</h2>';
h+='<div class="legend"><div class="legend-item"><div class="legend-swatch" style="background:#e03a3a;border-radius:50%"></div>市级</div><div class="legend-item"><div class="legend-swatch" style="background:#0071e3;border-radius:50%"></div>区县级</div></div>';
h+='<div class="chart-wrap"><svg viewBox="0 0 '+W+' '+H+'" style="width:100%;height:100%">';
// Grid
for(var g=0;g<=4;g++){{var gy=yScale(vMax*g/4);h+='<line x1="'+padL+'" y1="'+gy+'" x2="'+(W-padR)+'" y2="'+gy+'" stroke="#e5e7eb" stroke-dasharray="4,4"/>';h+='<text x="'+(padL-8)+'" y="'+(gy+4)+'" text-anchor="end" font-size="10" fill="#9ca3af">'+Math.round(vMax*g/4)+'</text>'}}
// X ticks
yTicks.forEach(function(t){{h+='<text x="'+t.x+'" y="'+(H-8)+'" text-anchor="middle" font-size="10" fill="#9ca3af">'+t.label+'</text>'}});
// City line + dots
h+='<polyline points="'+cityPts.join(' ')+'" fill="none" stroke="#e03a3a" stroke-width="2.5" stroke-linejoin="round"/><polyline points="'+cityPts.join(' ')+'" fill="none" stroke="#e03a3a" stroke-width="5" stroke-linecap="round" opacity="0"/>';
tl.forEach(function(y){{if(y["市级"]>0)h+='<circle cx="'+xScale(y.year)+'" cy="'+yScale(y["市级"])+'" r="3" fill="#e03a3a"><title>'+y.year+' 市级:'+y["市级"]+'</title></circle>'}});
// District line + dots
h+='<polyline points="'+distPts.join(' ')+'" fill="none" stroke="#0071e3" stroke-width="2.5" stroke-linejoin="round"/><polyline points="'+distPts.join(' ')+'" fill="none" stroke="#0071e3" stroke-width="5" stroke-linecap="round" opacity="0"/>';
tl.forEach(function(y){{if(y["区县级"]>0)h+='<circle cx="'+xScale(y.year)+'" cy="'+yScale(y["区县级"])+'" r="3" fill="#0071e3"><title>'+y.year+' 区级:'+y["区县级"]+'</title></circle>'}});
// Gap zone highlight
var gapStart=null,gapEnd=null;
for(var i=0;i<tl.length;i++){{if(tl[i].year>=2012&&tl[i]["市级"]===0){{if(gapStart===null)gapStart=tl[i].year;gapEnd=tl[i].year}}}}
if(gapStart!==null){{
var gx1=xScale(gapStart),gx2=xScale(gapEnd);
h+='<rect x="'+gx1+'" y="'+padT+'" width="'+(gx2-gx1+8)+'" height="'+(H-padT-padB)+'" fill="#fef2f2" opacity="0.6"/>';
h+='<text x="'+(gx1+(gx2-gx1)/2)+'" y="'+(padT+16)+'" text-anchor="middle" font-size="10" fill="#dc2626">断层 '+gapStart+'-'+gapEnd+'</text>';
}}
h+='</svg></div></div>';
document.getElementById("tab-timeline").innerHTML=h;
}})();
(function(){{
var hm=P.heatmap||[];
if(!hm.length){{document.getElementById("tab-heatmap").innerHTML='<div class="panel"><p style=\"color:var(--muted)\">无数据</p></div>';return}}
var allYears=new Set();hm.forEach(function(r){{Object.keys(r.years).forEach(function(y){{allYears.add(parseInt(y))}})}});
var yrList=Array.from(allYears).sort(function(a,b){{return a-b}});
var yMin2=yrList[0],yMax2=yrList[yrList.length-1];
var fullYrList=[];
for(var y=yMin2;y<=yMax2;y++)fullYrList.push(y);
if(!yrList.length){{document.getElementById("tab-heatmap").innerHTML='<div class="panel"><p style=\"color:var(--muted)\">无年份数据</p></div>';return}}
var maxN=1;hm.forEach(function(r){{Object.values(r.years).forEach(function(v){{maxN=Math.max(maxN,v)}})}});
function heatColor(n){{if(!n)return'#f8f9fa';var p=n/maxN;if(p<.25)return'#dbeafe';if(p<.5)return'#93c5fd';if(p<.75)return'#3b82f6';return'#1e40af'}}
var h='<div class=\"panel\"><h2>文本覆盖热力图</h2><div class=\"legend\"><div class=\"legend-item\"><div class=\"legend-swatch\" style=\"background:#f8f9fa;border:1px solid #e5e7eb\"></div>0</div><div class=\"legend-item\"><div class=\"legend-swatch\" style=\"background:#dbeafe\"></div>1-'+Math.ceil(maxN*.25)+'</div><div class=\"legend-item\"><div class=\"legend-swatch\" style=\"background:#93c5fd\"></div></div><div class=\"legend-item\"><div class=\"legend-swatch\" style=\"background:#3b82f6\"></div></div><div class=\"legend-item\"><div class=\"legend-swatch\" style=\"background:#1e40af\"></div>'+maxN+'</div></div>';
h+='<div class=\"tbl-wrap\" style=\"max-height:500px;overflow:auto\"><table><thead><tr><th style=\"min-width:120px\">区域</th>';
fullYrList.forEach(function(y){{h+='<th style=\"text-align:center;font-size:.65rem\">'+(String(y).substring(2))+'</th>'}});
h+='</tr></thead><tbody>';
hm.forEach(function(r){{
h+='<tr><td style=\"font-weight:600;font-size:.73rem\">'+r.label+'</td>';
fullYrList.forEach(function(y){{
var n=r.years[y]||0;
h+='<td style=\"background:'+heatColor(n)+(n>maxN*.5?';color:#fff':'')+';text-align:center;font-size:.68rem\">'+(n||'')+'</td>';
}});
h+='</tr>';
}});
h+='</tbody></table></div></div>';
document.getElementById("tab-heatmap").innerHTML=h;
}})();
(function(){{
var cs=P.candidates,h='';
if(!cs.length){{h+='<div class="panel"><p style="color:var(--muted)">[无候选] 运行 policyscout collect '+P.city+' '+P.province+'</p></div>'}}
else{{
h+='<div class="panel"><h2>采集候选 ('+(P.candidate_source||"")+')</h2>';
h+='<div class="alert alert-info">搜狗微信搜索结果（预筛选后）。需人工下载原文放入 intake 目录，再运行 V5 结构化。</div>';
h+='<div class="legend"><div class="legend-item"><span class="tag tag-green">PASS</span></div><div class="legend-item"><span class="tag tag-blue">LLM_PASS</span></div><div class="legend-item"><span class="tag tag-red">REJECT</span></div></div>';
h+='<div class="tbl-wrap"><table><thead><tr><th>#</th><th>标题</th><th>判</th><th>kw</th><th>??</th><th>??</th><th>??</th></tr></thead><tbody>';
cs.forEach(function(c,i){{
var vc=c.verdict==="PASS"?"tag-green":(c.verdict==="LLM_PASS"?"tag-blue":"tag-red");
h+='<tr><td>'+(i+1)+'</td><td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+c.title.replace(/"/g,"&quot;")+'">'+c.title.substring(0,80)+'</td><td><span class="tag '+vc+'">'+c.verdict+'</span></td><td>'+c.kw_score+'</td>';
h+='<td><a href="'+c.url+'" target="_blank" rel="noopener">&#x1F4F1; 微信</a></td>';
h+='<td>'+(c.pkulaw_link?'<a href="'+c.pkulaw_link+'" target="_blank" rel="noopener">&#x1F4DC; 法宝</a>':'-')+'</td>';
h+='<td>'+(c.flk_link?'<a href="'+c.flk_link+'" target="_blank" rel="noopener">&#x1F4DA; 法规库</a>':'-')+'</td>';
h+='</tr>';
}});
h+='</tbody></table></div></div>';
}}
document.getElementById("tab-candidates").innerHTML=h;
}})();
}})();
</script>
</body>
</html>'''


def save_dashboard(gap_data: dict, candidates: list[dict] = None, candidate_source: str = "", output_dir: Path = None) -> Path:
    """生成看板 HTML 并保存到文件。返回保存路径。"""
    if output_dir is None:
        output_dir = DASHBOARDS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    city = gap_data["city"].replace("/", "_").replace("\\", "_")
    html = build_dashboard_html(gap_data, candidates, candidate_source)
    outpath = output_dir / f"{city}_制度文本缺口看板.html"
    outpath.write_text(html, encoding="utf-8")
    return outpath
