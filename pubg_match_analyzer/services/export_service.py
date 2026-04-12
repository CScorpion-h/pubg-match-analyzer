"""导出表格和文件构建。"""

from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from pubg_match_analyzer.core.constants import display_game_mode, display_game_mode_category
from pubg_match_analyzer.core.models import CandidateMatch, MatchOverview, PlayerMatchStat, TeamSummary


def candidate_matches_df(items: list[CandidateMatch]) -> pd.DataFrame:
    """把候选对局对象列表转换成页面展示 DataFrame。"""
    rows = []
    for item in items:
        rows.append(
            {
                "match_id": item.match_id,
                "started_at": item.started_at,
                "map_name": item.map_name,
                "game_mode": display_game_mode(item.game_mode),
                "player_count": item.player_count,
                "hit_input_count": item.hit_input_count,
                "hit_rate": item.hit_rate,
                "game_mode_category": display_game_mode_category(item.custom_match_category),
                "hit_input_names": item.hit_input_names,
            }
        )
    return pd.DataFrame(rows)


def match_overview_df(item: MatchOverview | None) -> pd.DataFrame:
    """生成 MatchOverview 工作表。"""
    if item is None:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "match_id": item.match_id,
                "started_at": item.started_at,
                "duration": item.duration,
                "map_name": item.map_name,
                "game_mode": display_game_mode(item.game_mode),
                "game_mode_code": item.game_mode,
                "game_mode_category": display_game_mode_category(item.custom_match_category),
                "game_mode_category_code": item.custom_match_category,
                "match_type": item.match_type,
                "is_supported_custom_match": item.is_supported_custom_match,
                "player_count": item.player_count,
                "roster_count": item.roster_count,
                "telemetry_url": item.telemetry_url,
            }
        ]
    )


def player_stats_df(items: list[PlayerMatchStat]) -> pd.DataFrame:
    """生成 PlayerStats 工作表。"""
    return pd.DataFrame([item.to_dict() for item in items])


def team_summary_df(items: list[TeamSummary]) -> pd.DataFrame:
    """生成 TeamSummary 工作表。"""
    return pd.DataFrame([item.to_dict() for item in items])


def build_export_tables(
    *,
    overview: MatchOverview | None,
    player_stats: list[PlayerMatchStat],
    team_summaries: list[TeamSummary],
    include_match_overview: bool,
    include_player_stats: bool,
    include_team_summary: bool,
) -> list[tuple[str, pd.DataFrame]]:
    """根据勾选项组装待导出的工作表列表。"""
    tables: list[tuple[str, pd.DataFrame]] = []
    if include_match_overview:
        tables.append(("MatchOverview", match_overview_df(overview)))
    if include_player_stats:
        tables.append(("PlayerStats", player_stats_df(player_stats)))
    if include_team_summary:
        tables.append(("TeamSummary", team_summary_df(team_summaries)))
    return tables


def build_excel_bytes(
    *,
    overview: MatchOverview | None,
    player_stats: list[PlayerMatchStat],
    team_summaries: list[TeamSummary],
    include_match_overview: bool,
    include_player_stats: bool,
    include_team_summary: bool,
) -> bytes:
    """把当前勾选的导出内容打包成 Excel 工作簿字节流。"""
    tables = build_export_tables(
        overview=overview,
        player_stats=player_stats,
        team_summaries=team_summaries,
        include_match_overview=include_match_overview,
        include_player_stats=include_player_stats,
        include_team_summary=include_team_summary,
    )
    if not tables:
        raise ValueError("至少选择一个导出内容。")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, dataframe in tables:
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()


def build_csv_zip_bytes(
    *,
    overview: MatchOverview | None,
    player_stats: list[PlayerMatchStat],
    team_summaries: list[TeamSummary],
    include_match_overview: bool,
    include_player_stats: bool,
    include_team_summary: bool,
) -> bytes:
    """把当前勾选的导出内容打包成 CSV 压缩包字节流。"""
    tables = build_export_tables(
        overview=overview,
        player_stats=player_stats,
        team_summaries=team_summaries,
        include_match_overview=include_match_overview,
        include_player_stats=include_player_stats,
        include_team_summary=include_team_summary,
    )
    if not tables:
        raise ValueError("至少选择一个导出内容。")

    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as zf:
        for sheet_name, dataframe in tables:
            zf.writestr(f"{sheet_name}.csv", dataframe.to_csv(index=False).encode("utf-8-sig"))
    return buffer.getvalue()


