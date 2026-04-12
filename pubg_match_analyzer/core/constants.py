"""项目常量和展示映射。"""

from __future__ import annotations


DEFAULT_PLATFORM = "steam"
DEFAULT_RECENT_MATCH_LIMIT = 30
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


