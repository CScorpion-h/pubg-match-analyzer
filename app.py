"""Streamlit 入口文件，负责全局初始化和页面导航。"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from pubg_match_analyzer.ui.styles import apply_global_styles
from pubg_match_analyzer.core.ui_state import ensure_session_state


BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pubg_match_analyzer" / "pages"


def build_navigation() -> st.navigation:
    """构建侧边栏导航，显式控制页面顺序和显示名称。"""
    return st.navigation(
        [
            st.Page(PAGES_DIR / "home.py", title="首页"),
            st.Page(PAGES_DIR / "01_match_detect.py", title="对局识别"),
            st.Page(PAGES_DIR / "02_match_list.py", title="对局列表"),
            st.Page(PAGES_DIR / "03_match_detail.py", title="对局详情"),
            st.Page(PAGES_DIR / "05_export_center.py", title="导出中心"),
            st.Page(PAGES_DIR / "06_system_settings.py", title="系统设置"),
        ],
        position="sidebar",
    )


st.set_page_config(
    page_title="PUBG 水友赛数据统计工具",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_session_state()
apply_global_styles()
build_navigation().run()


