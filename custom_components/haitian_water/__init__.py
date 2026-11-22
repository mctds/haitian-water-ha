"""海天水务集成入口。"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from datetime import timedelta

from .api import HaitianApi, HaitianApiError, HaitianAuthError
from .const import (
    CONF_CUST_ID,
    CONF_TENANT,
    CONF_TOKEN,
    DEFAULT_TENANT,
    DOMAIN,
    TOKEN_KEEPALIVE_SECONDS,
)
from .coordinator import HaitianCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = HaitianApi(
        session,
        token=str(entry.data.get(CONF_TOKEN) or ""),
        tenant=entry.data.get(CONF_TENANT) or DEFAULT_TENANT,
    )

    try:
        await api.async_validate()
    except HaitianAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except HaitianApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = HaitianCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async def _keepalive(_now) -> None:
        """滚动续期令牌，并写回条目以便重启后仍可用。"""
        if not await api.relogin():
            _LOGGER.warning("令牌续期失败，下次取数将触发重新授权")
            return
        if api.token != entry.data.get(CONF_TOKEN):
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_TOKEN: api.token}
            )

    entry.async_on_unload(
        async_track_time_interval(
            hass, _keepalive, timedelta(seconds=TOKEN_KEEPALIVE_SECONDS)
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
