# GGF-TWI 城市采集 Agent

中国政府引导基金政策文本制度缺口诊断与多源采集工具。

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env          # 编辑填入你的 DeepSeek API key
python -m ggf_agent.server    # 启动 → 浏览器打开 http://127.0.0.1:8765
```

在网页输入城市名和省份 → 自动搜索、预筛选、生成交互看板。

## 功能

- **多源采集** — 搜狗微信 + Bing gov.cn + 北大法宝 + 国家法规库
- **智能预筛选** — 规则快判 + LLM 边际分类器，剔除无关文本
- **缺口诊断** — 市级/区级制度文本覆盖分析，年份断层检测
- **交互看板** — 自包含 HTML，4 选项卡，双击即用

## 命令行

```bash
python -m ggf_agent.server              # 启动 Web 服务
python -m ggf_agent.collect 深圳市 广东省  # CLI 采集
```

## 安全

- 服务器仅监听 `127.0.0.1`（本机），外部网络不可达
- API key 在 `.env` 文件中，不上传 GitHub
- 无远程依赖，纯本地运行
