# CLAUDE.md — 猫窝（Willow-Tokoton-Hitorineko Profile Repo）

## 仓库性质

这是 GitHub Profile 仓库，不是独立项目。已开源的项目作为子目录存放在这里。

- **主人**: 戆北在coding（Willow / 猫猫 / 小蔡）
- **人设**: 想学代码魔法的艾莉丝党 · 野猫 · vibe coding
- **在读**: 硕升专（ひきこもり大学 · シャリア）
- **课题**: 政府引导基金（剑术）+ Python 初修（魔法）

## 已上传项目

### 1. debut-wechat-article-crawler（处女作）
微信公众号爬虫 + 引导基金政策数据处理。Playwright 浏览器自动化抓取，本地 JSON 存储，可选 MySQL 入库。
**状态**: 公开归档 · vibe coding 产物 · Fork 跑通率约 50%
**技术栈**: Python + Playwright + MySQL + 硅基流动 API
**关键文件**: `debut-wechat-article-crawler/crawler/combined_crawler.py`（主爬虫 4600+ 行）
**注意**: 微信页面常改，不保证现在能一键跑通；公开仓不带真实爬取正文

### 2. finddr-fincmini-pipeline（FINDDR 参赛）
ACM ICAIF 2025 FinDDR 赛事存档 · **Test Set Rank #12**（队名 DeepSeek Your Report / 模型 FinCMini Agent 财小析）
**状态**: 已归档 · 规则库 + Pipeline 文档 + 部分输出样例
**关键路径**:
- `finddr-fincmini-pipeline/pipeline/README_3.6.md` — Pipeline 3.6 入口
- `finddr-fincmini-pipeline/pipeline/地区规范/` — 8 地区完整规范（核心）
- `finddr-fincmini-pipeline/docs/contribution.md` — 个人贡献说明
- `finddr-fincmini-pipeline/docs/project-summary.md` — 项目摘要
- `finddr-fincmini-pipeline/docs/competition-context.md` — 赛制背景
- `finddr-fincmini-pipeline/docs/leaderboard-test-set-final.png` — 测试集最终榜单截图

**不在本仓**: 原始年报（版权+体积）、API Key、队内私信、参赛证明

### 3. policyscout（采集 Agent — 最新）
政府引导基金制度文本缺口诊断与多源采集工具（硕士课题用）。
**状态**: 活跃开发中 · 首个正经 Python package
**关键路径**:
- `policyscout/policyscout/server.py` — Web 服务入口（`python -m policyscout.server`）
- `policyscout/policyscout/collect.py` — 采集编排器
- `policyscout/policyscout/gap.py` — 单城市制度文本缺口诊断
- `policyscout/policyscout/dashboard.py` — HTML 看板生成引擎
- `policyscout/policyscout/prescreen.py` — 规则 + LLM 两级预筛选
- `policyscout/policyscout/config.py` — 全局配置（含数据路径、API 设置、省份列表）
- `policyscout/scripts/` — 已弃用的独立脚本（仅供参考，建议用 policyscout package）

**功能**:
1. 搜狗微信搜索 → V5 预筛选（规则快判 + DeepSeek LLM 二分类）
2. 与已有数据库 + intake 目录智能去重
3. 单城市制度文本缺口诊断（市/区/省三级覆盖 + 年份断层检测 + 热力图 + 时间线）
4. 自包含 HTML 交互看板（4 选项卡，双击即用）
5. 本地 Web 界面（127.0.0.1:8765 + SSE 进度推送）

**依赖**: Python 3.10+ · pandas · requests · beautifulsoup4 · openai · 需要主数据库 CSV（`main_flat`）

## 本地研发环境

原始研究数据在 `D:/科研/GVC课题/` 下，不在此仓库内：
- 主数据库: `阶段3_指数构建与验证/09_数据质量诊断_20260515/outputs/main8_flat_v6_20260605.csv`
- 增量采集: `阶段1_权威数据与主库/03_待结构化增量采集_20260526/data/`

## 仓库约定

### 风格
- README 用猫窝风：居中 header + badges + 猫爪分隔线 + 回链到猫窝
- 中文为主，可夹日语（にゃ/desu）、猫相关 ASCII art
- Badge 颜色：主色 `#F97316`（橙）、Python `#3776AB`（蓝）、暗色 `#181717`

### 安全红线（上传前必须检查）
1. **绝不提交真实 API key** — `.env` 在 `.gitignore`；config 中用 `os.environ.get("VAR", "")`，fallback 必须是空字符串
2. **绝不提交真实研究数据** — `outputs/` 必须在 `.gitignore`；测试用例中的地名/标题必须用明显虚构的（"某市"、"某省"）
3. **绝不提交 `__pycache__/`、`*.pyc`** — `.gitignore` 覆盖
4. **公开行政区划列表是 OK 的**（中国省份名录 = 公共知识，非研究数据）

### Commit 风格
- 参考历史: `add: policyscout — 引导基金制度文本缺口诊断与多源采集工具`
- 格式: `type: short description — extended context`
- Type: `add` / `docs` / `fix` / `chore`

### 项目 README 必备元素
- `<div align="center">` 包裹的 header（项目名 + 一句话描述 + badges + 猫窝回链）
- `🐾 ─────────── 🐱 ─────────── 🐾` 分隔线
- "这是什么" + "能干什么" + 目录树 + 安装/运行 + 仓库范围表格 + 说明
- 诚实说明局限性（处女座有屎山预警，policyscout 有"需要自备数据"前提）

## 当前进度（2026-06）

- **剑术（课题）**: 引导基金 PMI 指数构建中，已完成 V6 flat 表 + 全国覆盖缺口诊断
- **policyscout**: 刚上传至猫窝，核心功能可用。后续：北大法宝付费 API 对接、Bing 命中率改善、批量城市编排
- **魔法（Python）**: 蟒語術初修，已能写 package + Web server + SSE
- **FINDDR**: 赛事已完成，名次 #12，规则库归档完毕
- **处女作**: 已归档，不打算更新

## 工具偏好

- **AI IDE**: Cursor
- **Python 环境**: Python 3.11（Windows）
- **数据库**: MySQL（课题用）
- **LLM API**: DeepSeek（主要）、硅基流动（旧项目）
- **Git**: GitHub Desktop（GUI）+ CLI
