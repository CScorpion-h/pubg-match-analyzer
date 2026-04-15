"""报名表结构识别、字段映射和联系人查询。"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd

HEADER_OPTION_NONE = "不使用"
MAX_MANUAL_SIGNUP_CONTACT_PAIRS = 6
PLACEHOLDER_VALUES = {"", "无须作答", "已删除", "没有", "无", "nan", "none", "null"}

SUBMITTED_AT_KEYWORDS = ("提交时间",)
MODE_KEYWORDS = ("你要参加的模式", "参加的模式", "报名模式", "模式")


@dataclass
class SignupWorkbookSheet:
    """报名表中的单个工作表结构。"""

    sheet_name: str
    columns: list[str]


@dataclass
class SignupContactPair:
    """一组游戏 ID / QQ 字段映射。"""

    game_id_col: str
    qq_col: str

    def to_dict(self) -> dict[str, str]:
        """转换成可写入 session_state 的字典。"""
        return {
            "game_id_col": self.game_id_col,
            "qq_col": self.qq_col,
        }


@dataclass
class SignupSheetSchema:
    """报名表结构定义。"""

    sheet_name: str
    submitted_at_col: str = ""
    mode_col: str = ""
    contact_pairs: list[SignupContactPair] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换成可写入 session_state 的字典。"""
        return {
            "sheet_name": self.sheet_name,
            "submitted_at_col": self.submitted_at_col,
            "mode_col": self.mode_col,
            "contact_pairs": [pair.to_dict() for pair in self.contact_pairs],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "SignupSheetSchema":
        """从 session_state 中恢复 schema。"""
        if not isinstance(raw, dict):
            return cls(sheet_name="")

        pairs = []
        for item in raw.get("contact_pairs", []):
            if not isinstance(item, dict):
                continue
            game_id_col = str(item.get("game_id_col", "")).strip()
            qq_col = str(item.get("qq_col", "")).strip()
            if not game_id_col or not qq_col:
                continue
            pairs.append(SignupContactPair(game_id_col=game_id_col, qq_col=qq_col))

        return cls(
            sheet_name=str(raw.get("sheet_name", "")).strip(),
            submitted_at_col=str(raw.get("submitted_at_col", "")).strip(),
            mode_col=str(raw.get("mode_col", "")).strip(),
            contact_pairs=pairs,
        )


@dataclass
class SignupSchemaDetectionResult:
    """自动识别报名表结构的结果。"""

    schema: SignupSheetSchema
    preset_name: str
    confidence: str
    requires_manual_confirmation: bool
    matched_sheet_name: str


@dataclass
class ContactRecord:
    """报名表中的单条联系人记录。"""

    mode_name: str
    game_id: str
    normalized_game_id: str
    qq: str
    submitted_at: datetime
    submitted_at_text: str


@dataclass
class ContactResolution:
    """某个参赛玩家的 QQ 匹配结果。"""

    player_name: str
    qq: str = ""
    status: str = "no_signup"
    candidate_qqs: list[str] = field(default_factory=list)
    latest_submitted_at: str = ""


class SignupContactLookup:
    """对报名表联系人映射做标准化和查询。"""

    def __init__(self, records: list[ContactRecord]):
        self.records = records
        self._global_by_id: dict[str, list[ContactRecord]] = {}
        self._mode_by_id: dict[tuple[str, str], list[ContactRecord]] = {}
        for record in records:
            self._global_by_id.setdefault(record.normalized_game_id, []).append(record)
            if record.mode_name:
                self._mode_by_id.setdefault((record.mode_name, record.normalized_game_id), []).append(record)

    @classmethod
    def from_excel_bytes(cls, file_bytes: bytes, schema: SignupSheetSchema) -> "SignupContactLookup":
        """按 schema 定义从报名表文件字节流中提取联系人映射。"""
        dataframe = _read_signup_sheet(file_bytes, schema.sheet_name)
        records: list[ContactRecord] = []

        for _, row in dataframe.iterrows():
            mode_name = _clean_text(row.get(schema.mode_col)) if schema.mode_col else ""
            submitted_at_raw = row.get(schema.submitted_at_col) if schema.submitted_at_col else None
            submitted_at = _to_datetime(submitted_at_raw)
            submitted_at_text = _format_datetime(submitted_at)

            for pair in schema.contact_pairs:
                game_id = _clean_text(row.get(pair.game_id_col))
                if not game_id:
                    continue
                qq = _clean_text(row.get(pair.qq_col))
                records.append(
                    ContactRecord(
                        mode_name=mode_name,
                        game_id=game_id,
                        normalized_game_id=_normalize_key(game_id),
                        qq=qq,
                        submitted_at=submitted_at,
                        submitted_at_text=submitted_at_text,
                    )
                )

        return cls(records)

    def resolve(self, player_name: str, signup_mode_name: str | None) -> ContactResolution:
        """按“玩法优先，全表兜底”的规则为玩家匹配 QQ。"""
        normalized = _normalize_key(player_name)
        if not normalized:
            return ContactResolution(player_name=player_name, status="missing")

        mode_records: list[ContactRecord] = []
        if signup_mode_name:
            mode_records = self._mode_by_id.get((signup_mode_name, normalized), [])
        if mode_records:
            return _resolve_from_records(player_name, mode_records)

        global_records = self._global_by_id.get(normalized, [])
        if global_records:
            return _resolve_from_records(player_name, global_records)

        return ContactResolution(player_name=player_name, status="missing")


def build_signup_file_cache_key(file_name: str, file_bytes: bytes) -> str:
    """基于文件名和内容生成会话级缓存键。"""
    digest = hashlib.sha1(file_bytes).hexdigest()[:12]
    return f"{file_name}:{len(file_bytes)}:{digest}"


def inspect_signup_workbook(file_bytes: bytes) -> list[SignupWorkbookSheet]:
    """读取报名表结构信息，仅提取工作表与表头。"""
    excel_file = pd.ExcelFile(BytesIO(file_bytes))
    sheets: list[SignupWorkbookSheet] = []
    for sheet_name in excel_file.sheet_names:
        dataframe = excel_file.parse(sheet_name=sheet_name, nrows=0)
        sheets.append(
            SignupWorkbookSheet(
                sheet_name=sheet_name,
                columns=[str(column) for column in dataframe.columns],
            )
        )
    return sheets


def detect_signup_sheet_schema(
    file_bytes: bytes,
    workbook_sheets: list[SignupWorkbookSheet] | None = None,
) -> SignupSchemaDetectionResult:
    """按列名关键词自动识别最可能的报名表结构。"""
    sheets = workbook_sheets or inspect_signup_workbook(file_bytes)
    if not sheets:
        return SignupSchemaDetectionResult(
            schema=SignupSheetSchema(sheet_name=""),
            preset_name="未识别",
            confidence="低",
            requires_manual_confirmation=True,
            matched_sheet_name="",
        )

    best_score = -1
    best_result: SignupSchemaDetectionResult | None = None
    for sheet in sheets:
        schema, score, preset_name = _detect_sheet_schema(sheet)
        confidence = _score_to_confidence(score)
        requires_manual = len(schema.contact_pairs) == 0 or confidence == "低"
        result = SignupSchemaDetectionResult(
            schema=schema,
            preset_name=preset_name,
            confidence=confidence,
            requires_manual_confirmation=requires_manual,
            matched_sheet_name=sheet.sheet_name,
        )
        if score > best_score:
            best_score = score
            best_result = result

    return best_result or SignupSchemaDetectionResult(
        schema=SignupSheetSchema(sheet_name=sheets[0].sheet_name),
        preset_name="未识别",
        confidence="低",
        requires_manual_confirmation=True,
        matched_sheet_name=sheets[0].sheet_name,
    )


def validate_signup_sheet_schema(schema: SignupSheetSchema, workbook_sheets: list[SignupWorkbookSheet]) -> None:
    """校验 schema 是否能在当前报名表中使用。"""
    if not schema.sheet_name:
        raise ValueError("未指定报名表工作表。")

    sheet_map = {sheet.sheet_name: sheet for sheet in workbook_sheets}
    sheet = sheet_map.get(schema.sheet_name)
    if sheet is None:
        raise ValueError("所选工作表不存在。")

    available = set(sheet.columns)
    if schema.submitted_at_col and schema.submitted_at_col not in available:
        raise ValueError("提交时间列不存在。")
    if schema.mode_col and schema.mode_col not in available:
        raise ValueError("玩法列不存在。")
    if not schema.contact_pairs:
        raise ValueError("至少需要 1 组联系人列。")

    for index, pair in enumerate(schema.contact_pairs, start=1):
        if pair.game_id_col not in available:
            raise ValueError(f"第 {index} 组联系人的游戏ID列不存在。")
        if pair.qq_col not in available:
            raise ValueError(f"第 {index} 组联系人的 QQ 列不存在。")
        if pair.game_id_col == pair.qq_col:
            raise ValueError(f"第 {index} 组联系人列不能把游戏ID列和 QQ 列设为同一列。")


def extract_signup_mode_names(file_bytes: bytes, schema: SignupSheetSchema) -> list[str]:
    """按已确认 schema 提取报名表中的玩法列表。"""
    if not schema.mode_col:
        return []

    dataframe = _read_signup_sheet(file_bytes, schema.sheet_name)
    if schema.mode_col not in dataframe.columns:
        raise ValueError("当前报名表映射未找到玩法列。")

    values = []
    seen: set[str] = set()
    for value in dataframe[schema.mode_col]:
        mode_name = _clean_text(value)
        if not mode_name or mode_name in seen:
            continue
        seen.add(mode_name)
        values.append(mode_name)
    return values


def _detect_sheet_schema(sheet: SignupWorkbookSheet) -> tuple[SignupSheetSchema, int, str]:
    """针对单个工作表计算最可能的 schema 和得分。"""
    columns = sheet.columns
    submitted_at_col = _best_matching_column(columns, SUBMITTED_AT_KEYWORDS)
    mode_col = _best_matching_column(columns, MODE_KEYWORDS)
    contact_pairs = _detect_contact_pairs(columns)
    schema = SignupSheetSchema(
        sheet_name=sheet.sheet_name,
        submitted_at_col=submitted_at_col,
        mode_col=mode_col,
        contact_pairs=contact_pairs,
    )

    score = len(contact_pairs) * 3
    if mode_col:
        score += 2
    if submitted_at_col:
        score += 1

    if len(contact_pairs) >= 2:
        preset_name = "组队报名结构"
    elif len(contact_pairs) == 1:
        preset_name = "单人报名结构"
    else:
        preset_name = "未识别"

    return schema, score, preset_name


def _score_to_confidence(score: int) -> str:
    """把识别分数转换成页面展示的置信度。"""
    if score >= 6:
        return "高"
    if score >= 3:
        return "中"
    return "低"


def _best_matching_column(columns: list[str], keywords: tuple[str, ...]) -> str:
    """按关键词命中情况选择最佳列。"""
    best_column = ""
    best_score = -1
    normalized_keywords = [_normalize_header(keyword) for keyword in keywords]
    for column in columns:
        normalized = _normalize_header(column)
        score = 0
        for keyword in normalized_keywords:
            if not keyword:
                continue
            if normalized == keyword:
                score = max(score, 100 + len(keyword))
            elif keyword in normalized:
                score = max(score, len(keyword))
        if score > best_score:
            best_score = score
            best_column = column
    return best_column if best_score > 0 else ""


def _detect_contact_pairs(columns: list[str]) -> list[SignupContactPair]:
    """从表头中推导联系人列组。"""
    id_by_token: dict[str, str] = {}
    qq_by_token: dict[str, str] = {}

    for column in columns:
        normalized = _normalize_header(column)
        if not normalized:
            continue

        token = _extract_contact_token(normalized)
        if not token:
            continue

        if _is_game_id_header(normalized) and token not in id_by_token:
            id_by_token[token] = column
        elif _is_qq_header(normalized) and token not in qq_by_token:
            qq_by_token[token] = column

    tokens = sorted(set(id_by_token) | set(qq_by_token), key=_sort_contact_token)
    pairs: list[SignupContactPair] = []
    for token in tokens:
        game_id_col = id_by_token.get(token, "")
        qq_col = qq_by_token.get(token, "")
        if game_id_col and qq_col:
            pairs.append(SignupContactPair(game_id_col=game_id_col, qq_col=qq_col))
    return pairs


def _extract_contact_token(normalized_header: str) -> str:
    """把联系人字段归一成可配对的 token。"""
    if "队友" in normalized_header:
        match = re.search(r"队友(\d+)", normalized_header)
        if match:
            return f"队友{match.group(1)}"
        return ""

    if _is_game_id_header(normalized_header) or _is_qq_header(normalized_header):
        return "本人"

    return ""


def _sort_contact_token(token: str) -> tuple[int, int]:
    """保证联系人列按“本人、队友1、队友2...”排序。"""
    if token == "本人":
        return (0, 0)
    match = re.search(r"(\d+)", token)
    if match:
        return (1, int(match.group(1)))
    return (2, 0)


def _normalize_header(value: str | None) -> str:
    """统一列名字符串，便于关键词匹配。"""
    if value is None:
        return ""
    normalized = str(value).strip().lower()
    for old in (" ", "_", "-", "（", "）", "(", ")", "[", "]", "【", "】", "：", ":", "，", ",", ".", "。"):
        normalized = normalized.replace(old, "")
    return normalized


def _is_game_id_header(normalized_header: str) -> bool:
    """判断一个列名是否是游戏 ID 列。"""
    return "游戏id" in normalized_header


def _is_qq_header(normalized_header: str) -> bool:
    """判断一个列名是否是 QQ 列。"""
    return "qq" in normalized_header


def _read_signup_sheet(file_bytes: bytes, sheet_name: str) -> pd.DataFrame:
    """读取指定报名表工作表。"""
    return pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name)


def _normalize_key(value: str | None) -> str:
    """把游戏 ID 归一成可匹配的键。"""
    if not value:
        return ""
    return str(value).strip().lower()


def _clean_text(value: Any) -> str:
    """清洗 Excel 单元格文本，过滤常见占位值。"""
    if value is None or pd.isna(value):
        return ""
    raw = str(value).strip()
    normalized = raw.replace(" ", "").lower()
    if normalized in PLACEHOLDER_VALUES:
        return ""
    return raw


def _to_datetime(value: Any) -> datetime:
    """把 Excel 里的提交时间安全转换成 datetime。"""
    if isinstance(value, datetime):
        return value
    try:
        ts = pd.to_datetime(value)
    except Exception:
        return datetime.min
    if pd.isna(ts):
        return datetime.min
    return ts.to_pydatetime()


def _format_datetime(value: datetime) -> str:
    """格式化时间用于冲突表展示。"""
    if value == datetime.min:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _resolve_from_records(player_name: str, records: list[ContactRecord]) -> ContactResolution:
    """从一组报名记录里解析最终联系人结果。"""
    non_empty = [record for record in records if record.qq]
    if not non_empty:
        return ContactResolution(player_name=player_name, status="missing")

    candidate_qqs = sorted({record.qq for record in non_empty})
    latest_record = max(non_empty, key=lambda item: item.submitted_at)
    if len(candidate_qqs) > 1:
        return ContactResolution(
            player_name=player_name,
            qq=latest_record.qq,
            status="conflict",
            candidate_qqs=candidate_qqs,
            latest_submitted_at=latest_record.submitted_at_text,
        )

    return ContactResolution(
        player_name=player_name,
        qq=latest_record.qq,
        status="matched",
        latest_submitted_at=latest_record.submitted_at_text,
    )
