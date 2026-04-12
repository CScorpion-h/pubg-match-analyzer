"""候选对局识别逻辑。"""

from __future__ import annotations

from collections import defaultdict

from pubg_match_analyzer.core.constants import (
    MIN_HIT_PLAYER_COUNT,
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


def detect_candidate_matches(
    client: PubgAPIClient,
    player_names: list[str],
    recent_match_limit: int,
) -> list[CandidateMatch]:
    """读取多个玩家的最近对局，并找出共同出现的自定义房。"""
    names = _unique_player_names(player_names)
    if len(names) < MIN_HIT_PLAYER_COUNT:
        raise ValueError(f"至少输入 {MIN_HIT_PLAYER_COUNT} 个玩家昵称。")

    match_hits: dict[str, list[str]] = defaultdict(list)
    for name in names:
        for match_id in client.get_recent_match_ids(name, recent_match_limit):
            match_hits[match_id].append(name)

    candidate_ids = [
        match_id
        for match_id, hit_names in match_hits.items()
        if len(hit_names) >= MIN_HIT_PLAYER_COUNT
    ]

    candidates: list[CandidateMatch] = []
    for match_id in candidate_ids:
        payload = client.get_match(match_id)
        overview = build_match_overview(match_id, payload)
        if not overview.is_supported_custom_match:
            continue
        hit_names = match_hits[match_id]
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
    return candidates


