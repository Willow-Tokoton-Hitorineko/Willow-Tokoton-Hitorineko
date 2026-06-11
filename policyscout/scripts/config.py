# DEPRECATED — use policyscout package instead (from policyscout.xxx import ...)
"""采集 Agent 全局配置。

目录结构:
  agent/
  ├── scripts/         ← 采集代码
  ├── outputs/
  │   ├── candidates/  ← 各城市候选列表 (URL+标题+摘要+V5判定)
  │   ├── gap/         ← 全国缺口表
  │   └── dedup/       ← 全局去重
  └── data/
      └── pending/     ← 待下载原文（人工确认后拷贝至此）
"""
from __future__ import annotations

import os
from pathlib import Path

# ── 路径 ──
AGENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AGENT_ROOT.parent
SCRIPTS_DIR = AGENT_ROOT / "scripts"
OUTPUTS_DIR = AGENT_ROOT / "outputs"
CANDIDATES_DIR = OUTPUTS_DIR / "candidates"
GAP_DIR = OUTPUTS_DIR / "gap"
DEDUP_DIR = OUTPUTS_DIR / "dedup"
DATA_DIR = AGENT_ROOT / "data" / "pending"
MAIN_FLAT = Path(os.environ.get("MAIN_FLAT_PATH", AGENT_ROOT / "data" / "main_flat.csv"))

# ── API（优先环境变量）──
DS_API_KEY = os.environ.get("DS_API_KEY", "")
DS_API_BASE = os.environ.get("DS_API_BASE", "https://api.deepseek.com/v1")
DS_MODEL = os.environ.get("DS_MODEL", "deepseek-chat")

# ── 搜索速率限制（秒）──
SEARCH_DELAY = 2.0          # 每次搜索间隔
BATCH_DELAY = 5.0           # 每个城市间隔

# ── 制度文种 ──
INST_TYPES = [
    "管理办法", "实施细则", "实施意见", "指导意见",
    "实施办法", "暂行管理办法",
]

# ── 省级覆盖率分层标准 ──
L2_MIN_COVERAGE_PCT = 30
L2_MIN_CITIES = 5
GGF_TWI_MIN_INST = 3

# ── 检索模板 ──
SEARCH_TEMPLATES = {
    "sogou_primary": "{city} 引导基金 管理办法",
    "sogou_alt1": "{city} 产业投资基金 暂行办法",
    "sogou_alt2": "{city} 政府投资基金 管理",
    "pkulaw_link": "https://www.pkulaw.com/law?keyword={city} 引导基金 管理办法",
}

# ── 省级行政区 ──
PROVINCES = [
    "北京市", "天津市", "上海市", "重庆市",
    "河北省", "山西省", "辽宁省", "吉林省", "黑龙江省",
    "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省",
    "河南省", "湖北省", "湖南省", "广东省",
    "广西壮族自治区", "海南省",
    "四川省", "贵州省", "云南省",
    "西藏自治区",
    "陕西省", "甘肃省", "青海省",
    "宁夏回族自治区",
    "新疆维吾尔自治区",
    "内蒙古自治区",
]

MUNICIPALITIES = {"北京市", "天津市", "上海市", "重庆市"}

PREFECTURE_COUNTS = {
    "河北省": 11, "山西省": 11, "辽宁省": 14, "吉林省": 9, "黑龙江省": 13,
    "江苏省": 13, "浙江省": 11, "安徽省": 16, "福建省": 9, "江西省": 11,
    "山东省": 16, "河南省": 17, "湖北省": 13, "湖南省": 14, "广东省": 21,
    "广西壮族自治区": 14, "海南省": 4,
    "四川省": 21, "贵州省": 9, "云南省": 16,
    "西藏自治区": 7,
    "陕西省": 10, "甘肃省": 14, "青海省": 8,
    "宁夏回族自治区": 5,
    "新疆维吾尔自治区": 14,
    "内蒙古自治区": 12,
}
