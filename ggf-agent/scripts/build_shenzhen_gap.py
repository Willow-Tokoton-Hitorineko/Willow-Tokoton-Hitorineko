"""
深圳市级制度文本缺口诊断 + HTML看板生成

用法: python agent/scripts/build_shenzhen_gap.py
输出: agent/outputs/gap/深圳_制度文本缺口看板.html
"""

import json, base64, sys
from pathlib import Path
from datetime import datetime as dt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MAIN_FLAT = ROOT.parent / "阶段3_指数构建与验证/09_数据质量诊断_20260515/outputs/main8_flat_v6_20260605.csv"
OUTDIR = ROOT / "outputs/gap"
OUTDIR.mkdir(parents=True, exist_ok=True)

CORE8 = ["subfund_structure","allow_direct_investment","manager_selection_mode",
         "non_interference_clause","has_tolerance_mechanism","exit_mechanisms_specified",
         "supervision_rights_defined","has_performance_evaluation"]
CORE8_LABELS = ["母子基金结构","直投安排","管理人遴选","不干预经营","容错机制","退出机制","监督报送","绩效评价"]
M_FIELDS = CORE8[:4]; R_FIELDS = CORE8[4:6]; V_FIELDS = CORE8[6:8]

INST_TYPES = ['管理办法','暂行办法','暂行管理办法','实施细则','实施办法','实施意见',
              '指导意见','设立方案','方案','章程','条例','规定','措施','指引','操作规程']

def is_hit(v):
    return pd.notna(v) and str(v).strip() not in ('','0','no','0.0','False','None')

# ── Load data ──
df = pd.read_csv(MAIN_FLAT)
sz_all = df[df['city'] == '深圳市'].copy()
sz_inst = sz_all[(sz_all['doc_type'].isin(INST_TYPES)) & (sz_all['is_national'] == 0)].copy()

# ── Build text rows ──
def build_text_rows(data, label):
    rows = []
    for _, r in data.iterrows():
        hits = sum(1 for f in CORE8 if is_hit(r.get(f)))
        fields_detail = {}
        for f in CORE8:
            v = r.get(f)
            fields_detail[f] = {"value": str(v)[:40] if pd.notna(v) else "nan", "hit": is_hit(v)}
        issues = []
        if hits == 0 and r['year'] < 2012:
            issues.append("旧文本(≤2011)")
        if '税' in str(r.get('title','')) and '引导基金' not in str(r.get('title','')):
            issues.append("分类错误:非引导基金文本")
        rows.append({
            "source_id": int(r.get('source_id', 0)) if pd.notna(r.get('source_id')) else None,
            "title": str(r.get('title',''))[:200],
            "year": int(r['year']) if pd.notna(r.get('year')) else None,
            "doc_type": str(r.get('doc_type','')),
            "policy_level": str(r.get('policy_level','')),
            "hits": hits,
            "fields": fields_detail,
            "issues": issues,
            "label": label,
        })
    return rows

city_rows = build_text_rows(sz_inst[sz_inst['policy_level'] == '市级'], '市级')
district_rows = build_text_rows(sz_inst[sz_inst['policy_level'] == '区县级'], '区县级')

# ── Year timeline ──
def year_timeline():
    years = {}
    for _, r in sz_inst.iterrows():
        yr = int(r['year']) if pd.notna(r.get('year')) else None
        if yr is None: continue
        pl = str(r.get('policy_level',''))
        if yr not in years:
            years[yr] = {"市级": 0, "区县级": 0}
        years[yr][pl if pl in ("市级","区县级") else "区县级"] += 1
    return [{"year": y, **counts} for y, counts in sorted(years.items())]

# ── Load candidates if available ──
candidates = []
cand_file = None
cand_dir = ROOT / "outputs/candidates"
for p in sorted(cand_dir.glob("广东省_深圳市_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True):
    cand_file = str(p)
    break

if cand_file:
    cand_df = pd.read_csv(cand_file)
    for _, r in cand_df.iterrows():
        candidates.append({
            "title": str(r.get('title',''))[:200],
            "url": str(r.get('url','')),
            "pkulaw_link": str(r.get('pkulaw_link','')) if 'pkulaw_link' in cand_df.columns else '',
            "flk_link": str(r.get('flk_link','')) if 'flk_link' in cand_df.columns else '',
            "source": str(r.get('source','')),
            "kw_score": int(r.get('kw_score', 0)) if pd.notna(r.get('kw_score')) else 0,
            "verdict": str(r.get('verdict','')),
            "reason": str(r.get('reason','')),
            "snippet": str(r.get('snippet',''))[:300],
        })

# ── Build payload ──
payload = {
    "generated": dt.now().strftime("%Y-%m-%d %H:%M"),
    "summary": {
        "total_institutional": len(sz_inst),
        "city_level_n": len(city_rows),
        "district_n": len(district_rows),
        "city_level_pmi": 0.0,
        "district_pmi": 0.550,
        "year_range_city": f"{min(r['year'] for r in city_rows)}-{max(r['year'] for r in city_rows)}" if city_rows else "N/A",
        "year_range_district": f"{min(r['year'] for r in district_rows)}-{max(r['year'] for r in district_rows)}" if district_rows else "N/A",
        "gap_years": "2012-2026",
        "n_candidates": len(candidates),
    },
    "city_texts": city_rows,
    "district_texts": district_rows,
    "year_timeline": year_timeline(),
    "core8_fields": CORE8,
    "core8_labels": CORE8_LABELS,
    "candidates": candidates,
    "candidate_source": Path(cand_file).name if cand_file else None,
}

# ── Generate HTML ──
payload_json = json.dumps(payload, ensure_ascii=False)
payload_b64 = base64.b64encode(payload_json.encode('utf-8')).decode('ascii')

def _q(s):
    """Escape for JS string literal"""
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '')

HTML = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>深圳市 · 制度文本缺口看板</title>
<style>
:root {{
  --bg: #f5f5f7; --card: #ffffff; --text: #1d1d1f; --muted: #86868b;
  --border: #e5e5ea; --shadow-sm: 0 1px 2px rgba(0,0,0,.04);
  --shadow: 0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.06);
  --shadow-md: 0 4px 6px rgba(0,0,0,.04), 0 2px 4px rgba(0,0,0,.06);
  --shadow-lg: 0 10px 15px rgba(0,0,0,.04), 0 4px 6px rgba(0,0,0,.05);
  --blue: #0071e3; --blue-bg: #f0f7ff; --blue-border: #c2e0ff;
  --red: #e03a3a; --red-bg: #fff5f5; --red-border: #ffd4d4;
  --green: #30b55a; --green-bg: #f2fbf5; --green-border: #c6f0d4;
  --amber: #e09d00; --amber-bg: #fffcf0; --amber-border: #ffe8a0;
  --purple: #894dde; --purple-bg: #f8f5ff;
  --radius: 12px; --radius-sm: 8px;
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-mono: "SF Mono", "Cascadia Code", "Consolas", monospace;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.55; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }}

/* ── Header ── */
header {{
  background: #1d1d1f; color: #f5f5f7; padding: 1.75rem 2rem;
  box-shadow: 0 2px 20px rgba(0,0,0,.15); position: sticky; top: 0; z-index: 100;
}}
header h1 {{ font-size: 1.4rem; font-weight: 700; letter-spacing: -.02em; }}
header .sub {{ font-size: .8rem; color: #a1a1aa; margin-top: .3rem; font-weight: 400; }}
header .badge-row {{ display: flex; gap: .5rem; margin-top: .85rem; flex-wrap: wrap; }}
header .hdr-badge {{
  display: inline-flex; align-items: center; gap: .35rem;
  padding: .3rem .75rem; border-radius: 999px; font-size: .73rem; font-weight: 500;
  backdrop-filter: blur(8px); letter-spacing: .01em;
}}
.hdr-badge.warn {{ background: rgba(224,58,58,.18); color: #ff9999; }}
.hdr-badge.info {{ background: rgba(0,113,227,.18); color: #7eb8ff; }}
.hdr-badge.ok {{ background: rgba(48,181,90,.18); color: #7ee0a0; }}
.hdr-badge.neutral {{ background: rgba(255,255,255,.08); color: #c4c4cc; }}

/* ── Layout ── */
.wrap {{ max-width: 1340px; margin: 0 auto; padding: 2rem 2rem 3rem; }}
@media (max-width: 768px) {{ .wrap {{ padding: 1rem 1rem 2rem; }} }}

/* ── KPI Cards ── */
.kpi-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1rem;
  margin-bottom: 1.75rem;
}}
.kpi {{
  background: var(--card); border-radius: var(--radius); padding: 1.15rem 1.25rem;
  box-shadow: var(--shadow); border: 1px solid var(--border);
  transition: transform .2s cubic-bezier(.16,1,.3,1), box-shadow .2s cubic-bezier(.16,1,.3,1);
  position: relative; overflow: hidden;
}}
.kpi::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  border-radius: var(--radius) var(--radius) 0 0; transition: opacity .2s;
}}
.kpi.warn::before {{ background: var(--red); }}
.kpi.ok::before {{ background: var(--green); }}
.kpi.info::before {{ background: var(--blue); }}
.kpi.amber::before {{ background: var(--amber); }}
.kpi:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-lg); }}
.kpi .kpi-icon {{ font-size: 1.15rem; margin-bottom: .4rem; opacity: .85; }}
.kpi .kpi-label {{ font-size: .7rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }}
.kpi .kpi-value {{ font-size: 1.75rem; font-weight: 700; margin-top: .1rem; letter-spacing: -.02em; }}
.kpi .kpi-sub {{ font-size: .7rem; color: var(--muted); margin-top: .15rem; }}
.kpi.warn .kpi-value {{ color: var(--red); }}
.kpi.ok .kpi-value {{ color: var(--green); }}
.kpi.info .kpi-value {{ color: var(--blue); }}
.kpi.amber .kpi-value {{ color: var(--amber); }}

/* ── Tabs ── */
.tab-bar {{
  display: flex; gap: .2rem; margin-bottom: 1.5rem;
  background: var(--card); border-radius: var(--radius); padding: .3rem;
  box-shadow: var(--shadow); border: 1px solid var(--border);
}}
.tab-btn {{
  flex: 1; padding: .65rem 1rem; border: none; background: transparent;
  border-radius: 9px; cursor: pointer; font-size: .82rem; font-weight: 500;
  color: var(--muted); transition: all .2s cubic-bezier(.16,1,.3,1);
  font-family: var(--font); white-space: nowrap;
}}
.tab-btn:hover {{ background: #f0f0f5; color: var(--text); }}
.tab-btn.active {{
  background: #1d1d1f; color: #fff; font-weight: 600;
  box-shadow: 0 2px 8px rgba(0,0,0,.12);
}}

/* ── Panels ── */
.tab-pane {{ display: none; animation: fadeIn .3s cubic-bezier(.16,1,.3,1); }}
.tab-pane.active {{ display: block; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: translateY(0); }} }}
.panel {{
  background: var(--card); border-radius: var(--radius); padding: 1.25rem 1.5rem;
  box-shadow: var(--shadow); border: 1px solid var(--border); margin-bottom: 1rem;
}}
.panel h2 {{ font-size: .95rem; font-weight: 700; margin-bottom: .85rem; display: flex; align-items: center; gap: .5rem; letter-spacing: -.01em; }}

/* ── Alerts ── */
.alert {{ padding: .85rem 1.1rem; border-radius: var(--radius-sm); margin-bottom: 1rem; font-size: .8rem; line-height: 1.55; }}
.alert b {{ font-weight: 600; }}
.alert-danger {{ background: var(--red-bg); border: 1px solid var(--red-border); color: #991b1b; }}
.alert-danger b {{ color: #c41e1e; }}
.alert-info {{ background: var(--blue-bg); border: 1px solid var(--blue-border); color: #1e3a5f; }}
.alert-info b {{ color: #0058b0; }}
.alert-warn {{ background: var(--amber-bg); border: 1px solid var(--amber-border); color: #6b4d00; }}
.alert-warn b {{ color: #a06d00; }}

/* ── Tables ── */
.tbl-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: var(--radius-sm); border: 1px solid var(--border); }}
table {{ width: 100%; border-collapse: collapse; font-size: .76rem; min-width: 750px; }}
thead th {{
  background: #fafafa; font-weight: 600; padding: .6rem .55rem; text-align: left;
  border-bottom: 2px solid #eaeaef; position: sticky; top: 0; z-index: 1;
  font-size: .7rem; color: var(--muted); white-space: nowrap; letter-spacing: .02em;
}}
tbody td {{ padding: .5rem .55rem; border-bottom: 1px solid #f3f3f7; vertical-align: middle; }}
tbody tr:nth-child(even) {{ background: #fafafa; }}
tbody tr:hover {{ background: #f0f7ff; }}

/* ── Field badges ── */
.f-hit {{ display: inline-block; background: #dcfce7; color: #166534; padding: .14rem .45rem; border-radius: 5px; font-size: .68rem; font-weight: 600; letter-spacing: .01em; }}
.f-no {{ display: inline-block; background: #fee2e2; color: #991b1b; padding: .14rem .45rem; border-radius: 5px; font-size: .68rem; font-weight: 500; }}
.f-nan {{ display: inline-block; background: #f3f4f6; color: #9ca3af; padding: .14rem .45rem; border-radius: 5px; font-size: .68rem; font-style: italic; }}

/* ── Tags ── */
.tag {{ display: inline-block; padding: .12rem .5rem; border-radius: 5px; font-size: .68rem; font-weight: 600; letter-spacing: .01em; }}
.tag-red {{ background: #fee2e2; color: #991b1b; }}
.tag-green {{ background: #dcfce7; color: #166534; }}
.tag-amber {{ background: #fef3c7; color: #92400e; }}
.tag-blue {{ background: #dbeafe; color: #1e40af; }}
.tag-gray {{ background: #f3f4f6; color: #6b7280; }}

/* ── Timeline ── */
.tl-header {{ display: flex; align-items: center; padding: .3rem .5rem; font-size: .68rem; color: var(--muted); font-weight: 600; letter-spacing: .03em; }}
.tl-header .tl-yr {{ width: 50px; }}
.tl-header .tl-bar-wrap {{ flex: 1; }}
.timeline-row {{ display: flex; align-items: center; gap: .4rem; padding: .4rem .5rem; border-radius: 6px; margin: 1px 0; }}
.timeline-row:hover {{ background: #f5f5f9; }}
.timeline-row.gap {{ background: #fff5f5; border-left: 2px solid var(--red); }}
.tl-yr {{ font-weight: 600; width: 50px; font-size: .8rem; font-family: var(--font-mono); }}
.tl-bar-wrap {{ flex: 1; height: 18px; background: #f3f4f6; border-radius: 9px; overflow: hidden; display: flex; gap: 1px; }}
.tl-bar-city {{ background: linear-gradient(90deg, #e03a3a, #f06060); height: 100%; transition: width .4s cubic-bezier(.16,1,.3,1); min-width: 3px; }}
.tl-bar-dist {{ background: linear-gradient(90deg, #0071e3, #339af0); height: 100%; transition: width .4s cubic-bezier(.16,1,.3,1); min-width: 3px; }}
.tl-n {{ font-size: .7rem; color: var(--muted); min-width: 90px; text-align: right; font-family: var(--font-mono); }}

/* ── Legend ── */
.legend {{ display: flex; gap: 1.25rem; flex-wrap: wrap; font-size: .73rem; margin: .6rem 0 .5rem; }}
.legend-item {{ display: flex; align-items: center; gap: .35rem; }}
.legend-swatch {{ width: 14px; height: 14px; border-radius: 4px; }}

/* ── Links ── */
a {{ color: var(--blue); text-decoration: none; font-weight: 500; transition: color .15s; }}
a:hover {{ color: #0058b0; text-decoration: underline; }}

/* ── Section title ── */
.section-title {{
  font-size: .9rem; font-weight: 700; color: #374151; margin: 1rem 0 .75rem;
  padding-bottom: .5rem; border-bottom: 2px solid #eaeaef;
  display: flex; align-items: center; gap: .5rem; letter-spacing: -.01em;
}}

/* ── Empty state ── */
.empty-state {{ text-align: center; padding: 3rem 1rem; color: var(--muted); }}
.empty-state .icon {{ font-size: 2.5rem; margin-bottom: .75rem; opacity: .5; }}

/* ── Responsive ── */
@media (max-width: 768px) {{
  header {{ padding: 1.25rem 1rem; }}
  header h1 {{ font-size: 1.15rem; }}
  .kpi-grid {{ grid-template-columns: repeat(2, 1fr); gap: .6rem; }}
  .kpi {{ padding: .85rem 1rem; }}
  .kpi .kpi-value {{ font-size: 1.35rem; }}
  .tab-btn {{ font-size: .72rem; padding: .5rem .55rem; }}
  .panel {{ padding: 1rem; }}
  .tl-n {{ display: none; }}
}}

@media (max-width: 480px) {{
  .kpi-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<header>
  <h1>深圳市 · 制度文本缺口看板</h1>
  <div class="sub">生成于 {payload['generated']} · 数据源 main8_flat_v6_20260605.csv · 3316条</div>
  <div class="badge-row">
    <span class="hdr-badge warn">市级断层 2012-2026</span>
    <span class="hdr-badge info">城市本级 PMI = 0.000</span>
    <span class="hdr-badge ok">区级 PMI = 0.550</span>
    <span class="hdr-badge info">采集候选 {payload['summary']['n_candidates']} 条</span>
  </div>
</header>

<div class="wrap">

<!-- KPI Cards -->
<div class="kpi-grid">
  <div class="kpi warn">
    <div class="kpi-icon">&#9888;</div>
    <div class="kpi-label">市级制度文本</div>
    <div class="kpi-value">{payload['summary']['city_level_n']} 条</div>
    <div class="kpi-sub">{payload['summary']['year_range_city']}</div>
  </div>
  <div class="kpi ok">
    <div class="kpi-icon">&#10004;</div>
    <div class="kpi-label">区级制度文本</div>
    <div class="kpi-value">{payload['summary']['district_n']} 条</div>
    <div class="kpi-sub">{payload['summary']['year_range_district']}</div>
  </div>
  <div class="kpi warn">
    <div class="kpi-icon">&#9679;</div>
    <div class="kpi-label">城市本级 PMI</div>
    <div class="kpi-value">0.000</div>
    <div class="kpi-sub">8字段全零/nan</div>
  </div>
  <div class="kpi ok">
    <div class="kpi-icon">&#9650;</div>
    <div class="kpi-label">区级 PMI</div>
    <div class="kpi-value">0.550</div>
    <div class="kpi-sub">前海/南山/坪山/宝安</div>
  </div>
  <div class="kpi amber">
    <div class="kpi-icon">&#8987;</div>
    <div class="kpi-label">市级断层</div>
    <div class="kpi-value">{payload['summary']['gap_years']}</div>
    <div class="kpi-sub">无制度文本入库</div>
  </div>
  <div class="kpi info">
    <div class="kpi-icon">&#128269;</div>
    <div class="kpi-label">采集候选</div>
    <div class="kpi-value">{payload['summary']['n_candidates']} 条</div>
    <div class="kpi-sub">搜狗微信搜索</div>
  </div>
</div>

<!-- Tab Bar -->
<div class="tab-bar" id="tabBar">
  <button class="tab-btn active" data-tab="city">&#128218; 市级文本（{payload['summary']['city_level_n']}条）</button>
  <button class="tab-btn" data-tab="district">&#127970; 区级文本（{payload['summary']['district_n']}条）</button>
  <button class="tab-btn" data-tab="timeline">&#128200; 时间线</button>
  <button class="tab-btn" data-tab="candidates">&#128269; 采集候选（{payload['summary']['n_candidates']}条）</button>
</div>

<!-- Tab Panes -->
<div id="tab-city" class="tab-pane active"></div>
<div id="tab-district" class="tab-pane"></div>
<div id="tab-timeline" class="tab-pane"></div>
<div id="tab-candidates" class="tab-pane"></div>

</div><!-- /.wrap -->

<script>
(function() {{
  // ── Decode payload ──
  var P = {payload_json};

  // ── Tab switching (proper event delegation) ──
  document.getElementById('tabBar').addEventListener('click', function(e) {{
    var btn = e.target.closest('.tab-btn');
    if (!btn) return;
    var name = btn.getAttribute('data-tab');
    document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
    document.querySelectorAll('.tab-pane').forEach(function(p) {{ p.classList.remove('active'); }});
    btn.classList.add('active');
    document.getElementById('tab-' + name).classList.add('active');
  }});

  // ── Render helpers ──
  function fieldCell(detail) {{
    if (!detail) return '<span class="f-nan">-</span>';
    if (detail.hit) return '<span class="f-hit">' + detail.value + '</span>';
    if (detail.value === 'nan') return '<span class="f-nan">nan</span>';
    return '<span class="f-no">' + detail.value + '</span>';
  }}

  function issueTags(issues) {{
    if (!issues.length) return '<span class="tag tag-gray">-</span>';
    return issues.map(function(i) {{
      var cls = i.indexOf('分类错误') >= 0 ? 'tag-red' : 'tag-amber';
      return '<span class="tag ' + cls + '">' + i + '</span>';
    }}).join(' ');
  }}

  function renderTextTable(texts, fields, labels) {{
    if (!texts.length) return '<div class="panel"><p style="color:var(--muted)">无数据</p></div>';
    var h = '<div class="panel"><div class="tbl-wrap"><table><thead><tr>';
    h += '<th>ID</th><th>标题</th><th>年</th><th>文种</th><th>命中</th>';
    for (var fi = 0; fi < fields.length; fi++) h += '<th title="' + fields[fi] + '">' + labels[fi] + '</th>';
    h += '<th>标注</th></tr></thead><tbody>';
    texts.forEach(function(r) {{
      h += '<tr>';
      h += '<td>' + (r.source_id || '-') + '</td>';
      h += '<td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + r.title.replace(/"/g,'&quot;') + '">' + r.title.substring(0, 70) + '</td>';
      h += '<td>' + (r.year || '-') + '</td>';
      h += '<td>' + r.doc_type + '</td>';
      h += '<td><b>' + r.hits + '/8</b></td>';
      for (var fi = 0; fi < fields.length; fi++) h += '<td>' + fieldCell(r.fields[fields[fi]]) + '</td>';
      h += '<td>' + issueTags(r.issues) + '</td>';
      h += '</tr>';
    }});
    h += '</tbody></table></div></div>';
    return h;
  }}

  var fields = P.core8_fields;
  var labels = P.core8_labels;

  // ── Tab: City-level ──
  (function() {{
    var h = '';
    h += '<div class="alert alert-danger"><b>严重缺口</b>：深圳仅3条市级制度文本入库，全部来自2003-2011年。<b>2012-2026年完全空白</b>——《深圳市政府投资引导基金管理办法》《深圳市天使投资引导基金管理办法》等关键文件均缺失。</div>';
    h += '<div class="alert alert-info"><b>数据质量问题</b>：source_id=1485 是深圳市地税局转发的《股息红利个人所得税征收管理办法》，非引导基金文本，被V2.5错误标为 doc_type=管理办法。source_id=1476/1477 为2010-2011年早期政策，LLM编码为全部no/nan，可能反映了早期文本确实缺乏市场化条款。</div>';
    h += renderTextTable(P.city_texts, fields, labels);
    document.getElementById('tab-city').innerHTML = h;
  }})();

  // ── Tab: District-level ──
  (function() {{
    var h = '';
    h += '<div class="alert alert-info"><b>区级是深圳制度创新的主战场</b>：7条区级制度文本覆盖2016-2024年，前海(4条)、南山(1条7/8命中)、坪山(1条7/8命中)、宝安(1条5/8命中)。市级 <b>vs</b> 区级 PMI 两端极化（0.000 vs 0.550），分离后才看清深圳的制度写出完全由区级驱动。</div>';
    h += renderTextTable(P.district_texts, fields, labels);
    document.getElementById('tab-district').innerHTML = h;
  }})();

  // ── Tab: Timeline ──
  (function() {{
    var tl = P.year_timeline;
    var maxCount = 0;
    tl.forEach(function(y) {{ maxCount = Math.max(maxCount, y['市级'] + y['区县级']); }});

    var h = '<div class="panel"><h2>&#128200; 深圳市 制度文本年份分布</h2>';
    h += '<div class="legend"><div class="legend-item"><div class="legend-swatch" style="background:var(--red)"></div>市级</div><div class="legend-item"><div class="legend-swatch" style="background:var(--blue)"></div>区县级</div><div class="legend-item" style="color:var(--muted)">| 橙色底 = 市级断层年份</div></div>';

    tl.forEach(function(y) {{
      var total = y['市级'] + y['区县级'];
      var gapClass = (y.year >= 2012 && y['市级'] === 0) ? ' gap' : '';
      var cityW = maxCount > 0 ? (y['市级'] / maxCount * 100) : 0;
      var distW = maxCount > 0 ? (y['区县级'] / maxCount * 100) : 0;
      h += '<div class="timeline-row' + gapClass + '">';
      h += '<span class="tl-yr">' + y.year + '</span>';
      h += '<div class="tl-bar-wrap">';
      if (cityW > 0) h += '<div class="tl-bar-city" style="width:' + cityW + '%" title="市级:' + y['市级'] + '"></div>';
      if (distW > 0) h += '<div class="tl-bar-dist" style="width:' + distW + '%" title="区级:' + y['区县级'] + '"></div>';
      h += '</div>';
      h += '<span class="tl-n">市级' + y['市级'] + ' 区级' + y['区县级'] + '</span>';
      h += '</div>';
    }});

    h += '<div class="alert alert-warn" style="margin-top:1rem">2012-2026年深圳市级制度文本完全空白。同期区级文本7条（2016-2024），市级与区级的制度文本时间序列完全脱节——市级停留在2011年前的老旧框架，区级在2015年后迎来制度爆发。</div>';
    h += '</div>';
    document.getElementById('tab-timeline').innerHTML = h;
  }})();

  // ── Tab: Candidates ──
  (function() {{
    var cands = P.candidates;
    var h = '';
    if (!cands.length) {{
      h += '<div class="panel"><p style="color:var(--muted)">暂无采集候选。运行: python agent/scripts/collect_city.py 深圳市 广东省</p></div>';
    }} else {{
      h += '<div class="panel"><h2>&#128269; 采集候选列表</h2>';
      h += '<p style="font-size:.78rem;color:var(--muted);margin-bottom:.75rem">来源: ' + (P.candidate_source || '-') + ' · 搜狗微信 + 北大法宝 + 国家法规库</p>';
      h += '<div class="legend"><div class="legend-item"><span class="tag tag-green">PASS</span> 规则快判通过</div><div class="legend-item"><span class="tag tag-blue">LLM_PASS</span> LLM分类通过</div><div class="legend-item"><span class="tag tag-red">REJECT</span> 已拒绝/去重</div><div class="legend-item" style="font-size:.68rem;color:var(--muted)">| 搜狗=浏览器打开 | 法宝/法规库=永久稳定</div></div>';

      h += '<div class="tbl-wrap"><table><thead><tr><th>#</th><th>标题</th><th>判决</th><th>原因</th><th>kw</th><th>搜狗微信</th><th>北大法宝</th><th>法规库</th></tr></thead><tbody>';
      cands.forEach(function(c, i) {{
        var vCls = c.verdict === 'PASS' ? 'tag-green' : (c.verdict === 'LLM_PASS' ? 'tag-blue' : 'tag-red');
        h += '<tr>';
        h += '<td>' + (i + 1) + '</td>';
        h += '<td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + c.title.replace(/"/g, '&quot;') + '">' + c.title.substring(0, 80) + '</td>';
        h += '<td><span class="tag ' + vCls + '">' + c.verdict + '</span></td>';
        h += '<td style="font-size:.72rem">' + c.reason + '</td>';
        h += '<td>' + c.kw_score + '</td>';
        h += '<td><a href="' + c.url + '" target="_blank" rel="noopener" title="浏览器打开微信文章">微信</a></td>';
        h += '<td>' + (c.pkulaw_link ? '<a href="' + c.pkulaw_link + '" target="_blank" rel="noopener" title="北大法宝检索">法宝</a>' : '-') + '</td>';
        h += '<td>' + (c.flk_link ? '<a href="' + c.flk_link + '" target="_blank" rel="noopener" title="国家法规库检索">法规库</a>' : '-') + '</td>';
        h += '</tr>';
      }});
      h += '</tbody></table></div></div>';
    }}
    document.getElementById('tab-candidates').innerHTML = h;
  }})();

}})();
</script>
</body>
</html>'''

outpath = OUTDIR / "深圳_制度文本缺口看板.html"
outpath.write_text(HTML, encoding='utf-8')
print(f"OK: {outpath} ({len(HTML)} bytes)")

# ── Diagnosis summary ──
P = payload['summary']
print(f"\n深圳制度文本缺口诊断")
print(f"  市级: {P['city_level_n']}条 ({P['year_range_city']}), PMI={P['city_level_pmi']}")
print(f"  区级: {P['district_n']}条 ({P['year_range_district']}), PMI={P['district_pmi']}")
print(f"  断层: {P['gap_years']} 市级空白")
print(f"  候选: {P['n_candidates']}条")
print(f"\n  市级3条: source_id=1485(税务文件误标) / 1476 / 1477")
print(f"  区级7条: 前海x4(2016-2023) + 南山x1(2024) + 坪山x1(2018) + 宝安x1(2018)")
