"""海天水务（四川乐至海天等）微信小程序数据接口。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from .const import (
    BASE_URL,
    CLIENT_ID,
    CLIENT_SECRET,
    CONF_TOKEN,
    REQUEST_TIMEOUT,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class HaitianAuthError(Exception):
    """令牌失效且无法自动续期。"""


class HaitianApiError(Exception):
    """接口返回异常。"""


class HaitianApi:
    """与 tchal.haitianshuiwu.cn 通信的轻量封装。"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str,
        tenant: str,
    ) -> None:
        self._session = session
        self.token = token
        self.tenant = tenant
        self._lock = asyncio.Lock()
        self.last_refresh = time.time()

    # ------------------------------------------------------------------
    #  基础请求
    # ------------------------------------------------------------------
    @property
    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        retry: bool = True,
    ) -> Any:
        url = f"{BASE_URL}{path}"
        try:
            async with self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status == 401:
                    if retry and await self.relogin():
                        return await self._request(
                            method, path, params=params, json_body=json_body, retry=False
                        )
                    raise HaitianAuthError("令牌已失效，需要重新授权")
                text = await resp.text()
                if resp.status >= 400:
                    raise HaitianApiError(f"HTTP {resp.status}: {text[:200]}")
                if not text:
                    return None
                try:
                    return await resp.json(content_type=None)
                except Exception:  # noqa: BLE001
                    return text
        except aiohttp.ClientError as err:
            raise HaitianApiError(f"网络错误: {err}") from err

    # ------------------------------------------------------------------
    #  登录 / 续期
    # ------------------------------------------------------------------
    async def relogin(self) -> bool:
        """用现有令牌换一枚新令牌；失败返回 False。"""
        async with self._lock:
            payload = {
                "clientId": CLIENT_ID,
                "clientSecret": CLIENT_SECRET,
                "tenantName": self.tenant,
            }
            try:
                async with self._session.post(
                    f"{BASE_URL}/api/user/relogin",
                    json=payload,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.debug("relogin 失败 status=%s", resp.status)
                        return False
                    data = await resp.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.debug("relogin 异常: %s", err)
                return False

            token = (data or {}).get("access_token") if isinstance(data, dict) else None
            if not token:
                _LOGGER.debug("relogin 返回异常: %s", str(data)[:200])
                return False
            self.token = token
            self.last_refresh = time.time()
            _LOGGER.debug("令牌续期成功")
            return True

    # ------------------------------------------------------------------
    #  业务接口
    # ------------------------------------------------------------------
    async def get_custs(self) -> list[dict[str, Any]]:
        """当前微信账号下绑定的户号列表。"""
        data = await self._request("GET", "/api/app/smallAppCust/list")
        return data if isinstance(data, list) else []

    async def get_charges(self, cust_id: int | str, count: int = 13) -> dict[str, Any]:
        """账单/抄表明细，最新一期的 index 为 0。"""
        data = await self._request(
            "GET",
            f"/api/app/weChatCharge/{cust_id}/custCharge",
            params={"billMonth": 0, "SkipCount": 0, "MaxResultCount": count},
        )
        return data if isinstance(data, dict) else {}

    async def async_validate(self) -> list[dict[str, Any]]:
        """校验令牌是否可用，返回户号列表。"""
        return await self.get_custs()

    @staticmethod
    def entry_token(entry_data: dict[str, Any]) -> str:
        return str(entry_data.get(CONF_TOKEN) or "")
