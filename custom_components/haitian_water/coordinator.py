"""数据协调器。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import HaitianApi, HaitianApiError, HaitianAuthError
from .const import (
    BILL_HISTORY_COUNT,
    CONF_CUST_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _f(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _month_label(bill_month: Any) -> str | None:
    try:
        raw = str(int(bill_month))
    except (TypeError, ValueError):
        return None
    if len(raw) != 6:
        return None
    return f"{raw[:4]}-{raw[4:]}"


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None


class HaitianCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """拉取账单并整理成实体需要的结构。"""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: HaitianApi) -> None:
        hours = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{entry.data.get(CONF_CUST_ID)}",
            update_interval=timedelta(hours=float(hours)),
        )
        self.entry = entry
        self.api = api
        self.cust_id = entry.data.get(CONF_CUST_ID)
        self._cust_cache: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            charges = await self.api.get_charges(self.cust_id, BILL_HISTORY_COUNT)
        except HaitianAuthError as err:
            raise UpdateFailed(str(err)) from err
        except HaitianApiError as err:
            raise UpdateFailed(str(err)) from err

        bills = charges.get("items") or []
        if not isinstance(bills, list):
            bills = []

        cust = await self._async_cust()
        latest = bills[0] if bills else {}

        now_year = dt_util.now().year
        year_usage = 0.0
        for bill in bills:
            month = str(bill.get("billMonth") or "")
            if month.startswith(str(now_year)):
                year_usage += _f(bill.get("billWater")) or 0.0

        unpaid = 0.0
        for bill in bills:
            if bill.get("payState") == 0:
                unpaid += _f(bill.get("extendedAmount")) or 0.0

        return {
            "cust": cust,
            "bills": bills,
            "latest": latest,
            "reading": _f(latest.get("reading")),
            "last_usage": _f(latest.get("billWater")),
            "last_amount": _f(latest.get("extendedAmount")),
            "last_month": _month_label(latest.get("billMonth")),
            "last_read_date": latest.get("readDate"),
            "last_pay_state": latest.get("payStateName"),
            "year_usage": round(year_usage, 2),
            "unpaid": round(unpaid, 2),
            "cust_code": cust.get("custCode") or self.entry.data.get("cust_code"),
            "cust_name": cust.get("custName") or self.entry.data.get("cust_name"),
            "cust_address": cust.get("custAddress"),
            "deposit": _f(cust.get("deposit")),
            "fetched_at": dt_util.utcnow(),
        }

    async def _async_cust(self) -> dict[str, Any]:
        """户号基础信息来自 list 接口；失败时退回缓存。"""
        if self._cust_cache:
            return self._cust_cache
        try:
            custs = await self.api.get_custs()
        except (HaitianAuthError, HaitianApiError):
            return {}
        for item in custs:
            if str(item.get("custId")) == str(self.cust_id):
                self._cust_cache = item
                return item
        if len(custs) == 1:
            self._cust_cache = custs[0]
            return self._cust_cache
        return {}

    def daily_series(self) -> list[dict[str, Any]]:
        """给属性用的近几期账单摘要。"""
        bills = (self.data or {}).get("bills") or []
        out = []
        for bill in bills[:12]:
            out.append(
                {
                    "month": _month_label(bill.get("billMonth")),
                    "reading": _f(bill.get("reading")),
                    "usage": _f(bill.get("billWater")),
                    "amount": _f(bill.get("extendedAmount")),
                    "read_date": bill.get("readDate"),
                    "state": bill.get("payStateName"),
                }
            )
        return out
