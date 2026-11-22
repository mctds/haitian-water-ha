"""传感器实体。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, NAME
from .coordinator import HaitianCoordinator


@dataclass(frozen=True, kw_only=True)
class HaitianSensorDescription(SensorEntityDescription):
    """带取值函数的实体描述。"""

    value_key: str = ""
    extra: tuple[str, ...] = ()


SENSORS: tuple[HaitianSensorDescription, ...] = (
    HaitianSensorDescription(
        key="reading",
        name="水表读数",
        value_key="reading",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:water-pump",
        extra=("last_month", "last_read_date", "last_pay_state", "cust_code", "cust_name", "cust_address"),
    ),
    HaitianSensorDescription(
        key="last_usage",
        name="上期用水量",
        value_key="last_usage",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water",
        extra=("last_month", "last_read_date"),
    ),
    HaitianSensorDescription(
        key="last_amount",
        name="上期水费",
        value_key="last_amount",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:cash",
        extra=("last_month", "last_read_date", "last_pay_state"),
    ),
    HaitianSensorDescription(
        key="unpaid",
        name="待缴金额",
        value_key="unpaid",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:cash-clock",
    ),
    HaitianSensorDescription(
        key="year_usage",
        name="本年累计用水",
        value_key="year_usage",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:chart-bar",
    ),
    HaitianSensorDescription(
        key="deposit",
        name="预存金额",
        value_key="deposit",
        native_unit_of_measurement="CNY",
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:wallet",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HaitianCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(HaitianSensor(coordinator, desc) for desc in SENSORS)


class HaitianSensor(CoordinatorEntity[HaitianCoordinator], SensorEntity):
    """单个指标实体。"""

    _attr_has_entity_name = True
    _attr_attribution = "数据来源：海天水务微信小程序"

    def __init__(
        self, coordinator: HaitianCoordinator, description: HaitianSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        cust = coordinator.entry.data.get("cust_code") or coordinator.cust_id
        self._attr_name = description.name
        self._attr_unique_id = f"{DOMAIN}_{coordinator.cust_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(coordinator.cust_id))},
            "name": f"{NAME} {cust}",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        return data.get(self.entity_description.value_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        attrs: dict[str, Any] = {
            "customer_code": data.get("cust_code"),
            "customer_name": data.get("cust_name"),
            "address": data.get("cust_address"),
        }
        for key in self.entity_description.extra:
            label = {
                "last_month": "账单月份",
                "last_read_date": "抄表日期",
                "last_pay_state": "缴费状态",
                "cust_code": "户号",
                "cust_name": "户名",
                "cust_address": "地址",
            }.get(key, key)
            attrs[label] = data.get(key)
        if self.entity_description.key == "reading":
            attrs["近12期账单"] = self.coordinator.daily_series()
        return attrs
