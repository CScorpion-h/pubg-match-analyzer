"""PUBG 官方 API 的基础封装。"""

from __future__ import annotations

from typing import Any

import requests


class PubgAPIError(RuntimeError):
    """PUBG API 请求失败时抛出的统一异常。"""


class PubgAPIClient:
    """负责访问 players、matches 和 telemetry 接口。"""

    def __init__(self, platform: str, api_key: str = "", timeout: int = 30) -> None:
        self.platform = platform
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "pubg-fans-match-tool/0.1"})

    def _request_json(
        self,
        url: str,
        *,
        accept: str,
        params: dict[str, Any] | None = None,
        require_auth: bool = False,
    ) -> Any:
        """发送 GET 请求并返回 JSON 结果。"""
        headers = {"Accept": accept}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif require_auth:
            raise PubgAPIError("读取玩家信息需要 API Key，请先在“系统设置”里填写 PUBG API Key。")

        resp = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
        if resp.status_code >= 400:
            detail = resp.text[:300].replace("\n", " ")
            raise PubgAPIError(f"HTTP {resp.status_code}: {detail}")
        return resp.json()

    def get_player_by_name(self, player_name: str) -> dict[str, Any]:
        """按玩家昵称读取玩家对象。"""
        payload = self._request_json(
            f"https://api.pubg.com/shards/{self.platform}/players",
            accept="application/vnd.api+json",
            params={"filter[playerNames]": player_name},
            require_auth=True,
        )
        data = payload.get("data") or []
        if not data:
            raise PubgAPIError(f"未找到玩家：{player_name}")
        return data[0]

    def get_recent_match_ids(self, player_name: str, limit: int) -> list[str]:
        """读取指定玩家最近的 match_id 列表。"""
        player = self.get_player_by_name(player_name)
        relationships = player.get("relationships") or {}
        matches = ((relationships.get("matches") or {}).get("data") or [])[:limit]
        return [item["id"] for item in matches if isinstance(item, dict) and item.get("id")]

    def get_match(self, match_id: str) -> dict[str, Any]:
        """读取单场对局的 matches 接口返回。"""
        return self._request_json(
            f"https://api.pubg.com/shards/{self.platform}/matches/{match_id}",
            accept="application/vnd.api+json",
            require_auth=False,
        )

    def get_telemetry(self, telemetry_url: str) -> list[dict[str, Any]]:
        """读取 telemetry 事件数组。"""
        data = self._request_json(
            telemetry_url,
            accept="application/json",
            require_auth=False,
        )
        if not isinstance(data, list):
            raise PubgAPIError("Telemetry 返回结构不是事件数组。")
        return data


