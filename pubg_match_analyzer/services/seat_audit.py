"""按 roster 规则进行座位模板核验。"""

from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from io import BytesIO

import pandas as pd

from pubg_match_analyzer.core.constants import normalize_player_name
from pubg_match_analyzer.core.models import SeatAuditRow, SeatTemplateRow, TeamSummary


REQUIRED_TEMPLATE_COLUMNS = ["round_no", "team_no", "seat_no", "expected_name"]


def load_seat_template(uploaded_file) -> tuple[pd.DataFrame, list[SeatTemplateRow]]:
    """读取上传的 CSV/XLSX 座位模板并转换成标准行结构。"""
    file_name = uploaded_file.name.lower()
    payload = uploaded_file.getvalue()
    if file_name.endswith(".csv"):
        df = pd.read_csv(BytesIO(payload))
    else:
        df = pd.read_excel(BytesIO(payload))

    missing = [col for col in REQUIRED_TEMPLATE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"座位模板缺少必要列：{', '.join(missing)}")

    if "expected_account_id" not in df.columns:
        df["expected_account_id"] = ""

    rows = [
        SeatTemplateRow(
            round_no=int(row["round_no"]),
            team_no=int(row["team_no"]),
            seat_no=int(row["seat_no"]),
            expected_name=str(row["expected_name"] or ""),
            expected_account_id=str(row.get("expected_account_id") or ""),
        )
        for _, row in df.iterrows()
    ]
    rows.sort(key=lambda item: (item.round_no, item.team_no, item.seat_no))
    return df, rows


def build_alias_lookup(alias_df: pd.DataFrame | None) -> dict[str, str]:
    """把别名映射表转换成规范名查找字典。"""
    if alias_df is None or alias_df.empty:
        return {}
    if "raw_name" not in alias_df.columns or "canonical_name" not in alias_df.columns:
        return {}

    mapping: dict[str, str] = {}
    for _, row in alias_df.iterrows():
        raw_name = normalize_player_name(str(row["raw_name"] or ""))
        canonical_name = normalize_player_name(str(row["canonical_name"] or ""))
        if raw_name and canonical_name:
            mapping[raw_name] = canonical_name
    return mapping


def _canonical(name: str, alias_lookup: dict[str, str]) -> str:
    """按别名映射返回一个名字的规范键。"""
    key = normalize_player_name(name)
    return alias_lookup.get(key, key)


def _best_team_assignment(
    template_groups: list[list[SeatTemplateRow]],
    actual_teams: list[TeamSummary],
    alias_lookup: dict[str, str],
) -> list[int]:
    """用最大交集分数给模板队伍和实际队伍做一一分配。"""
    size = max(len(template_groups), len(actual_teams))
    padded_templates = template_groups + [[] for _ in range(size - len(template_groups))]
    padded_actual = actual_teams + [
        TeamSummary(
            match_id="",
            team_index=index + 1,
            source_team_id=None,
            rank=None,
            won=False,
            player_count=0,
            player_names=[],
            total_kills=0,
            total_damage=0.0,
        )
        for index in range(size - len(actual_teams))
    ]

    scores = []
    for group in padded_templates:
        expected = {_canonical(row.expected_name, alias_lookup) for row in group if row.expected_name}
        row_scores = []
        for team in padded_actual:
            actual = {_canonical(name, alias_lookup) for name in team.player_names if name}
            row_scores.append(len(expected & actual))
        scores.append(row_scores)

    @lru_cache(maxsize=None)
    def dp(group_idx: int, used_mask: int) -> tuple[int, tuple[int, ...]]:
        if group_idx == size:
            return 0, ()
        best_score = -1
        best_path: tuple[int, ...] = ()
        for team_idx in range(size):
            if used_mask & (1 << team_idx):
                continue
            sub_score, sub_path = dp(group_idx + 1, used_mask | (1 << team_idx))
            total = scores[group_idx][team_idx] + sub_score
            if total > best_score:
                best_score = total
                best_path = (team_idx,) + sub_path
        return best_score, best_path

    _, path = dp(0, 0)
    return list(path[: len(template_groups)])


def audit_seat_template(
    template_rows: list[SeatTemplateRow],
    actual_teams: list[TeamSummary],
    alias_df: pd.DataFrame | None = None,
) -> tuple[list[SeatAuditRow], list[str]]:
    """根据模板和实际 roster 生成座位核验结果。"""
    alias_lookup = build_alias_lookup(alias_df)
    rows_by_team: dict[int, list[SeatTemplateRow]] = defaultdict(list)
    for row in template_rows:
        rows_by_team[row.team_no].append(row)

    template_groups = [sorted(group, key=lambda item: item.seat_no) for _, group in sorted(rows_by_team.items())]
    assignment = _best_team_assignment(template_groups, actual_teams, alias_lookup)

    audit_rows: list[SeatAuditRow] = []
    unmatched_actual: list[str] = []

    for group_index, group in enumerate(template_groups):
        actual_team = actual_teams[assignment[group_index]] if assignment[group_index] < len(actual_teams) else None
        actual_names = list(actual_team.player_names) if actual_team else []
        actual_counter = Counter(_canonical(name, alias_lookup) for name in actual_names if name)
        actual_name_by_key = {
            _canonical(name, alias_lookup): name for name in actual_names if _canonical(name, alias_lookup)
        }

        for seat in group:
            expected_key = _canonical(seat.expected_name, alias_lookup)
            if expected_key and actual_counter[expected_key] > 0:
                actual_counter[expected_key] -= 1
                audit_rows.append(
                    SeatAuditRow(
                        round_no=seat.round_no,
                        team_no=seat.team_no,
                        seat_no=seat.seat_no,
                        expected_name=seat.expected_name,
                        actual_name=actual_name_by_key.get(expected_key, seat.expected_name),
                        status="green",
                        reason="原报名玩家命中该队伍实际名单",
                        matched_team_index=actual_team.team_index if actual_team else None,
                    )
                )
                continue

            replacement_key = next((key for key, count in actual_counter.items() if count > 0), "")
            if replacement_key:
                actual_counter[replacement_key] -= 1
                audit_rows.append(
                    SeatAuditRow(
                        round_no=seat.round_no,
                        team_no=seat.team_no,
                        seat_no=seat.seat_no,
                        expected_name=seat.expected_name,
                        actual_name=actual_name_by_key.get(replacement_key, ""),
                        status="yellow",
                        reason="该队伍存在其他实际参赛玩家，已回填该位置",
                        matched_team_index=actual_team.team_index if actual_team else None,
                    )
                )
            else:
                audit_rows.append(
                    SeatAuditRow(
                        round_no=seat.round_no,
                        team_no=seat.team_no,
                        seat_no=seat.seat_no,
                        expected_name=seat.expected_name,
                        actual_name="",
                        status="red",
                        reason="该队伍实际人数不足，该位置清空",
                        matched_team_index=actual_team.team_index if actual_team else None,
                    )
                )

        for key, count in actual_counter.items():
            if count <= 0:
                continue
            for _ in range(count):
                unmatched_actual.append(actual_name_by_key.get(key, key))

    return audit_rows, unmatched_actual


