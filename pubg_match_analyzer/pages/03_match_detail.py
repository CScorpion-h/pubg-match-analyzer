"""对局详情页面，展示当前已载入对局的玩家和队伍数据。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.constants import display_game_mode, display_game_mode_category, format_duration_mmss
from pubg_match_analyzer.core.ui_state import ensure_session_state
from pubg_match_analyzer.services.export_service import player_stats_df, team_summary_df
from pubg_match_analyzer.ui.components import render_empty_state, render_page_header
from pubg_match_analyzer.ui.styles import apply_global_styles


ensure_session_state()
apply_global_styles()
render_page_header("对局详情", "查看当前已载入对局的摘要指标、玩家明细和队伍汇总。")

overview = st.session_state.selected_match_overview
if not overview:
    render_empty_state("请先在“对局列表”里载入一个对局。")
    st.stop()

players = st.session_state.selected_player_stats
teams = st.session_state.selected_team_summaries

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("参赛玩家数", overview.player_count)
col2.metric("队伍数", overview.roster_count)
col3.metric("地图", overview.map_name)
col4.metric("模式", display_game_mode(overview.game_mode))
col5.metric("模式分类", display_game_mode_category(overview.custom_match_category) or "-")

st.caption(f"开始时间：{overview.started_at} | telemetry 链接：{overview.telemetry_url or '未发现'}")

player_df = player_stats_df(players)
team_df = team_summary_df(teams)

tab1, tab2 = st.tabs(["玩家明细", "队伍汇总"])

with tab1:
    st.text_input("按玩家昵称搜索", key="player_search_query")
    filtered = player_df
    if st.session_state.player_search_query.strip():
        filtered = filtered[
            filtered["玩家昵称"].str.contains(
                st.session_state.player_search_query.strip(),
                case=False,
                na=False,
            )
        ]
    display_df = filtered.drop(columns=["对局ID"], errors="ignore")
    if "存活时长" in display_df.columns:
        display_df = display_df.copy()
        display_df["存活时长"] = display_df["存活时长"].map(format_duration_mmss)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab2:
    st.dataframe(team_df, use_container_width=True, hide_index=True)

with st.expander("原始对局信息"):
    st.json(overview.to_dict(), expanded=False)
