"""首页，展示赛事氛围化入口和当前识别规则。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.constants import MIN_HIT_PLAYER_COUNT
from pubg_match_analyzer.core.ui_state import ensure_session_state
from pubg_match_analyzer.ui.components import (
    badge,
    load_asset_data_uri,
    render_home_landing,
    render_rule_item,
    render_stat_card,
)
from pubg_match_analyzer.ui.styles import apply_global_styles


ensure_session_state()
apply_global_styles()

platform_label = (st.session_state.platform or "steam").capitalize()
search_window = int(st.session_state.recent_match_limit)
candidate_count = len(st.session_state.candidate_match_pool)
hero_image = load_asset_data_uri("hero_banner.png")

stat_cards = [
    render_stat_card("平台", platform_label, "当前赛事查询平台"),
    render_stat_card("最大搜索窗口", str(search_window), "用于共同对局识别的候选范围"),
    render_stat_card("命中规则", f"至少 {MIN_HIT_PLAYER_COUNT} 人", "候选对局需满足最少共同出现人数"),
    render_stat_card("候选对局数", str(candidate_count), "当前候选池中已累积的可用对局"),
]

rule_items = [
    render_rule_item(1, f"对局识别：根据玩家昵称查找共同对局，并保留 {badge('matchType = custom')} 的对局。"),
    render_rule_item(2, f"识别逻辑：自动选择 {badge('recent matches')} 总量最少的玩家作为锚点，并在最大搜索窗口内检索其他玩家是否共同出现。"),
    render_rule_item(3, f"命中规则：候选对局只保留至少 {MIN_HIT_PLAYER_COUNT} 名输入玩家共同出现的对局。"),
    render_rule_item(4, f"分类信息：{badge('gameMode')} 仅用于展示房间的类别和队伍模式。"),
    render_rule_item(5, f"参赛者名单：可基于 {badge('roster')} 生成名单文件，且可选导入报名表补充 QQ。"),
    render_rule_item(6, "系统设置：当前只保留 PUBG API Key、平台和最大搜索窗口。"),
]

render_home_landing(
    eyebrow="PUBG Custom Match Analyzer",
    title="PUBG 水友赛数据统计工具",
    subtitle="支持自定义房间识别、参赛名单统计、报名表联系方式映射与赛果导出。",
    background_image=hero_image,
    stat_cards=stat_cards,
    rule_items=rule_items,
)
