"""Quiet-time PWM fan speed cap for RoomMind."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..const import make_roommind_context

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class QuietTimeManager:
    """Caps configured fan.* entities to a max speed while a quiet-time schedule is active."""

    async def async_apply(self, hass: HomeAssistant, room: dict, area_id: str) -> None:
        """Clamp any room fan above its quiet-time cap while the quiet schedule is on."""
        schedule_entity_id = room.get("quiet_schedule_entity", "")
        fans = room.get("fans", [])
        if not schedule_entity_id or not fans:
            return

        schedule_state = hass.states.get(schedule_entity_id)
        if schedule_state is None or schedule_state.state != "on":
            return  # not in a quiet window (or entity missing/unavailable)

        for fan in fans:
            entity_id = fan.get("entity_id", "")
            max_percent = fan.get("quiet_max_percent", 30)
            state = hass.states.get(entity_id)
            if state is None or state.state != "on":
                continue
            current_percent = state.attributes.get("percentage")
            if current_percent is None or current_percent <= max_percent:
                continue
            try:
                await hass.services.async_call(
                    "fan",
                    "set_percentage",
                    {"entity_id": entity_id, "percentage": max_percent},
                    blocking=True,
                    context=make_roommind_context(),
                )
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Area '%s': fan.set_percentage(%s) failed on '%s'",
                    area_id,
                    max_percent,
                    entity_id,
                    exc_info=True,
                )
