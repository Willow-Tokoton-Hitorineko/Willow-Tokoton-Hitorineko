<div align="center">

<h1>ggf-agent</h1>

<b>政府引导基金 · 制度文本缺口诊断与多源采集</b><br/>
硕士课题用 · 替代人工逐市检索制度文本的体力活

<br/>

<img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/搜狗微信-采集-F97316?style=flat-square" alt="搜狗微信" />
<img src="https://img.shields.io/badge/DeepSeek-LLM分类-4B6BFB?style=flat-square" alt="DeepSeek" />
<img src="https://img.shields.io/badge/License-MIT-181717?style=flat-square" alt="MIT" />

<br/><br/>

<a href="https://github.com/Willow-Tokoton-Hitorineko/Willow-Tokoton-Hitorineko">← 戆北在coding の猫窝</a>

</div>

<p align="center">🐾 ─────────── 🐱 ─────────── 🐾</p>

## 这是什么

硕士课题里第 3 套工具——**不再写一次性脚本了，这次是正经的 Python package。**

做的是政府引导基金制度文本的**缺口诊断 + 多源检索**。给定一个城市名，自动搜微信公众号里的政策文章 → 预筛选剔除无关内容 → 和已有数据库比对去重 → 生成一份可以双击打开的 HTML 交互看板。

研究过程中需要逐城市排查"这个市有没有出台引导基金管理办法、是哪一年的、缺不缺制度文本"，纯手工逐个城市搜索很慢。这个 Agent 把这套流程自动化了。

<sub>🔧 课题探索中的工作流工具 · 不是成品 SaaS</sub>

<p align="center">🐾 ─────────── 🐱 ─────────── 🐾</p>

## 能干什么

| | |
|:--|:--|
| **缺口诊断** | 对单城市做制度文本覆盖分析：市级/区级/省级各有多少条、年份分布、断层检测 |
| **多源采集** | 搜狗微信搜索（主力）→ 含 Bing gov.cn 和北大法宝入口（默认关闭，见下方说明） |
| **智能预筛选** | 规则快判（关键词匹配）+ LLM 边际分类器（DeepSeek），两级过滤无关文本 |
| **智能去重** | 《》内政策名称 vs 已有数据库 + intake 目录，避免重复入库 |
| **交互看板** | 自包含 HTML，4 选项卡（市级/区级/时间线/采集候选），双击即用，无需服务器 |
| **Web 界面** | 本地 HTTP + SSE 进度推送，输入城市名 → 实时看进度 → 下载结果 |

<p align="center">🐾 ─────────── 🐱 ─────────── 🐾</p>

## 目录

```
ggf_agent/                主包
├── server.py             Web 服务（localhost:8765）
├── collect.py            采集编排（搜索→筛选→去重→保存）
├── gap.py                单城市制度文本缺口诊断
├── dashboard.py          HTML 看板生成引擎
├── prescreen.py          预筛选（规则 + LLM 二分类）
├── dedup.py              全局去重引擎
├── search_sogou.py       搜狗微信搜索适配器
├── search_bing.py        Bing gov.cn 适配器（默认关闭）
├── config.py             全局配置
└── templates/
    └── index.html        Web 界面
scripts/                  已弃用的独立脚本（仅供参考）
    ├── collect_city.py   旧版单城市采集
    ├── pre_screen.py     旧版预筛选
    ├── dedup.py          旧版去重
    ├── search_sogou.py   旧版搜狗搜索
    ├── search_bing.py    旧版 Bing 搜索
    └── build_national_gap_table.py  全国缺口表生成
```

<p align="center">🐾 ─────────── 🐱 ─────────── 🐾</p>

## 环境

**Python 3.10+** · 无需数据库 · 纯本地运行 · LLM 预筛选需要 DeepSeek API key

```bash
git clone https://github.com/Willow-Tokoton-Hitorineko/Willow-Tokoton-Hitorineko.git
cd Willow-Tokoton-Hitorineko/ggf-agent
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`，填入 DeepSeek API key（仅 LLM 预筛选需要；不填也能跑规则快判）。

<p align="center">🐾 ─────────── 🐱 ─────────── 🐾</p>

## 怎么跑

```bash
# Web 界面（推荐）→ 浏览器打开 http://127.0.0.1:8765
python -m ggf_agent.server

# CLI 采集
python -m ggf_agent.collect 某市 某省
python -m ggf_agent.collect 某市 某省 --no-llm   # 仅规则快判，不调 API
```

**功能前提：** 需要已有数据库文件（`main_flat` CSV），路径见 `ggf_agent/config.py` 中的 `MAIN_FLAT`。没有这个文件的话，缺口诊断和去重比对无法工作——这工具做的是**增量采集**，不是从零建库。

<p align="center">🐾 ─────────── 🐱 ─────────── 🐾</p>

## 当前检索来源

| 来源 | 状态 | 说明 |
|:--|:--:|:--|
| 搜狗微信 | 主力 | 微信公众号文章检索，无需 API key，HTML 抓取 |
| Bing gov.cn | 默认关闭 | 命中率很低；`ENABLE_BING=True` 可开启 |
| 北大法宝 | 默认关闭 | 需付费登录；配 `PKULAW_USER` / `PKULAW_PASS` 开启 |

搜狗微信返回的是**文章链接**——需要手动打开下载原文，放入 intake 目录后再跑 V5 结构化入库。这一步目前是人工的。

另外，搜狗微信页面 HTML 结构偶尔会变，如果哪天搜不到结果了就是这个原因。

<p align="center">🐾 ─────────── 🐱 ─────────── 🐾</p>

## 仓库范围

| 在本仓 | 不在本仓 |
|:--|:--|
| Agent 代码（搜索/筛选/去重/缺口诊断/看板） | 主数据库 CSV（`main_flat`） |
| Web 界面 + 模板 | API key（`.env`） |
| 输出目录结构（gitignore 保留空目录） | 采集结果、缓存、看板产出（`outputs/`） |
| `.env.example` 模板 | 北大法宝付费账号 |

<p align="center">🐾 ─────────── 🐱 ─────────── 🐾</p>

## 说明

- 仅用于课题研究、个人学习；遵守微信公众号平台规则
- 搜狗微信抓取依赖页面结构，不保证长期可用
- `scripts/` 目录已弃用，保留供参考；建议使用 `ggf_agent` package
- MIT → [开源许可证](LICENSE)

<p align="center"><sub>🐱 <a href="https://github.com/Willow-Tokoton-Hitorineko/Willow-Tokoton-Hitorineko">戆北在coding の猫窝</a> · 欢迎 Issue</sub></p>
