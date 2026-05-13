"""Tests for const.py helper functions."""

from __future__ import annotations

import time

from custom_components.roommind.const import (
    build_override_live,
    is_override_active,
    is_override_suppressed,
)


class TestIsOverrideActive:
    """Unit tests for is_override_active."""

    def test_no_override_temp(self):
        """No override_temp → inactive."""
        assert is_override_active({}) is False

    def test_override_temp_none(self):
        """override_temp=None → inactive."""
        assert is_override_active({"override_temp": None}) is False

    def test_permanent_override(self):
        """override_temp set, override_until=None → permanent, active."""
        assert is_override_active({"override_temp": 20.0, "override_until": None}) is True

    def test_future_override(self):
        """override_until in the future → active."""
        future = time.time() + 3600
        assert is_override_active({"override_temp": 20.0, "override_until": future}) is True

    def test_expired_override(self):
        """override_until in the past → inactive."""
        past = time.time() - 3600
        assert is_override_active({"override_temp": 20.0, "override_until": past}) is False


class TestIsOverrideSuppressed:
    """Unit tests for is_override_suppressed (#306)."""

    def test_presence_home_never_suppresses(self):
        assert is_override_suppressed({}, {"presence_clears_override": True}, False) is False

    def test_setting_disabled_never_suppresses(self):
        assert is_override_suppressed({}, {"presence_clears_override": False}, True) is False

    def test_setting_missing_defaults_off(self):
        assert is_override_suppressed({}, {}, True) is False

    def test_ignore_presence_room_never_suppressed(self):
        room = {"ignore_presence": True}
        assert is_override_suppressed(room, {"presence_clears_override": True}, True) is False

    def test_suppressed_when_all_conditions_met(self):
        assert is_override_suppressed({}, {"presence_clears_override": True}, True) is True


class TestBuildOverrideLive:
    """Unit tests for build_override_live (#306)."""

    def test_inactive_override(self):
        result = build_override_live({})
        assert result["override_active"] is False
        assert result["override_suppressed"] is False

    def test_active_override_not_suppressed(self):
        room = {"override_temp": 22.0, "override_until": None, "override_type": "boost"}
        result = build_override_live(room, suppressed=False)
        assert result["override_active"] is True
        assert result["override_type"] == "boost"
        assert result["override_suppressed"] is False

    def test_active_override_suppressed(self):
        room = {"override_temp": 22.0, "override_until": None, "override_type": "boost"}
        result = build_override_live(room, suppressed=True)
        assert result["override_active"] is True
        assert result["override_suppressed"] is True

    def test_inactive_override_never_suppressed(self):
        """Suppressed flag is meaningless when override is not active."""
        result = build_override_live({}, suppressed=True)
        assert result["override_active"] is False
        assert result["override_suppressed"] is False
