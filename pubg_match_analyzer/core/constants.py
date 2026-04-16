"""项目常量和展示映射。"""

from __future__ import annotations


DEFAULT_PLATFORM = "steam"
DEFAULT_RECENT_MATCH_LIMIT = 100
MAX_SEARCH_WINDOW_LIMIT = 1000
SEARCH_WINDOW_STEP = 50
MIN_HIT_PLAYER_COUNT = 2

# 这些前缀用于从 gameMode 中识别常见自定义房分类。
CUSTOM_MODE_PREFIXES = {
    "esports": "esports-",
    "normal": "normal-",
    "war": "war-",
    "zombie": "zombie-",
    "conquest": "conquest-",
}

GAME_MODE_CATEGORY_LABELS = {
    "normal": "经典模式",
    "ibr": "激战大逃杀",
    "conquest": "热点模式",
    "esports": "电竞模式",
    "war": "战争模式",
    "zombie": "僵尸模式",
    "lab": "实验室",
    "tdm": "团队殊死战",
}

TEAM_SIZE_LABELS = {
    "solo": "单排",
    "duo": "双排",
    "squad": "四排",
}

PERSPECTIVE_LABELS = {
    "tpp": "TPP",
    "fpp": "FPP",
}

MAP_NAME_LABELS = {
    "Baltic_Main": "艾伦格",
    "Erangel_Main": "艾伦格（旧）",
    "Desert_Main": "米拉玛",
    "Savage_Main": "萨诺",
    "DihorOtok_Main": "维寒迪",
    "Summerland_Main": "卡拉金",
    "Chimera_Main": "帕拉莫",
    "Heaven_Main": "褐湾",
    "Tiger_Main": "泰戈",
    "Kiki_Main": "帝斯顿",
    "Neon_Main": "荣都",
    "Range_Main": "训练场",
}

CANDIDATE_MATCH_COLUMN_LABELS = {
    "match_id": "对局ID",
    "started_at": "开始时间",
    "map_name": "地图",
    "game_mode": "模式",
    "player_count": "参赛人数",
    "hit_input_count": "命中输入人数",
    "hit_rate": "命中率",
    "game_mode_category": "模式分类",
    "hit_input_names": "命中玩家名单",
}

MATCH_OVERVIEW_COLUMN_LABELS = {
    "match_id": "对局ID",
    "started_at": "开始时间",
    "duration": "对局时长",
    "map_name": "地图",
    "game_mode": "模式",
    "game_mode_category": "模式分类",
    "match_type": "对局类型",
    "is_supported_custom_match": "是否为自定义房",
    "player_count": "参赛人数",
    "roster_count": "队伍数",
    "telemetry_url": "Telemetry链接",
}

PLAYER_STATS_COLUMN_LABELS = {
    "match_id": "对局ID",
    "player_name": "玩家昵称",
    "player_account_id": "玩家账号ID",
    "team_index": "队伍序号",
    "source_team_id": "原始队伍ID",
    "placement": "名次",
    "kills": "淘汰",
    "assists": "助攻",
    "damage_dealt": "总伤害",
    "time_survived": "存活时长",
    "dbnos": "击倒数",
    "headshot_kills": "爆头淘汰",
}

TEAM_SUMMARY_COLUMN_LABELS = {
    "match_id": "对局ID",
    "team_index": "队伍序号",
    "source_team_id": "原始队伍ID",
    "rank": "队伍排名",
    "won": "是否获胜",
    "player_count": "队员人数",
    "player_names": "队员名单",
    "total_kills": "队伍总淘汰",
    "total_damage": "队伍总伤害",
}

EXPORT_SHEET_LABELS = {
    "match_overview": "对局概览",
    "player_stats": "玩家明细",
    "team_summary": "队伍汇总",
}


def normalize_player_name(name: str | None) -> str:
    """把昵称转成统一的小写键，便于去重和匹配。"""
    if not name:
        return ""
    return name.strip().lower()


def display_map_name(map_name: str | None) -> str:
    """把 PUBG 原始地图代码映射成页面展示名称。"""
    if not map_name:
        return ""
    return MAP_NAME_LABELS.get(str(map_name), str(map_name))


def classify_custom_match_category(game_mode: str | None) -> str | None:
    """从 gameMode 中推导当前对局的大类编码。"""
    if not game_mode:
        return None

    game_mode = str(game_mode)
    if game_mode == "tdm":
        return "tdm"
    if game_mode.startswith("lab-"):
        return "lab"
    if game_mode.startswith("ibr-"):
        return "ibr"

    for category, prefix in CUSTOM_MODE_PREFIXES.items():
        if game_mode.startswith(prefix):
            return category

    # 基础 solo/duo/squad 也统一归到经典模式。
    base_mode = game_mode.split("-", 1)[0]
    if base_mode in TEAM_SIZE_LABELS:
        return "normal"
    return base_mode


def display_game_mode_category(category_code: str | None) -> str:
    """把对局分类编码映射成中文名称。"""
    if not category_code:
        return ""
    return GAME_MODE_CATEGORY_LABELS.get(str(category_code), str(category_code))


def display_game_mode(game_mode: str | None) -> str:
    """把原始 gameMode 映射成适合页面展示的模式描述。"""
    if not game_mode:
        return ""

    game_mode = str(game_mode)
    if game_mode == "tdm":
        return "-"

    parts = game_mode.split("-")
    category_code = classify_custom_match_category(game_mode)
    perspective_code = "fpp" if parts[-1] == "fpp" else "tpp"
    perspective_label = PERSPECTIVE_LABELS.get(perspective_code, perspective_code.upper())

    if category_code == "lab":
        return perspective_label

    filtered_parts = [
        part for part in parts if part not in {"normal", "conquest", "esports", "war", "zombie", "ibr", "fpp"}
    ]
    team_size_code = next((part for part in filtered_parts if part in TEAM_SIZE_LABELS), "")
    if team_size_code:
        return f"{TEAM_SIZE_LABELS[team_size_code]} {perspective_label}"

    return game_mode


def is_custom_match(match_type: str | None, is_custom_match_flag: bool | None = None) -> bool:
    """统一判断一个 match 是否属于自定义房。"""
    if str(match_type or "").lower() == "custom":
        return True
    if is_custom_match_flag is True:
        return True
    return False


def format_duration_mmss(seconds: int | float | None) -> str:
    """把秒数格式化成“X分Y秒”展示。"""
    if seconds is None:
        return ""

    try:
        total_seconds = max(0, int(round(float(seconds))))
    except (TypeError, ValueError):
        return ""

    minutes, remain_seconds = divmod(total_seconds, 60)
    return f"{minutes}分{remain_seconds}秒"


