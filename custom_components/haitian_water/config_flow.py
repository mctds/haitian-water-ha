"""配置流程。"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HaitianApi, HaitianApiError, HaitianAuthError
from .const import (
    CONF_CUST_CODE,
    CONF_CUST_ID,
    CONF_CUST_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TENANT,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DEFAULT_TENANT,
    DOMAIN,
    MAX_SCAN_INTERVAL_HOURS,
    MIN_SCAN_INTERVAL_HOURS,
    NAME,
)

_LOGGER = logging.getLogger(__name__)

TOKEN_FIELD = selector.TextSelector(
    selector.TextSelectorConfig(multiline=True, type=selector.TextSelectorType.TEXT)
)


class HaitianWaterConfigFlow(ConfigFlow, domain=DOMAIN):
    """添加设备时的交互流程。"""

    VERSION = 1

    def __init__(self) -> None:
        self._token: str = ""
        self._tenant: str = DEFAULT_TENANT
        self._custs: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._token = str(user_input[CONF_TOKEN]).strip()
            self._tenant = (user_input.get(CONF_TENANT) or DEFAULT_TENANT).strip()
            try:
                self._custs = await self._fetch_custs()
            except HaitianAuthError:
                errors["base"] = "auth_failed"
            except HaitianApiError:
                errors["base"] = "cannot_connect"
            else:
                if not self._custs:
                    errors["base"] = "no_cust"
                elif len(self._custs) == 1:
                    return await self._async_create(self._custs[0])
                else:
                    return await self.async_step_pick()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOKEN): TOKEN_FIELD,
                    vol.Optional(CONF_TENANT, default=DEFAULT_TENANT): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "hint": "在微信「乐至海天水务」公众号 → 营业大厅 → 微网厅 登录后，"
                "可从抓包或浏览器本地存储中取得 access_token"
            },
        )

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            cust_id = str(user_input[CONF_CUST_ID])
            for cust in self._custs:
                if str(cust.get("custId")) == cust_id:
                    return await self._async_create(cust)
            return await self.async_step_pick()

        options = [
            selector.SelectOptionDict(
                value=str(cust.get("custId")),
                label=f"{cust.get('custName')} · {cust.get('custCode')} · {cust.get('custAddress') or ''}",
            )
            for cust in self._custs
        ]
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CUST_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options)
                    )
                }
            ),
        )

    async def _async_create(self, cust: dict[str, Any]) -> ConfigFlowResult:
        cust_id = str(cust.get("custId"))
        await self.async_set_unique_id(f"{DOMAIN}_{cust_id}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"{NAME} {cust.get('custCode')}",
            data={
                CONF_TOKEN: self._token,
                CONF_TENANT: self._tenant,
                CONF_CUST_ID: cust_id,
                CONF_CUST_CODE: cust.get("custCode"),
                CONF_CUST_NAME: cust.get("custName"),
            },
        )

    async def _fetch_custs(self) -> list[dict[str, Any]]:
        session = async_get_clientsession(self.hass)
        api = HaitianApi(session, token=self._token, tenant=self._tenant)
        return await api.async_validate()

    # ------------------------------------------------------------------
    #  重新授权
    # ------------------------------------------------------------------
    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = str(user_input[CONF_TOKEN]).strip()
            tenant = entry.data.get(CONF_TENANT) or DEFAULT_TENANT
            try:
                self._token = token
                self._tenant = tenant
                self._custs = await self._fetch_custs()
            except HaitianAuthError:
                errors["base"] = "auth_failed"
            except HaitianApiError:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_TOKEN: token}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): TOKEN_FIELD}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HaitianOptionsFlow()


class HaitianOptionsFlow(OptionsFlow):
    """调整刷新间隔。"""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_SCAN_INTERVAL_HOURS, max=MAX_SCAN_INTERVAL_HOURS
                        ),
                    )
                }
            ),
        )
