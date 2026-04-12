"""应用内使用的数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CandidateMatch:
    """候选对局的简化展示结构。"""

    match_id: str
    started_at: str
    map_name: str
    game_mode: str
    player_count: int
    hit_input_count: int
    hit_rate: float
    custom_match_category: str
    hit_input_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """导出为 DataFrame 可直接使用的字典。"""
        return asdict(self)


@dataclass
class MatchOverview:
    """单场对局的总体信息。"""

    match_id: str
    started_at: str
    duration: int
    map_name: str
    game_mode: str
    match_type: str
    is_supported_custom_match: bool
    custom_match_category: str
    player_count: int
    roster_count: int
    telemetry_url: str

    def to_dict(self) -> dict[str, Any]:
        """导出为 DataFrame 或 JSON 可直接使用的字典。"""
        return asdict(self)


@dataclass
class PlayerMatchStat:
    """单场里单个玩家的统计。"""

    match_id: str
    player_name: str
    player_account_id: str
    team_index: int
    source_team_id: int | None
    placement: int
    kills: int
    assists: int
    damage_dealt: float
    time_survived: float
    dbnos: int
    headshot_kills: int

    def to_dict(self) -> dict[str, Any]:
        """导出为 DataFrame 可直接使用的字典。"""
        return asdict(self)


@dataclass
class TeamSummary:
    """单场里单个队伍的汇总统计。"""

    match_id: str
    team_index: int
    source_team_id: int | None
    rank: int | None
    won: bool
    player_count: int
    player_names: list[str]
    total_kills: int
    total_damage: float

    def to_dict(self) -> dict[str, Any]:
        """把玩家名单转成逗号分隔字符串，便于导出。"""
        data = asdict(self)
        data["player_names"] = ", ".join(self.player_names)
        return data


@dataclass
class SeatTemplateRow:
    """座位模板中的单行定义。"""

    round_no: int
    team_no: int
    seat_no: int
    expected_name: str
    expected_account_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """导出为字典。"""
        return asdict(self)


@dataclass
class SeatAuditRow:
    """座位核验结果中的单行记录。"""

    round_no: int
    team_no: int
    seat_no: int
    expected_name: str
    actual_name: str
    status: str
    reason: str
    matched_team_index: int | None

    def to_dict(self) -> dict[str, Any]:
        """导出为字典。"""
        return asdict(self)


