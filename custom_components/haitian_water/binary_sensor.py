"""欠费状态二元传感器。"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, NAME
from .coordinator import HaitianCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HaitianCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HaitianArrearsSensor(coordinator)])


class HaitianArrearsSensor(CoordinatorEntity[HaitianCoordinator], BinarySensorEntity):
    """是否存在未缴账单。"""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle-outline"
    _attr_has_entity_name = True

    def __init__(self, coordinator: HaitianCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "欠费"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.cust_id}_arrears"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(coordinator.cust_id))},
            "name": f"{NAME} {coordinator.entry.data.get('cust_code') or coordinator.cust_id}",
            "manufacturer": MANUFACTURER,
        }

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return (data.get("unpaid") or 0) > 0

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {
            "待缴金额": data.get("unpaid"),
            "最近账单月份": data.get("last_month"),
            "最近缴费状态": data.get("last_pay_state"),
        }
