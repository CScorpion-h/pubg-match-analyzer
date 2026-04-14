"""对局列表页面，负责选择或载入单个 match_id。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.models import CandidateMatch
from pubg_match_analyzer.core.constants import display_game_mode, display_game_mode_category
from pubg_match_analyzer.services.export_service import candidate_matches_df
from pubg_match_analyzer.services.match_details import (
    build_match_overview,
    extract_player_stats,
    extract_team_summaries,
)
from pubg_match_analyzer.services.pubg_api import PubgAPIClient, PubgAPIError
from pubg_match_analyzer.ui.styles import apply_global_styles
from pubg_match_analyzer.core.ui_state import ensure_session_state, merge_candidate_match_pool


def build_candidate_pool_item(match_id: str, overview, matches: list[CandidateMatch]) -> CandidateMatch:
    """把当前载入结果转换成可放入候选池的基础结构。"""
    existing = next((item for item in matches if item.match_id == match_id), None)
    if existing is not None:
        return existing
    return CandidateMatch(
        match_id=overview.match_id,
        started_at=overview.started_at,
        map_name=overview.map_name,
        game_mode=overview.game_mode,
        player_count=overview.player_count,
        hit_input_count=0,
        hit_rate=0.0,
        custom_match_category=overview.custom_match_category,
        hit_input_names=[],
    )


ensure_session_state()
apply_global_styles()
st.title("对局列表")
st.caption("从候选结果中选择，或直接输入 match_id 载入对局详情。")

matches = st.session_state.candidate_matches
if matches:
    st.dataframe(candidate_matches_df(matches), use_container_width=True, hide_index=True)
else:
    st.info("当前还没有候选对局。你也可以直接手动输入 match_id。")

candidate_ids = [item.match_id for item in matches]
match_options = [""] + candidate_ids
if st.session_state.selected_candidate_match_id not in match_options:
    st.session_state.selected_candidate_match_id = ""

st.selectbox("候选对局 match_id", options=match_options, key="selected_candidate_match_id")
st.text_input("手动输入 match_id", key="manual_match_id_input")

target_match_id = (
    st.session_state.manual_match_id_input.strip()
    or st.session_state.selected_candidate_match_id.strip()
)

if st.button("载入对局", type="primary", use_container_width=True):
    if not target_match_id:
        st.error("请先选择或输入 match_id。")
    else:
        try:
            client = PubgAPIClient(platform=st.session_state.platform, api_key=st.session_state.api_key)
            payload = client.get_match(target_match_id)
            overview = build_match_overview(target_match_id, payload)
            players = extract_player_stats(target_match_id, payload)
            teams = extract_team_summaries(target_match_id, payload)
        except PubgAPIError as exc:
            st.error(str(exc))
        else:
            st.session_state.selected_match_id = target_match_id
            st.session_state.selected_match_overview = overview
            st.session_state.selected_player_stats = players
            st.session_state.selected_team_summaries = teams
            st.session_state.selected_telemetry_url = overview.telemetry_url
            pool_item = build_candidate_pool_item(target_match_id, overview, matches)
            added_count, pool_size = merge_candidate_match_pool([pool_item])
            action_text = "已加入候选池" if added_count else "候选池中已存在该对局"
            st.success(f"对局数据已载入，{action_text}。候选池当前共 {pool_size} 局。")

overview = st.session_state.selected_match_overview
if overview:
    st.subheader("当前已载入")
    st.caption("对局 ID")
    # 长字符串放进代码块比 metric 更稳定，不会被截断。
    st.code(overview.match_id, language=None)

    col1, col2, col3 = st.columns(3)
    col1.metric("地图", overview.map_name)
    col2.metric("模式", display_game_mode(overview.game_mode))
    col3.metric("参赛人数", overview.player_count)
    st.caption(f"模式分类：{display_game_mode_category(overview.custom_match_category)}")


