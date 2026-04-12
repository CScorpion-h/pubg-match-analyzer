"""全局样式定义。"""

from __future__ import annotations

import streamlit as st


APP_FONT_FAMILY = '"Microsoft YaHei", sans-serif'
SIDEBAR_WIDTH_PX = 208


def apply_global_styles() -> None:
    """注入全局字体和侧边栏宽度样式。"""
    st.markdown(
        f"""
        <style>
        .stApp {{
            --app-font-family: {APP_FONT_FAMILY};
            --app-sidebar-width: {SIDEBAR_WIDTH_PX}px;
        }}

        .stApp [data-testid="stSidebar"] {{
            min-width: var(--app-sidebar-width) !important;
            max-width: var(--app-sidebar-width) !important;
        }}

        .stApp [data-testid="stSidebar"] > div:first-child {{
            width: var(--app-sidebar-width) !important;
        }}

        .stApp,
        .stApp :is(h1, h2, h3, h4, h5, h6, p, li, label, button, input, textarea, select),
        .stApp [data-testid="stMetricValue"],
        .stApp [data-testid="stMetricValue"] *,
        .stApp [data-testid="stMetricLabel"],
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stCode"],
        .stApp [data-testid="stCode"] *,
        .stApp [data-testid="stDataFrame"],
        .stApp [data-testid="stDataFrame"] *,
        .stApp [data-testid="stDataFrameResizable"],
        .stApp [data-testid="stDataFrameResizable"] * {{
            font-family: var(--app-font-family) !important;
            font-synthesis: none !important;
        }}

        .stApp [data-testid="stMetricValue"],
        .stApp [data-testid="stMetricValue"] *,
        .stApp [data-testid="stDataFrame"],
        .stApp [data-testid="stDataFrame"] *,
        .stApp [data-testid="stDataFrameResizable"],
        .stApp [data-testid="stDataFrameResizable"] * {{
            font-weight: 400 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


