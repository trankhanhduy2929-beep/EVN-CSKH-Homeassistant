from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Customer
from .const import customer_device_info, scope_id
from .coordinator import EvnConfigEntry, EvnCoordinator, customer_key

PARALLEL_UPDATES = 0

TRANSLATION_KEY = "refresh"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EvnConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            EvnButton(coordinator, entry, snapshot.customer)
            for snapshot in coordinator.data.values()
        ]
    )


class EvnButton(CoordinatorEntity[EvnCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = TRANSLATION_KEY

    def __init__(
        self,
        coordinator: EvnCoordinator,
        entry: EvnConfigEntry,
        customer: Customer,
    ) -> None:
        key = customer_key(customer)
        super().__init__(coordinator, context=key)
        self._customer_key = key
        scope = (
            entry.unique_id or entry.entry_id,
            customer.management_unit,
            customer.code,
        )
        self._attr_unique_id = scope_id(*scope, None, TRANSLATION_KEY)
        self._attr_device_info = customer_device_info(scope)

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
