"""参赛者名单页面，支持单局和批量生成。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.core.ui_state import (
    clear_candidate_match_pool,
    ensure_session_state,
)
from pubg_match_analyzer.services.export_service import candidate_matches_df
from pubg_match_analyzer.services.participant_list import (
    build_batch_participant_zip,
    build_participant_list_filename,
    build_participant_list_workbook,
    extract_signup_mode_names,
    infer_participant_template,
)
from pubg_match_analyzer.services.pubg_api import PubgAPIClient, PubgAPIError
from pubg_match_analyzer.ui.styles import apply_global_styles


ensure_session_state()
apply_global_styles()
st.title("参赛者名单")
st.caption("基于对局 roster 生成参赛名单，可按单局生成，也可对候选对局池做批量生成。")


def clear_generated_participant_list() -> None:
    """清空当前会话中的单局参赛名单生成缓存。"""
    st.session_state.generated_participant_list_match_id = ""
    st.session_state.generated_participant_list_bytes = b""
    st.session_state.generated_participant_list_filename = ""
    st.session_state.generated_participant_list_summary = {}


def clear_generated_participant_batch() -> None:
    """清空当前会话中的批量参赛名单生成缓存。"""
    st.session_state.generated_participant_batch_zip_bytes = b""
    st.session_state.generated_participant_batch_zip_filename = ""
    st.session_state.generated_participant_batch_summary = {}


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
            clear_generated_participant_batch()

    return (
        st.session_state.cached_participant_signup_filename,
        st.session_state.cached_participant_signup_bytes,
    )


def clear_signup_sheet_cache() -> None:
    """清空报名表缓存和关联的玩法选择。"""
    st.session_state.cached_participant_signup_filename = ""
    st.session_state.cached_participant_signup_bytes = b""
    st.session_state.participant_signup_mode_select = "不指定（直接全表查找）"
    st.session_state.participant_signup_uploader_nonce += 1
    clear_generated_participant_list()
    clear_generated_participant_batch()


def render_signup_cache_section() -> tuple[bytes, str]:
    """渲染报名表缓存上传区，返回缓存字节和当前优先玩法。"""
    st.subheader("报名表缓存")
    uploader_key = f"participant_signup_file_{st.session_state.participant_signup_uploader_nonce}"
    st.file_uploader("上传报名表（可选）", type=["xlsx"], key=uploader_key)
    cached_signup_name, cached_signup_bytes = sync_signup_sheet_cache(uploader_key)

    selected_signup_mode_name = ""
    if not cached_signup_bytes:
        st.info("未上传报名表时，仍可生成参赛名单，但 QQ 列会留空，且不会把空 QQ 标成缺失。")
        return b"", ""

    action_col, info_col = st.columns([1, 4])
    with action_col:
        if st.button("清除缓存报名表", use_container_width=True):
            clear_signup_sheet_cache()
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

    return cached_signup_bytes, selected_signup_mode_name


def round_name_widget_key(match_id: str) -> str:
    """为批量局次名称输入生成稳定 widget key。"""
    return f"participant_batch_round_name_{match_id}"


def sync_batch_round_name(match_id: str, default_name: str) -> None:
    """同步批量生成页面中的局次名称。"""
    widget_key = round_name_widget_key(match_id)
    value = str(st.session_state.get(widget_key, "")).strip() or default_name
    round_name_map = dict(st.session_state.participant_batch_round_name_map)
    round_name_manual = dict(st.session_state.participant_batch_round_name_manual)
    round_name_map[match_id] = value
    round_name_manual[match_id] = value != default_name
    st.session_state.participant_batch_round_name_map = round_name_map
    st.session_state.participant_batch_round_name_manual = round_name_manual


signup_excel_bytes, selected_signup_mode_name = render_signup_cache_section()
st.divider()

mode = st.radio(
    "生成模式",
    options=["单局生成", "批量生成"],
    key="participant_generation_mode",
    horizontal=True,
)

overview = st.session_state.selected_match_overview
teams = st.session_state.selected_team_summaries
candidate_pool = st.session_state.candidate_match_pool

if mode == "单局生成":
    if not overview:
        clear_generated_participant_list()
        st.info("请先在“对局列表”里载入一个对局。")
        st.stop()

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

    if st.button("生成参赛者名单", type="primary", use_container_width=True):
        try:
            result = build_participant_list_workbook(
                overview=overview,
                teams=teams,
                signup_excel_bytes=signup_excel_bytes or None,
                signup_mode_name=selected_signup_mode_name or None,
                round_name=None,
            )
        except Exception as exc:
            st.error(f"生成失败：{exc}")
        else:
            st.session_state.generated_participant_list_match_id = overview.match_id
            st.session_state.generated_participant_list_bytes = result.workbook_bytes
            st.session_state.generated_participant_list_filename = build_participant_list_filename(
                match_id=overview.match_id,
            )
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
else:
    st.subheader("候选对局池")
    pool_col1, pool_col2 = st.columns([4, 1])
    with pool_col1:
        st.caption("批量对象来自候选对局池。候选池可由多次对局识别结果累积，也可由对局列表中的手动载入补充。")
    with pool_col2:
        if st.button("清空候选池", use_container_width=True):
            clear_candidate_match_pool()
            st.rerun()

    if not candidate_pool:
        clear_generated_participant_batch()
        st.info("当前候选对局池为空。请先通过“对局识别”累积候选对局，或在“对局列表”中手动载入 match_id。")
        st.stop()

    pool_by_id = {item.match_id: item for item in candidate_pool}
    pool_sorted = sorted(candidate_pool, key=lambda item: item.started_at)
    st.dataframe(candidate_matches_df(pool_sorted), use_container_width=True, hide_index=True)

    valid_match_ids = [item.match_id for item in pool_sorted]
    st.session_state.participant_batch_selected_ids = [
        match_id for match_id in st.session_state.participant_batch_selected_ids if match_id in valid_match_ids
    ]

    st.multiselect(
        "勾选要批量生成的对局",
        options=valid_match_ids,
        key="participant_batch_selected_ids",
        format_func=lambda match_id: (
            f"{pool_by_id[match_id].started_at} | {pool_by_id[match_id].map_name} | {pool_by_id[match_id].match_id}"
        ),
    )

    selected_matches = sorted(
        [pool_by_id[match_id] for match_id in st.session_state.participant_batch_selected_ids],
        key=lambda item: item.started_at,
    )
    if not selected_matches:
        clear_generated_participant_batch()
        st.info("请先从候选对局池中勾选至少一局。")
        st.stop()

    st.text_input("赛事名（可选）", key="participant_batch_event_name")
    st.subheader("局次设置")
    st.caption("局次默认按 started_at 升序生成。若需要对外展示不同名称，可在这里手动修改。")

    for index, item in enumerate(selected_matches, start=1):
        default_round_name = f"第{index}局"
        widget_key = round_name_widget_key(item.match_id)
        round_name_map = st.session_state.participant_batch_round_name_map
        round_name_manual = st.session_state.participant_batch_round_name_manual
        if round_name_manual.get(item.match_id):
            default_value = round_name_map.get(item.match_id, default_round_name)
        else:
            default_value = default_round_name
        st.session_state[widget_key] = default_value

        info_col, name_col = st.columns([3, 2])
        with info_col:
            st.caption(f"{item.started_at} | {item.map_name} | {item.match_id}")
        with name_col:
            st.text_input(
                f"{item.match_id} 局次名称",
                key=widget_key,
                label_visibility="collapsed",
                on_change=sync_batch_round_name,
                args=(item.match_id, default_round_name),
            )
        sync_batch_round_name(item.match_id, default_round_name)

    if st.button("批量生成参赛者名单", type="primary", use_container_width=True):
        clear_generated_participant_batch()
        round_name_map = {
            item.match_id: st.session_state.participant_batch_round_name_map.get(item.match_id, f"第{index}局")
            for index, item in enumerate(selected_matches, start=1)
        }
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        progress_bar = progress_placeholder.progress(0)

        def update_progress(index: int, total: int, match_id: str, status: str) -> None:
            round_name = round_name_map.get(match_id, f"第{index}局")
            if status == "start":
                progress_bar.progress((index - 1) / total)
                status_placeholder.info(f"正在处理 {round_name} | {match_id}（{index}/{total}）")
            elif status == "success":
                progress_bar.progress(index / total)
                status_placeholder.success(f"已完成 {round_name} | {match_id}（{index}/{total}）")
            else:
                progress_bar.progress(index / total)
                status_placeholder.warning(f"处理失败 {round_name} | {match_id}（{index}/{total}）")

        try:
            client = PubgAPIClient(platform=st.session_state.platform, api_key=st.session_state.api_key)
            result = build_batch_participant_zip(
                client=client,
                match_ids=[item.match_id for item in selected_matches],
                signup_excel_bytes=signup_excel_bytes or None,
                signup_mode_name=selected_signup_mode_name or None,
                event_name=st.session_state.participant_batch_event_name.strip(),
                round_name_map=round_name_map,
                current_overview=overview,
                current_teams=teams,
                progress_callback=update_progress,
            )
        except (PubgAPIError, ValueError) as exc:
            progress_placeholder.empty()
            st.error(f"批量生成失败：{exc}")
        else:
            progress_bar.progress(1.0)
            status_placeholder.success("批量生成已结束。")
            st.session_state.generated_participant_batch_zip_bytes = result.zip_bytes
            st.session_state.generated_participant_batch_zip_filename = result.zip_filename
            st.session_state.generated_participant_batch_summary = {
                "requested_match_count": result.requested_match_count,
                "generated_match_count": result.generated_match_count,
                "failed_match_count": len(result.failed_matches),
                "total_players": result.total_players,
                "total_conflicts": result.total_conflicts,
                "total_missing_contacts": result.total_missing_contacts,
                "item_filenames": result.item_filenames,
                "failed_matches": result.failed_matches,
                "selected_match_ids": [item.match_id for item in selected_matches],
            }
            st.success("批量参赛者名单已生成。")

    batch_summary = st.session_state.generated_participant_batch_summary
    if (
        st.session_state.generated_participant_batch_zip_bytes
        and batch_summary
        and batch_summary.get("selected_match_ids") == [item.match_id for item in selected_matches]
    ):
        st.subheader("批量生成结果")
        result_col1, result_col2, result_col3, result_col4 = st.columns(4)
        result_col1.metric("请求局数", batch_summary.get("requested_match_count", 0))
        result_col2.metric("成功局数", batch_summary.get("generated_match_count", 0))
        result_col3.metric("失败局数", batch_summary.get("failed_match_count", 0))
        result_col4.metric("总参赛人数", batch_summary.get("total_players", 0))
        extra_col1, extra_col2 = st.columns(2)
        extra_col1.metric("缺失联系方式", batch_summary.get("total_missing_contacts", 0))
        extra_col2.metric("QQ 冲突", batch_summary.get("total_conflicts", 0))
        st.caption("ZIP 内文件：" + "、".join(batch_summary.get("item_filenames", [])))
        failed_matches = batch_summary.get("failed_matches", [])
        if failed_matches:
            st.warning("以下局次生成失败，未写入本次 ZIP：")
            st.dataframe(failed_matches, use_container_width=True, hide_index=True)
        st.download_button(
            "下载批量参赛者名单 ZIP",
            data=st.session_state.generated_participant_batch_zip_bytes,
            file_name=st.session_state.generated_participant_batch_zip_filename,
            mime="application/zip",
            use_container_width=True,
            key="download_participant_batch_zip_button",
            on_click="ignore",
        )
