"""Streamlit 会话状态和本地配置持久化。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from pubg_match_analyzer.core.constants import (
    DEFAULT_PLATFORM,
    DEFAULT_RECENT_MATCH_LIMIT,
    MIN_HIT_PLAYER_COUNT,
)

# 这些 key 对应页面上的 widget，需要在页面切换时保活。
PERSISTED_WIDGET_KEYS = (
    "api_key",
    "platform",
    "recent_match_limit",
    "detect_input_text",
    "selected_candidate_match_id",
    "manual_match_id_input",
    "player_search_query",
    "export_include_match_overview",
    "export_include_player_stats",
    "export_include_team_summary",
)

LOCAL_SETTINGS_FILE = Path(__file__).resolve().parents[1] / "configs" / "local_settings.json"
LOCAL_SETTING_KEYS = ("api_key", "platform", "recent_match_limit")


def _load_local_settings() -> dict[str, object]:
    """从本地 JSON 读取可持久化设置。"""
    if not LOCAL_SETTINGS_FILE.exists():
        return {}

    try:
        raw = json.loads(LOCAL_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw, dict):
        return {}

    settings: dict[str, object] = {}

    api_key = raw.get("api_key")
    if isinstance(api_key, str):
        settings["api_key"] = api_key

    platform = raw.get("platform")
    if isinstance(platform, str):
        settings["platform"] = platform.strip() or DEFAULT_PLATFORM

    recent_match_limit = raw.get("recent_match_limit")
    try:
        recent_match_limit = int(recent_match_limit)
    except (TypeError, ValueError):
        recent_match_limit = None
    if recent_match_limit is not None:
        settings["recent_match_limit"] = min(100, max(5, recent_match_limit))

    return settings


def save_local_settings() -> None:
    """把当前会话中的基础设置写回本地文件。"""
    payload = {key: st.session_state.get(key) for key in LOCAL_SETTING_KEYS}
    LOCAL_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_SETTINGS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_local_settings() -> None:
    """删除本地保存的基础设置文件。"""
    if LOCAL_SETTINGS_FILE.exists():
        LOCAL_SETTINGS_FILE.unlink()


def sync_local_settings() -> None:
    """仅在基础设置变更时刷新本地保存，避免每次重跑都写盘。"""
    payload = {key: st.session_state.get(key) for key in LOCAL_SETTING_KEYS}
    last_saved = st.session_state.get("_local_settings_snapshot")
    if last_saved == payload:
        return
    save_local_settings()
    st.session_state._local_settings_snapshot = payload


def ensure_session_state() -> None:
    """初始化会话默认值，并恢复本地保存的基础设置。"""
    local_settings: dict[str, object] = {}
    if "_local_settings_loaded" not in st.session_state:
        local_settings = _load_local_settings()
        st.session_state._local_settings_loaded = True
        st.session_state._local_settings_snapshot = local_settings

    defaults = {
        "api_key": local_settings.get("api_key", os.getenv("PUBG_API_KEY", "")),
        "platform": local_settings.get("platform", DEFAULT_PLATFORM),
        "recent_match_limit": local_settings.get("recent_match_limit", DEFAULT_RECENT_MATCH_LIMIT),
        "min_hit_player_count": MIN_HIT_PLAYER_COUNT,
        "detect_input_text": "",
        "candidate_matches": [],
        "selected_match_id": "",
        "selected_match_overview": None,
        "selected_player_stats": [],
        "selected_team_summaries": [],
        "selected_telemetry_url": "",
        "selected_candidate_match_id": "",
        "manual_match_id_input": "",
        "player_search_query": "",
        "export_include_match_overview": True,
        "export_include_player_stats": True,
        "export_include_team_summary": True,
        "seat_template_df": pd.DataFrame(),
        "seat_audit_rows": [],
        "seat_unmatched_players": [],
        "alias_map_df": pd.DataFrame(),
        "generated_export_match_id": "",
        "generated_export_sheet_names": [],
        "generated_export_excel_bytes": b"",
        "generated_export_csv_zip_bytes": b"",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Streamlit 会清理当前页未渲染的 widget 状态，这里主动回写一次，
    # 让跨页面输入值能继续保留在 session_state 里。
    for key in PERSISTED_WIDGET_KEYS:
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]

    sync_local_settings()


def clear_loaded_match() -> None:
    """清空当前已载入对局及其派生出的展示/导出缓存。"""
    st.session_state.selected_match_id = ""
    st.session_state.selected_match_overview = None
    st.session_state.selected_player_stats = []
    st.session_state.selected_team_summaries = []
    st.session_state.selected_telemetry_url = ""
    st.session_state.player_search_query = ""
    st.session_state.seat_audit_rows = []
    st.session_state.seat_unmatched_players = []
    st.session_state.generated_export_match_id = ""
    st.session_state.generated_export_sheet_names = []
    st.session_state.generated_export_excel_bytes = b""
    st.session_state.generated_export_csv_zip_bytes = b""


