"""对局识别页面。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.constants import MAX_SEARCH_WINDOW_LIMIT, MIN_HIT_PLAYER_COUNT
from pubg_match_analyzer.core.ui_state import clear_loaded_match, ensure_session_state, merge_candidate_match_pool
from pubg_match_analyzer.services.export_service import candidate_matches_df
from pubg_match_analyzer.services.match_detection import detect_candidate_matches
from pubg_match_analyzer.services.pubg_api import PubgAPIClient, PubgAPIError
from pubg_match_analyzer.ui.components import render_empty_state, render_page_header
from pubg_match_analyzer.ui.styles import apply_global_styles


ensure_session_state()
apply_global_styles()
render_page_header(
    "对局识别",
    "输入玩家昵称，系统会自动选择 recent matches 总量最少的玩家作为锚点，并在最大搜索窗口内识别共同出现的自定义房。",
)

st.text_area(
    "玩家昵称列表",
    key="detect_input_text",
    height=180,
    placeholder="每行一个昵称，例如：\nplayer_alpha\nplayer_bravo",
)

col1, col2 = st.columns(2)
with col1:
    st.number_input(
        "最大搜索窗口",
        min_value=5,
        max_value=MAX_SEARCH_WINDOW_LIMIT,
        key="recent_match_limit",
        help="系统会自动选择 recent matches 总量最少的玩家作为锚点，并在该玩家的最近 N 局范围内查找共同对局。",
    )
with col2:
    st.metric("命中规则", f"至少 {MIN_HIT_PLAYER_COUNT} 人")

if st.button("识别候选对局", type="primary", use_container_width=True):
    player_names = [line.strip() for line in st.session_state.detect_input_text.splitlines() if line.strip()]
    try:
        client = PubgAPIClient(platform=st.session_state.platform, api_key=st.session_state.api_key)
        matches, anchor_name = detect_candidate_matches(
            client=client,
            player_names=player_names,
            recent_match_limit=int(st.session_state.recent_match_limit),
        )
    except (ValueError, PubgAPIError) as exc:
        st.error(str(exc))
    else:
        st.session_state.candidate_matches = matches
        added_count, pool_size = merge_candidate_match_pool(matches)
        clear_loaded_match()
        st.success(
            f"识别完成，锚点玩家：{anchor_name}；共得到 {len(matches)} 个自定义房候选对局，"
            f"其中新增 {added_count} 个进入候选池，候选池当前共 {pool_size} 局。"
        )

matches = st.session_state.candidate_matches
candidate_pool = st.session_state.candidate_match_pool
hit_player_count = len({name for item in matches for name in item.hit_input_names})
col1, col2, col3, col4 = st.columns(4)
col1.metric("候选对局数", len(matches))
col2.metric("命中玩家数", hit_player_count)
col3.metric("平台", st.session_state.platform)
col4.metric("候选池局数", len(candidate_pool))

if matches:
    st.dataframe(candidate_matches_df(matches), use_container_width=True, hide_index=True)
else:
    render_empty_state("当前还没有候选对局。该功能需要有效的 API Key，因为玩家昵称查询依赖 players 接口。")
