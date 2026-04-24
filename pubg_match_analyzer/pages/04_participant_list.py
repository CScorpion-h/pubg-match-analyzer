"""参赛者名单页面，支持单局和批量生成。"""

from __future__ import annotations

import json

import streamlit as st

from pubg_match_analyzer.core.ui_state import clear_candidate_match_pool, ensure_session_state
from pubg_match_analyzer.services.export_service import candidate_matches_df
from pubg_match_analyzer.services.participant_list import (
    build_batch_participant_zip,
    build_participant_list_filename,
    build_participant_list_workbook,
    infer_participant_template,
)
from pubg_match_analyzer.services.pubg_api import PubgAPIClient, PubgAPIError
from pubg_match_analyzer.services.signup_mapping import (
    HEADER_OPTION_NONE,
    MAX_MANUAL_SIGNUP_CONTACT_PAIRS,
    SignupContactPair,
    SignupSheetSchema,
    build_signup_file_cache_key,
    detect_signup_sheet_schema,
    extract_signup_mode_names,
    inspect_signup_workbook,
    validate_signup_sheet_schema,
)
from pubg_match_analyzer.ui.components import render_page_header
from pubg_match_analyzer.ui.styles import apply_global_styles


ensure_session_state()
apply_global_styles()
render_page_header("参赛者名单", "基于当前已载入对局的 roster 生成参赛名单，可按单局生成，也可对候选对局池做批量生成。")

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


def clear_generated_participant_outputs() -> None:
    """当报名表或字段映射变化时，清空所有已生成结果。"""
    clear_generated_participant_list()
    clear_generated_participant_batch()


def get_signup_schema_cache_entry(file_key: str) -> dict[str, object] | None:
    """读取当前文件对应的 schema 缓存。"""
    cache = st.session_state.participant_signup_schema_cache
    entry = cache.get(file_key)
    return entry if isinstance(entry, dict) else None


def set_signup_schema_cache_entry(file_key: str, schema: SignupSheetSchema, mapping_mode: str) -> None:
    """写入当前文件对应的 schema 缓存。"""
    cache = dict(st.session_state.participant_signup_schema_cache)
    cache[file_key] = {
        "schema": schema.to_dict(),
        "mapping_mode": mapping_mode,
    }
    st.session_state.participant_signup_schema_cache = cache


def ensure_option_state(key: str, default_value: str | int, options: list[str] | None = None) -> None:
    """在 widget 渲染前确保 session_state 中的默认值可用。"""
    current = st.session_state.get(key)
    if options is None:
        if current is None:
            st.session_state[key] = default_value
        return
    if current not in options:
        st.session_state[key] = default_value if default_value in options else options[0]


def sync_signup_sheet_cache(uploader_key: str) -> tuple[str, bytes, str]:
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
            st.session_state.participant_signup_mode_select = "不指定（直接全表查找）"
            clear_generated_participant_outputs()

    cached_signup_name = st.session_state.cached_participant_signup_filename
    cached_signup_bytes = st.session_state.cached_participant_signup_bytes
    if not cached_signup_name or not cached_signup_bytes:
        st.session_state.participant_signup_schema_file_key = ""
        st.session_state.participant_signup_manual_mapping = False
        return "", b"", ""

    file_key = build_signup_file_cache_key(cached_signup_name, cached_signup_bytes)
    if st.session_state.participant_signup_schema_file_key != file_key:
        st.session_state.participant_signup_schema_file_key = file_key
        cache_entry = get_signup_schema_cache_entry(file_key)
        st.session_state.participant_signup_manual_mapping = bool(
            cache_entry and cache_entry.get("mapping_mode") == "manual"
        )

    return cached_signup_name, cached_signup_bytes, file_key


def clear_signup_sheet_cache() -> None:
    """清空报名表缓存和关联的字段映射状态。"""
    st.session_state.cached_participant_signup_filename = ""
    st.session_state.cached_participant_signup_bytes = b""
    st.session_state.participant_signup_mode_select = "不指定（直接全表查找）"
    st.session_state.participant_signup_uploader_nonce += 1
    st.session_state.participant_signup_schema_file_key = ""
    st.session_state.participant_signup_manual_mapping = False
    st.session_state.participant_signup_sheet_select = ""
    st.session_state.participant_signup_mode_col_select = HEADER_OPTION_NONE
    st.session_state.participant_signup_submitted_at_col_select = HEADER_OPTION_NONE
    st.session_state.participant_signup_contact_pair_count = 1
    for index in range(MAX_MANUAL_SIGNUP_CONTACT_PAIRS):
        st.session_state.pop(f"participant_signup_game_id_col_{index}", None)
        st.session_state.pop(f"participant_signup_qq_col_{index}", None)
    clear_generated_participant_outputs()


def sync_participant_signup_signature(file_key: str, schema: SignupSheetSchema | None, signup_mode_name: str) -> None:
    """当报名表映射或优先玩法变化时，主动清空旧生成结果。"""
    schema_dict = schema.to_dict() if schema is not None else {}
    signature = json.dumps(
        {
            "file_key": file_key,
            "schema": schema_dict,
            "signup_mode_name": signup_mode_name,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    if st.session_state.get("_participant_signup_signature") == signature:
        return
    clear_generated_participant_outputs()
    st.session_state._participant_signup_signature = signature


def render_manual_schema_editor(
    workbook_sheets,
    detection_schema: SignupSheetSchema,
    cached_schema: SignupSheetSchema,
) -> SignupSheetSchema | None:
    """渲染手动字段映射区。"""
    sheet_options = [sheet.sheet_name for sheet in workbook_sheets]
    base_schema = cached_schema if cached_schema.sheet_name else detection_schema
    default_sheet = base_schema.sheet_name or sheet_options[0]
    ensure_option_state("participant_signup_sheet_select", default_sheet, sheet_options)
    selected_sheet = st.selectbox("工作表", options=sheet_options, key="participant_signup_sheet_select")

    selected_sheet_info = next(sheet for sheet in workbook_sheets if sheet.sheet_name == selected_sheet)
    field_options = [HEADER_OPTION_NONE] + selected_sheet_info.columns

    default_submitted_at = base_schema.submitted_at_col or HEADER_OPTION_NONE
    default_mode_col = base_schema.mode_col or HEADER_OPTION_NONE
    ensure_option_state("participant_signup_submitted_at_col_select", default_submitted_at, field_options)
    ensure_option_state("participant_signup_mode_col_select", default_mode_col, field_options)

    col1, col2 = st.columns(2)
    with col1:
        submitted_at_value = st.selectbox(
            "提交时间列（可选）",
            options=field_options,
            key="participant_signup_submitted_at_col_select",
        )
    with col2:
        mode_col_value = st.selectbox(
            "玩法列（可选）",
            options=field_options,
            key="participant_signup_mode_col_select",
        )

    pair_limit = max(1, min(MAX_MANUAL_SIGNUP_CONTACT_PAIRS, len(selected_sheet_info.columns)))
    default_pair_count = min(max(1, len(base_schema.contact_pairs) or 1), pair_limit)
    ensure_option_state("participant_signup_contact_pair_count", default_pair_count)
    if not isinstance(st.session_state.participant_signup_contact_pair_count, int):
        st.session_state.participant_signup_contact_pair_count = default_pair_count
    st.session_state.participant_signup_contact_pair_count = min(
        pair_limit,
        max(1, int(st.session_state.participant_signup_contact_pair_count)),
    )
    pair_count = st.number_input(
        "联系人列组数",
        min_value=1,
        max_value=pair_limit,
        step=1,
        key="participant_signup_contact_pair_count",
    )

    st.caption("每组联系人列都由“游戏ID列 + QQ列”组成。")
    pairs: list[SignupContactPair] = []
    has_incomplete_pair = False
    for index in range(int(pair_count)):
        default_pair = base_schema.contact_pairs[index] if index < len(base_schema.contact_pairs) else None
        game_key = f"participant_signup_game_id_col_{index}"
        qq_key = f"participant_signup_qq_col_{index}"
        ensure_option_state(
            game_key,
            default_pair.game_id_col if default_pair else HEADER_OPTION_NONE,
            field_options,
        )
        ensure_option_state(
            qq_key,
            default_pair.qq_col if default_pair else HEADER_OPTION_NONE,
            field_options,
        )
        pair_col1, pair_col2 = st.columns(2)
        with pair_col1:
            game_id_col = st.selectbox(
                f"第 {index + 1} 组 游戏ID列",
                options=field_options,
                key=game_key,
            )
        with pair_col2:
            qq_col = st.selectbox(
                f"第 {index + 1} 组 QQ列",
                options=field_options,
                key=qq_key,
            )
        if game_id_col == HEADER_OPTION_NONE and qq_col == HEADER_OPTION_NONE:
            continue
        if game_id_col == HEADER_OPTION_NONE or qq_col == HEADER_OPTION_NONE:
            has_incomplete_pair = True
            continue
        pairs.append(SignupContactPair(game_id_col=game_id_col, qq_col=qq_col))

    if has_incomplete_pair:
        st.error("手动映射中存在未配完整的联系人列组，请同时指定游戏ID列和 QQ 列。")
        return None

    schema = SignupSheetSchema(
        sheet_name=selected_sheet,
        submitted_at_col="" if submitted_at_value == HEADER_OPTION_NONE else submitted_at_value,
        mode_col="" if mode_col_value == HEADER_OPTION_NONE else mode_col_value,
        contact_pairs=pairs,
    )
    try:
        validate_signup_sheet_schema(schema, workbook_sheets)
    except ValueError as exc:
        st.error(f"当前字段映射无效：{exc}")
        return None

    return schema


def render_signup_mapping_section(cached_signup_bytes: bytes, file_key: str) -> SignupSheetSchema | None:
    """渲染报名表结构识别与字段映射。"""
    workbook_sheets = inspect_signup_workbook(cached_signup_bytes)
    detection = detect_signup_sheet_schema(cached_signup_bytes, workbook_sheets)
    cache_entry = get_signup_schema_cache_entry(file_key)
    if cache_entry is None:
        set_signup_schema_cache_entry(file_key, detection.schema, "auto")
        cache_entry = get_signup_schema_cache_entry(file_key)

    cached_schema = SignupSheetSchema.from_dict(cache_entry.get("schema") if cache_entry else {})
    default_manual = bool(cache_entry and cache_entry.get("mapping_mode") == "manual")

    with st.expander("报名表结构识别 / 字段映射", expanded=detection.requires_manual_confirmation or default_manual):
        st.caption(
            f"自动识别结果：{detection.preset_name} | 工作表：{detection.matched_sheet_name} | "
            f"联系人列组：{len(detection.schema.contact_pairs)} 组 | 置信度：{detection.confidence}"
        )
        if detection.requires_manual_confirmation:
            st.warning("当前自动识别置信度较低，建议打开手动调整字段映射进行确认。")

        manual_mapping = st.checkbox("手动调整字段映射", key="participant_signup_manual_mapping")
        if manual_mapping:
            active_schema = render_manual_schema_editor(workbook_sheets, detection.schema, cached_schema)
            if active_schema is not None:
                set_signup_schema_cache_entry(file_key, active_schema, "manual")
                st.caption(
                    f"当前使用手动映射：工作表 {active_schema.sheet_name} | 联系人列组 {len(active_schema.contact_pairs)} 组"
                )
            return active_schema

        active_schema = detection.schema
        try:
            validate_signup_sheet_schema(active_schema, workbook_sheets)
        except ValueError as exc:
            st.error(f"自动识别的字段映射不可用：{exc}")
            return None

        set_signup_schema_cache_entry(file_key, active_schema, "auto")
        st.caption(
            f"当前使用自动识别映射：工作表 {active_schema.sheet_name} | 联系人列组 {len(active_schema.contact_pairs)} 组"
        )
        return active_schema


def render_signup_cache_section() -> tuple[bytes, SignupSheetSchema | None, str]:
    """渲染报名表缓存上传区，返回缓存字节、schema 和当前优先玩法。"""
    st.subheader("报名表缓存")
    uploader_key = f"participant_signup_file_{st.session_state.participant_signup_uploader_nonce}"
    st.file_uploader("上传报名表（可选）", type=["xlsx"], key=uploader_key)
    cached_signup_name, cached_signup_bytes, file_key = sync_signup_sheet_cache(uploader_key)

    if not cached_signup_bytes:
        sync_participant_signup_signature("", None, "")
        st.info("未上传报名表时，仍可生成参赛名单，但 QQ 列会留空，且不会把空 QQ 标成缺失。")
        return b"", None, ""

    action_col, info_col = st.columns([1, 4])
    with action_col:
        if st.button("清除缓存报名表", use_container_width=True):
            clear_signup_sheet_cache()
            st.rerun()
    with info_col:
        st.caption(f"当前缓存报名表：{cached_signup_name}")

    try:
        active_schema = render_signup_mapping_section(cached_signup_bytes, file_key)
    except Exception as exc:
        st.error(f"报名表结构读取失败：{exc}")
        sync_participant_signup_signature(file_key, None, "")
        return cached_signup_bytes, None, ""

    selected_signup_mode_name = ""
    mode_options = ["不指定（直接全表查找）"]
    if active_schema is not None:
        try:
            signup_mode_options = extract_signup_mode_names(cached_signup_bytes, active_schema)
        except Exception as exc:
            st.error(f"报名表玩法读取失败：{exc}")
            signup_mode_options = []
        mode_options.extend(signup_mode_options)

    if st.session_state.participant_signup_mode_select not in mode_options:
        st.session_state.participant_signup_mode_select = mode_options[0]

    selected_mode = st.selectbox(
        "报名表优先匹配玩法（可选）",
        options=mode_options,
        key="participant_signup_mode_select",
    )
    if active_schema is None:
        st.warning("当前字段映射不可用，本次不会使用报名表补充 QQ。")
        sync_participant_signup_signature(file_key, None, "")
        return cached_signup_bytes, None, ""

    if not active_schema.mode_col:
        st.caption("当前映射未指定玩法列，将直接全表查找。")
    elif selected_mode != mode_options[0]:
        selected_signup_mode_name = selected_mode
        st.caption(f"报名表匹配策略：优先按“{selected_signup_mode_name}”匹配，未命中时再全表兜底。")
    else:
        st.caption("报名表匹配策略：当前未指定优先玩法，将直接全表查找。")

    sync_participant_signup_signature(file_key, active_schema, selected_signup_mode_name)
    return cached_signup_bytes, active_schema, selected_signup_mode_name


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
    clear_generated_participant_batch()


signup_excel_bytes, signup_sheet_schema, selected_signup_mode_name = render_signup_cache_section()
st.text_input(
    "赛事名（可选）",
    key="participant_batch_event_name",
    on_change=clear_generated_participant_outputs,
)
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
participant_event_name = st.session_state.participant_batch_event_name.strip() or None

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
    single_round_name = "第1局"

    if st.button("生成参赛者名单", type="primary", use_container_width=True):
        try:
            result = build_participant_list_workbook(
                overview=overview,
                teams=teams,
                signup_excel_bytes=signup_excel_bytes or None,
                signup_sheet_schema=signup_sheet_schema,
                signup_mode_name=selected_signup_mode_name or None,
                event_name=participant_event_name,
                round_name=single_round_name,
            )
        except Exception as exc:
            st.error(f"生成失败：{exc}")
        else:
            st.session_state.generated_participant_list_match_id = overview.match_id
            st.session_state.generated_participant_list_bytes = result.workbook_bytes
            st.session_state.generated_participant_list_filename = build_participant_list_filename(
                match_id=overview.match_id,
                event_name=participant_event_name,
                round_name=single_round_name,
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
                signup_sheet_schema=signup_sheet_schema,
                signup_mode_name=selected_signup_mode_name or None,
                event_name=participant_event_name,
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
