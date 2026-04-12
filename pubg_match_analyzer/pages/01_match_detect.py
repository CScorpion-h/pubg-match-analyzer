"""对局识别页面。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.constants import MIN_HIT_PLAYER_COUNT
from pubg_match_analyzer.services.export_service import candidate_matches_df
from pubg_match_analyzer.services.match_detection import detect_candidate_matches
from pubg_match_analyzer.services.pubg_api import PubgAPIClient, PubgAPIError
from pubg_match_analyzer.ui.styles import apply_global_styles
from pubg_match_analyzer.core.ui_state import clear_loaded_match, ensure_session_state


ensure_session_state()
apply_global_styles()
st.title("对局识别")
st.caption("输入玩家昵称，读取最近对局，并筛选自定义房候选对局。")

st.text_area(
    "玩家昵称列表",
    key="detect_input_text",
    height=180,
    placeholder="每行一个昵称，例如：\nplayer_alpha\nplayer_bravo",
)

col1, col2 = st.columns(2)
with col1:
    st.number_input(
        "最近对局窗口",
        min_value=5,
        max_value=100,
        key="recent_match_limit",
    )
with col2:
    st.caption("当前固定规则")
    st.write(f"至少 {MIN_HIT_PLAYER_COUNT} 名输入玩家共同出现在同一局中。")

if st.button("识别候选对局", type="primary", use_container_width=True):
    player_names = [line.strip() for line in st.session_state.detect_input_text.splitlines() if line.strip()]
    try:
        client = PubgAPIClient(platform=st.session_state.platform, api_key=st.session_state.api_key)
        matches = detect_candidate_matches(
            client=client,
            player_names=player_names,
            recent_match_limit=int(st.session_state.recent_match_limit),
        )
    except (ValueError, PubgAPIError) as exc:
        st.error(str(exc))
    else:
        st.session_state.candidate_matches = matches
        clear_loaded_match()
        st.success(f"识别完成，共得到 {len(matches)} 个自定义房候选对局。")

matches = st.session_state.candidate_matches
hit_player_count = len({name for item in matches for name in item.hit_input_names})
col1, col2, col3, col4 = st.columns(4)
col1.metric("候选对局数", len(matches))
col2.metric("命中玩家数", hit_player_count)
col3.metric("平台", st.session_state.platform)
col4.metric("最近对局窗口", str(st.session_state.recent_match_limit))

if matches:
    st.dataframe(candidate_matches_df(matches), use_container_width=True, hide_index=True)
else:
    st.info("当前还没有候选对局。该功能需要有效的 API Key，因为玩家昵称查询依赖 players 接口。")


