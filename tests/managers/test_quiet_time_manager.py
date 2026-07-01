"""Tests for quiet_time_manager.py — PWM fan speed cap during quiet hours."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.roommind.managers.quiet_time_manager import QuietTimeManager


def _state(state, attributes=None):
    s = MagicMock()
    s.state = state
    s.attributes = attributes or {}
    return s


@pytest.fixture
def mgr():
    return QuietTimeManager()


def _room(**overrides):
    room = {
        "quiet_schedule_entity": "schedule.living_room_quiet",
        "fans": [{"entity_id": "fan.living_room_convector", "quiet_max_percent": 30}],
    }
    room.update(overrides)
    return room


@pytest.mark.asyncio
async def test_no_schedule_entity_is_noop(hass, mgr):
    hass.services.async_call = AsyncMock()
    await mgr.async_apply(hass, _room(quiet_schedule_entity=""), "living_room")
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_no_fans_configured_is_noop(hass, mgr):
    hass.services.async_call = AsyncMock()
    await mgr.async_apply(hass, _room(fans=[]), "living_room")
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_off_is_noop(hass, mgr):
    hass.states.get = MagicMock(return_value=_state("off"))
    hass.services.async_call = AsyncMock()
    await mgr.async_apply(hass, _room(), "living_room")
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_entity_missing_is_noop(hass, mgr):
    hass.states.get = MagicMock(return_value=None)
    hass.services.async_call = AsyncMock()
    await mgr.async_apply(hass, _room(), "living_room")
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_fan_already_within_cap_is_noop(hass, mgr):
    def states_get(entity_id):
        if entity_id == "schedule.living_room_quiet":
            return _state("on")
        if entity_id == "fan.living_room_convector":
            return _state("on", {"percentage": 20})
        return None

    hass.states.get = MagicMock(side_effect=states_get)
    hass.services.async_call = AsyncMock()
    await mgr.async_apply(hass, _room(), "living_room")
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_fan_above_cap_gets_clamped(hass, mgr):
    def states_get(entity_id):
        if entity_id == "schedule.living_room_quiet":
            return _state("on")
        if entity_id == "fan.living_room_convector":
            return _state("on", {"percentage": 80})
        return None

    hass.states.get = MagicMock(side_effect=states_get)
    hass.services.async_call = AsyncMock()
    await mgr.async_apply(hass, _room(), "living_room")

    hass.services.async_call.assert_awaited_once()
    args, kwargs = hass.services.async_call.call_args
    assert args[0] == "fan"
    assert args[1] == "set_percentage"
    assert args[2] == {"entity_id": "fan.living_room_convector", "percentage": 30}
    assert kwargs["blocking"] is True


@pytest.mark.asyncio
async def test_fan_off_is_skipped(hass, mgr):
    def states_get(entity_id):
        if entity_id == "schedule.living_room_quiet":
            return _state("on")
        if entity_id == "fan.living_room_convector":
            return _state("off")
        return None

    hass.states.get = MagicMock(side_effect=states_get)
    hass.services.async_call = AsyncMock()
    await mgr.async_apply(hass, _room(), "living_room")
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_fan_missing_percentage_attribute_is_skipped(hass, mgr):
    def states_get(entity_id):
        if entity_id == "schedule.living_room_quiet":
            return _state("on")
        if entity_id == "fan.living_room_convector":
            return _state("on", {})
        return None

    hass.states.get = MagicMock(side_effect=states_get)
    hass.services.async_call = AsyncMock()
    await mgr.async_apply(hass, _room(), "living_room")
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_service_call_failure_is_caught(hass, mgr):
    def states_get(entity_id):
        if entity_id == "schedule.living_room_quiet":
            return _state("on")
        if entity_id == "fan.living_room_convector":
            return _state("on", {"percentage": 80})
        return None

    hass.states.get = MagicMock(side_effect=states_get)
    hass.services.async_call = AsyncMock(side_effect=Exception("service unavailable"))

    # Should not raise
    await mgr.async_apply(hass, _room(), "living_room")


@pytest.mark.asyncio
async def test_multiple_fans_each_evaluated(hass, mgr):
    def states_get(entity_id):
        if entity_id == "schedule.living_room_quiet":
            return _state("on")
        if entity_id == "fan.a":
            return _state("on", {"percentage": 90})
        if entity_id == "fan.b":
            return _state("on", {"percentage": 10})
        return None

    hass.states.get = MagicMock(side_effect=states_get)
    hass.services.async_call = AsyncMock()

    room = _room(
        fans=[
            {"entity_id": "fan.a", "quiet_max_percent": 30},
            {"entity_id": "fan.b", "quiet_max_percent": 30},
        ]
    )
    await mgr.async_apply(hass, room, "living_room")

    hass.services.async_call.assert_awaited_once()
    args, _ = hass.services.async_call.call_args
    assert args[2] == {"entity_id": "fan.a", "percentage": 30}
