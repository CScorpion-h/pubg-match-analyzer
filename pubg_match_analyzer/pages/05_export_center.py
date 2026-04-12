"""导出中心页面。"""

from __future__ import annotations

import streamlit as st

from pubg_match_analyzer.services.export_service import build_csv_zip_bytes, build_excel_bytes
from pubg_match_analyzer.ui.styles import apply_global_styles
from pubg_match_analyzer.core.ui_state import ensure_session_state


ensure_session_state()
apply_global_styles()
st.title("导出中心")
st.caption("先勾选导出内容，再点击“生成导出文件”。生成完成后才会显示下载按钮。")


def clear_generated_export() -> None:
    """清空当前会话里已经生成的导出缓存。"""
    st.session_state.generated_export_match_id = ""
    st.session_state.generated_export_sheet_names = []
    st.session_state.generated_export_excel_bytes = b""
    st.session_state.generated_export_csv_zip_bytes = b""


overview = st.session_state.selected_match_overview
if not overview:
    clear_generated_export()
    st.info("请先载入一个对局。")
    st.stop()

if (
    st.session_state.generated_export_match_id
    and st.session_state.generated_export_match_id != overview.match_id
):
    clear_generated_export()

with st.form("export_form"):
    st.subheader("导出内容")
    st.checkbox("对局基础信息（MatchOverview）", key="export_include_match_overview")
    st.checkbox("玩家明细（PlayerStats）", key="export_include_player_stats")
    st.checkbox("队伍汇总（TeamSummary）", key="export_include_team_summary")
    generate = st.form_submit_button("生成导出文件", type="primary", use_container_width=True)

selected_sheets = []
if st.session_state.export_include_match_overview:
    selected_sheets.append("MatchOverview")
if st.session_state.export_include_player_stats:
    selected_sheets.append("PlayerStats")
if st.session_state.export_include_team_summary:
    selected_sheets.append("TeamSummary")

st.info("修改勾选项后，需要重新点击一次“生成导出文件”。仅切换勾选项不会自动下载。")

if generate:
    if not selected_sheets:
        clear_generated_export()
        st.error("至少选择一个导出内容。")
    else:
        excel_bytes = build_excel_bytes(
            overview=overview,
            player_stats=st.session_state.selected_player_stats,
            team_summaries=st.session_state.selected_team_summaries,
            include_match_overview=st.session_state.export_include_match_overview,
            include_player_stats=st.session_state.export_include_player_stats,
            include_team_summary=st.session_state.export_include_team_summary,
        )
        csv_zip_bytes = build_csv_zip_bytes(
            overview=overview,
            player_stats=st.session_state.selected_player_stats,
            team_summaries=st.session_state.selected_team_summaries,
            include_match_overview=st.session_state.export_include_match_overview,
            include_player_stats=st.session_state.export_include_player_stats,
            include_team_summary=st.session_state.export_include_team_summary,
        )
        st.session_state.generated_export_match_id = overview.match_id
        st.session_state.generated_export_sheet_names = selected_sheets
        st.session_state.generated_export_excel_bytes = excel_bytes
        st.session_state.generated_export_csv_zip_bytes = csv_zip_bytes
        st.success("导出文件已生成。")

base_name = f"{overview.match_id}_{overview.game_mode}".replace("/", "_").replace(" ", "_")

if (
    st.session_state.generated_export_match_id == overview.match_id
    and st.session_state.generated_export_sheet_names
):
    st.subheader("导出结果")
    st.write("当前包含：" + "、".join(st.session_state.generated_export_sheet_names))

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "下载 Excel 工作簿",
            data=st.session_state.generated_export_excel_bytes,
            file_name=f"{base_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_excel_button",
            on_click="ignore",
        )
    with col2:
        st.download_button(
            "下载 CSV 压缩包",
            data=st.session_state.generated_export_csv_zip_bytes,
            file_name=f"{base_name}_csv.zip",
            mime="application/zip",
            use_container_width=True,
            key="download_csv_zip_button",
            on_click="ignore",
        )


