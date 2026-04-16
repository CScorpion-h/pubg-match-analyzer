"""系统设置页面。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.constants import MAX_SEARCH_WINDOW_LIMIT
from pubg_match_analyzer.core.ui_state import LOCAL_SETTINGS_FILE, clear_local_settings, ensure_session_state
from pubg_match_analyzer.ui.styles import apply_global_styles


ensure_session_state()
apply_global_styles()

st.title("系统设置")
st.caption("当前页面只保留基础查询设置，改动会自动保存到本地。")

st.text_input(
    "PUBG API Key",
    key="api_key",
    type="password",
    help="对局识别中的玩家昵称查询依赖 players 接口，需要有效的 API Key。",
)

col1, col2 = st.columns(2)
with col1:
    st.text_input(
        "平台",
        key="platform",
        help="默认使用 steam，需要时也可填写 psn、xbox、tournament 等平台标识。",
    )
with col2:
    st.number_input(
        "默认最大搜索窗口",
        min_value=5,
        max_value=MAX_SEARCH_WINDOW_LIMIT,
        key="recent_match_limit",
        help="系统会自动选择 recent matches 总量最少的玩家作为锚点，并在该玩家的最近 N 局范围内查找共同对局。",
    )

st.caption(f"本地保存路径：`{LOCAL_SETTINGS_FILE}`")

if st.button("清除本地保存", use_container_width=True):
    clear_local_settings()
    st.info("本地保存已清除。当前会话中的值暂时保留，重启后不会再自动恢复。")

st.success("设置会自动保存到本地。重启 Streamlit 后会自动恢复。")
