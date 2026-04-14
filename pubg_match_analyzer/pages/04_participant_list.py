"""参赛者名单页面，按 roster 生成模板化参赛名单。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.ui_state import ensure_session_state
from pubg_match_analyzer.services.participant_list import (
    build_participant_list_workbook,
    extract_signup_mode_names,
    infer_participant_template,
)
from pubg_match_analyzer.ui.styles import apply_global_styles


ensure_session_state()
apply_global_styles()
st.title("参赛者名单")
st.caption("基于当前已载入对局的 roster 生成参赛名单，可选导入报名表补 QQ。")


def clear_generated_participant_list() -> None:
    """清空当前会话中的参赛名单生成缓存。"""
    st.session_state.generated_participant_list_match_id = ""
    st.session_state.generated_participant_list_bytes = b""
    st.session_state.generated_participant_list_filename = ""
    st.session_state.generated_participant_list_summary = {}


def sync_signup_sheet_cache(uploader_key: str) -> tuple[str, bytes]:
    """把当前上传的报名表同步到会话缓存，并返回可用缓存。"""
    signup_file = st.session_state.get(uploader_key)
    if signup_file is not None:
        uploaded_bytes = signup_file.getvalue()
        uploaded_name = signup_file.name
        if (
            st.session_state.cached_participant_signup_filename != uploaded_name
            or st.session_state.cached_participant_signup_bytes != uploaded_bytes
        ):
            st.session_state.cached_participant_signup_filename = uploaded_name
            st.session_state.cached_participant_signup_bytes = uploaded_bytes
            clear_generated_participant_list()

    return (
        st.session_state.cached_participant_signup_filename,
        st.session_state.cached_participant_signup_bytes,
    )


overview = st.session_state.selected_match_overview
if not overview:
    clear_generated_participant_list()
    st.info("请先在“对局列表”里载入一个对局。")
    st.stop()

teams = st.session_state.selected_team_summaries
if (
    st.session_state.generated_participant_list_match_id
    and st.session_state.generated_participant_list_match_id != overview.match_id
):
    clear_generated_participant_list()

template_type, _ = infer_participant_template(teams)
max_team_size = max((team.player_count for team in teams), default=0)

st.caption("当前对局 ID")
st.code(overview.match_id, language=None)

col1, col2, col3 = st.columns(3)
col1.metric("队伍数", len(teams))
col2.metric("最大队伍人数", max_team_size)
col3.metric("模板类型", template_type)

uploader_key = f"participant_signup_file_{st.session_state.participant_signup_uploader_nonce}"
st.file_uploader("上传报名表（可选）", type=["xlsx"], key=uploader_key)
cached_signup_name, cached_signup_bytes = sync_signup_sheet_cache(uploader_key)

selected_signup_mode_name = ""
if not cached_signup_bytes:
    st.info("未上传报名表时，仍会生成参赛名单，但 QQ 列会留空，且不会把空 QQ 标成缺失。")
else:
    action_col, info_col = st.columns([1, 4])
    with action_col:
        if st.button("清除缓存报名表", use_container_width=True):
            st.session_state.cached_participant_signup_filename = ""
            st.session_state.cached_participant_signup_bytes = b""
            st.session_state.participant_signup_mode_select = "不指定（直接全表查找）"
            st.session_state.participant_signup_uploader_nonce += 1
            clear_generated_participant_list()
            st.rerun()
    with info_col:
        st.caption(f"当前缓存报名表：{cached_signup_name}")

    try:
        signup_mode_options = extract_signup_mode_names(cached_signup_bytes)
    except Exception as exc:
        st.error(f"报名表玩法读取失败：{exc}")
        signup_mode_options = []

    mode_options = ["不指定（直接全表查找）"] + signup_mode_options
    if st.session_state.participant_signup_mode_select not in mode_options:
        st.session_state.participant_signup_mode_select = mode_options[0]

    selected_mode = st.selectbox(
        "报名表优先匹配玩法（可选）",
        options=mode_options,
        key="participant_signup_mode_select",
    )
    if selected_mode != mode_options[0]:
        selected_signup_mode_name = selected_mode
        st.caption(f"报名表匹配策略：优先按“{selected_signup_mode_name}”匹配，未命中时再全表兜底。")
    else:
        st.caption("报名表匹配策略：当前未指定优先玩法，将直接全表查找。")

if st.button("生成参赛者名单", type="primary", use_container_width=True):
    try:
        result = build_participant_list_workbook(
            overview=overview,
            teams=teams,
            signup_excel_bytes=cached_signup_bytes or None,
            signup_mode_name=selected_signup_mode_name or None,
        )
    except Exception as exc:
        st.error(f"生成失败：{exc}")
    else:
        st.session_state.generated_participant_list_match_id = overview.match_id
        st.session_state.generated_participant_list_bytes = result.workbook_bytes
        st.session_state.generated_participant_list_filename = f"{overview.match_id}_参赛者名单.xlsx"
        st.session_state.generated_participant_list_summary = {
            "template_type": result.template_type,
            "signup_mode_name": result.signup_mode_name,
            "total_players": result.total_players,
            "filled_qq_count": result.filled_qq_count,
            "missing_contact_count": result.missing_contact_count,
            "conflict_count": result.conflict_count,
            "used_signup_sheet": result.used_signup_sheet,
        }
        st.success("参赛者名单已生成。")

summary = st.session_state.generated_participant_list_summary
if (
    st.session_state.generated_participant_list_match_id == overview.match_id
    and st.session_state.generated_participant_list_bytes
    and summary
):
    st.subheader("生成结果")
    result_col1, result_col2, result_col3, result_col4 = st.columns(4)
    result_col1.metric("参赛人数", summary.get("total_players", 0))
    result_col2.metric("已填 QQ 数", summary.get("filled_qq_count", 0))
    result_col3.metric("缺失联系方式", summary.get("missing_contact_count", 0))
    result_col4.metric("QQ 冲突", summary.get("conflict_count", 0))

    if summary.get("used_signup_sheet"):
        mode_text = summary.get("signup_mode_name") or "未指定，已直接全表匹配"
        st.caption(f"报名表已参与匹配。优先玩法：{mode_text}")
    else:
        st.caption("本次未导入报名表，名单仅包含 roster 中的实际参赛玩家。")

    st.download_button(
        "下载参赛者名单 Excel",
        data=st.session_state.generated_participant_list_bytes,
        file_name=st.session_state.generated_participant_list_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="download_participant_list_button",
        on_click="ignore",
    )
