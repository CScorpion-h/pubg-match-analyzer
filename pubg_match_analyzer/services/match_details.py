"""对局详情解析逻辑。"""

from __future__ import annotations

from typing import Any

from pubg_match_analyzer.core.constants import (
    classify_custom_match_category,
    display_map_name,
    is_custom_match,
)
from pubg_match_analyzer.core.models import MatchOverview, PlayerMatchStat, TeamSummary


def extract_telemetry_url(match_payload: dict[str, Any]) -> str:
    """从 match 返回体的 included.assets 中提取 telemetry URL。"""
    included = match_payload.get("included") or []
    for item in included:
        if item.get("type") != "asset":
            continue
        attrs = item.get("attributes") or {}
        if attrs.get("name") == "telemetry" and attrs.get("URL"):
            return str(attrs["URL"])
    return ""


def build_match_overview(match_id: str, match_payload: dict[str, Any]) -> MatchOverview:
    """把原始 match JSON 解析成页面和导出都可复用的概要对象。"""
    data = match_payload.get("data") or {}
    attrs = data.get("attributes") or {}
    included = match_payload.get("included") or []
    player_count = sum(1 for item in included if item.get("type") == "participant")
    roster_count = sum(1 for item in included if item.get("type") == "roster")
    game_mode = str(attrs.get("gameMode") or "")
    match_type = str(attrs.get("matchType") or "")
    custom_flag = attrs.get("isCustomMatch")
    is_custom = is_custom_match(match_type, custom_flag)
    category = classify_custom_match_category(game_mode) if is_custom else ""
    if is_custom and not category:
        category = "custom"
    return MatchOverview(
        match_id=match_id,
        started_at=str(attrs.get("createdAt") or ""),
        duration=int(attrs.get("duration") or 0),
        map_name=display_map_name(attrs.get("mapName")),
        game_mode=game_mode,
        match_type=match_type,
        is_supported_custom_match=is_custom,
        custom_match_category=category,
        player_count=player_count,
        roster_count=roster_count,
        telemetry_url=extract_telemetry_url(match_payload),
    )


def _participant_stats_by_id(match_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """建立 participant id 到其 stats 的查找表。"""
    stats_by_id: dict[str, dict[str, Any]] = {}
    for item in match_payload.get("included") or []:
        if item.get("type") != "participant":
            continue
        stats_by_id[item["id"]] = (item.get("attributes") or {}).get("stats") or {}
    return stats_by_id


def extract_team_summaries(match_id: str, match_payload: dict[str, Any]) -> list[TeamSummary]:
    """按 roster 聚合队伍统计。"""
    participant_stats = _participant_stats_by_id(match_payload)
    teams: list[TeamSummary] = []
    roster_idx = 0
    for item in match_payload.get("included") or []:
        if item.get("type") != "roster":
            continue
        roster_idx += 1
        attrs = item.get("attributes") or {}
        roster_stats = attrs.get("stats") or {}
        participant_refs = (((item.get("relationships") or {}).get("participants") or {}).get("data") or [])
        players = []
        total_kills = 0
        total_damage = 0.0
        for ref in participant_refs:
            pstats = participant_stats.get(ref.get("id"), {})
            if not pstats:
                continue
            players.append(str(pstats.get("name") or ""))
            total_kills += int(pstats.get("kills") or 0)
            total_damage += float(pstats.get("damageDealt") or 0.0)
        teams.append(
            TeamSummary(
                match_id=match_id,
                team_index=roster_idx,
                source_team_id=roster_stats.get("teamId"),
                rank=roster_stats.get("rank"),
                won=str(attrs.get("won")).lower() == "true",
                player_count=len(players),
                player_names=players,
                total_kills=total_kills,
                total_damage=round(total_damage, 3),
            )
        )
    return teams


def extract_player_stats(match_id: str, match_payload: dict[str, Any]) -> list[PlayerMatchStat]:
    """把 participant stats 转成页面展示使用的玩家明细。"""
    team_lookup: dict[str, tuple[int, int | None]] = {}
    roster_idx = 0
    for item in match_payload.get("included") or []:
        if item.get("type") != "roster":
            continue
        roster_idx += 1
        source_team_id = ((item.get("attributes") or {}).get("stats") or {}).get("teamId")
        participant_refs = (((item.get("relationships") or {}).get("participants") or {}).get("data") or [])
        for ref in participant_refs:
            pid = ref.get("id")
            if pid:
                team_lookup[pid] = (roster_idx, source_team_id)

    rows: list[PlayerMatchStat] = []
    for item in match_payload.get("included") or []:
        if item.get("type") != "participant":
            continue
        attrs = item.get("attributes") or {}
        stats = attrs.get("stats") or {}
        team_index, source_team_id = team_lookup.get(item["id"], (0, None))
        rows.append(
            PlayerMatchStat(
                match_id=match_id,
                player_name=str(stats.get("name") or ""),
                player_account_id=str(stats.get("playerId") or ""),
                team_index=team_index,
                source_team_id=source_team_id,
                placement=int(stats.get("winPlace") or 0),
                kills=int(stats.get("kills") or 0),
                assists=int(stats.get("assists") or 0),
                damage_dealt=round(float(stats.get("damageDealt") or 0.0), 3),
                time_survived=float(stats.get("timeSurvived") or 0.0),
                dbnos=int(stats.get("DBNOs") or 0),
                headshot_kills=int(stats.get("headshotKills") or 0),
            )
        )
    rows.sort(key=lambda row: (row.damage_dealt, row.kills, row.assists), reverse=True)
    return rows


