"""policyscout 全局配置。路径感知包结构。"""
from __future__ import annotations

import os
from pathlib import Path

# ── 包根 ──
PKG_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PKG_ROOT.parent

# ── 输出 ──
OUTPUTS_DIR = PKG_ROOT / "outputs"
CANDIDATES_DIR = OUTPUTS_DIR / "candidates"
GAP_DIR = OUTPUTS_DIR / "gap"
DASHBOARDS_DIR = OUTPUTS_DIR / "dashboards"
DEDUP_DIR = OUTPUTS_DIR / "dedup"

# ── 主数据（可通过环境变量覆盖）──
MAIN_FLAT = Path(os.environ.get("MAIN_FLAT_PATH", PKG_ROOT / "data" / "main_flat.csv"))

# ── API（优先环境变量，回退默认值）──
DS_API_KEY = os.environ.get("DS_API_KEY", "")
DS_API_BASE = os.environ.get("DS_API_BASE", "https://api.deepseek.com/v1")
DS_MODEL = os.environ.get("DS_MODEL", "deepseek-chat")

# ── 速率 ──
SEARCH_DELAY = 1.0          # 搜狗间隔（秒）
BATCH_DELAY = 3.0

# ── 来源开关 ──
ENABLE_BING = False         # Bing gov.cn 命中率极低，默认关闭
ENABLE_PKULAW = False       # 北大法宝需付费登录，默认关闭（可配置 PKULAW_USER/PKULAW_PASS 开启）

# ── 本地数据路径（可通过环境变量 INTAKE_DIR 覆盖）──
INTAKE_DATA_DIR = Path(os.environ.get("INTAKE_DIR", PKG_ROOT / "data" / "intake"))

# ── 制度文种（14 类，与 V5 + phase1 一致）──
INST_TYPES = [
    "管理办法", "暂行办法", "暂行管理办法", "实施细则", "实施办法",
    "实施意见", "指导意见", "设立方案", "方案", "章程", "条例",
    "规定", "措施", "指引", "操作规程",
]

# ── CORE8 指标 ──
CORE8 = [
    "subfund_structure", "allow_direct_investment", "manager_selection_mode",
    "non_interference_clause", "has_tolerance_mechanism", "exit_mechanisms_specified",
    "supervision_rights_defined", "has_performance_evaluation",
]
CORE8_LABELS = [
    "母子基金", "直投安排", "管理人遴选", "不干预经营",
    "容错机制", "退出机制", "监督报送", "绩效评价",
]

# ── 省级 ──
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

# ── P0 缺口省份（覆盖率<30% 且 <5城）──
P0_PROVINCES = ["新疆维吾尔自治区", "西藏自治区", "吉林省", "云南省", "青海省"]

# ── 检索模板 ──
SEARCH_TEMPLATES = [
    "{city} 引导基金 管理办法",
    "{city} 产业投资基金 暂行办法",
    "{city} 政府投资基金 管理",
]
