"""
ggf_agent — 政府引导基金政策文本采集 Agent

全国制度文本缺口诊断 + 多源采集 + 交互 HTML 看板。

用法:
    from ggf_agent.collect import collect_city
    from ggf_agent.gap import build_city_gap
    from ggf_agent.server import start_server

或命令行:
    python -m ggf_agent.server          # 启动本地 Web 服务
    python -m ggf_agent.collect 某市 某省      # CLI 采集
"""
__version__ = "0.1.0"
