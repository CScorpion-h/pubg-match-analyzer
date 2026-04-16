"""候选对局识别逻辑。"""

from __future__ import annotations

from collections import defaultdict

from pubg_match_analyzer.core.constants import (
    MIN_HIT_PLAYER_COUNT,
    SEARCH_WINDOW_STEP,
    normalize_player_name,
)
from pubg_match_analyzer.core.models import CandidateMatch
from pubg_match_analyzer.services.match_details import build_match_overview
from pubg_match_analyzer.services.pubg_api import PubgAPIClient


def _unique_player_names(player_names: list[str]) -> list[str]:
    """去掉空行和大小写重复昵称，保留用户原始输入顺序。"""
    result: list[str] = []
    seen: set[str] = set()
    for name in player_names:
        clean = name.strip()
        key = normalize_player_name(clean)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(clean)
    return result


def _search_windows(max_window: int) -> list[int]:
    """按固定步长生成累计搜索窗口。"""
    if max_window <= 0:
        return []

    windows: list[int] = []
    current = min(SEARCH_WINDOW_STEP, max_window)
    while current < max_window:
        windows.append(current)
        current += SEARCH_WINDOW_STEP
    windows.append(max_window)
    return windows


def _choose_anchor_player(names: list[str], match_ids_by_player: dict[str, list[str]]) -> str:
    """自动选择 recent matches 集合最小的玩家作为识别锚点。"""
    name_order = {name: idx for idx, name in enumerate(names)}
    return min(
        names,
        key=lambda name: (len(match_ids_by_player.get(name, [])), name_order[name]),
    )


def detect_candidate_matches(
    client: PubgAPIClient,
    player_names: list[str],
    recent_match_limit: int,
) -> tuple[list[CandidateMatch], str]:
    """读取多个玩家的 recent matches，并识别共同出现的自定义房。"""
    names = _unique_player_names(player_names)
    if len(names) < MIN_HIT_PLAYER_COUNT:
        raise ValueError(f"至少输入 {MIN_HIT_PLAYER_COUNT} 个玩家昵称。")

    match_ids_by_player = {name: client.get_all_match_ids(name) for name in names}
    anchor_name = _choose_anchor_player(names, match_ids_by_player)
    anchor_match_ids = match_ids_by_player.get(anchor_name, [])
    max_window = min(max(0, int(recent_match_limit)), len(anchor_match_ids))
    if max_window == 0:
        return [], anchor_name

    match_id_sets = {name: set(match_ids) for name, match_ids in match_ids_by_player.items()}
    match_hits: dict[str, list[str]] = defaultdict(list)
    processed_ids: set[str] = set()

    for window_size in _search_windows(max_window):
        for match_id in anchor_match_ids[:window_size]:
            if match_id in processed_ids:
                continue
            processed_ids.add(match_id)
            hit_names = [name for name in names if match_id in match_id_sets[name]]
            if len(hit_names) >= MIN_HIT_PLAYER_COUNT:
                match_hits[match_id] = hit_names

    candidates: list[CandidateMatch] = []
    for match_id, hit_names in match_hits.items():
        payload = client.get_match(match_id)
        overview = build_match_overview(match_id, payload)
        if not overview.is_supported_custom_match:
            continue
        candidates.append(
            CandidateMatch(
                match_id=match_id,
                started_at=overview.started_at,
                map_name=overview.map_name,
                game_mode=overview.game_mode,
                player_count=overview.player_count,
                hit_input_count=len(hit_names),
                hit_rate=round(len(hit_names) / len(names), 4),
                custom_match_category=overview.custom_match_category,
                hit_input_names=hit_names,
            )
        )

    candidates.sort(key=lambda item: (item.hit_input_count, item.started_at), reverse=True)
    return candidates, anchor_name
