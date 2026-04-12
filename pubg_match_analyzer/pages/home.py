"""首页，总结当前实现范围和当前选中的对局。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.constants import MIN_HIT_PLAYER_COUNT
from pubg_match_analyzer.core.constants import display_game_mode, display_game_mode_category
from pubg_match_analyzer.ui.styles import apply_global_styles
from pubg_match_analyzer.core.ui_state import ensure_session_state


ensure_session_state()
apply_global_styles()

st.title("PUBG 水友赛数据统计工具")
st.caption("当前版本包含对局识别、对局列表、对局详情、导出中心和系统设置。")

col1, col2, col3, col4 = st.columns(4)
col1.metric("平台", st.session_state.platform)
col2.metric("最近对局窗口", str(st.session_state.recent_match_limit))
col3.metric("命中规则", f"至少 {MIN_HIT_PLAYER_COUNT} 人")
col4.metric("候选对局数", len(st.session_state.candidate_matches))

if st.session_state.selected_match_overview:
    overview = st.session_state.selected_match_overview
    st.success(
        "当前已载入对局："
        f"{overview.match_id} | "
        f"{display_game_mode_category(overview.custom_match_category)} | "
        f"{display_game_mode(overview.game_mode)} | "
        f"{overview.map_name}"
    )
else:
    st.info("先进入“对局识别”生成候选结果，或在“对局列表”里手动输入 match_id。")

st.markdown(
    f"""
### 当前实现说明

1. 对局识别：根据玩家昵称查共同对局，并保留 `matchType = custom` 的对局。
2. 命中规则：候选对局只保留至少 {MIN_HIT_PLAYER_COUNT} 名输入玩家共同出现的对局。
3. 分类信息：`gameMode` 只用于展示房间类别和队伍模式。
4. 当前导出：支持 `MatchOverview`、`PlayerStats` 和 `TeamSummary`。
5. 系统设置：当前只保留 PUBG API Key、平台和最近对局窗口。
"""
)


