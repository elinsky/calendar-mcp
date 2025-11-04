"""Unit tests for server handlers (without requiring Calendar access)."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from calendar_mcp.models import Event
from calendar_mcp.server import (
    create_event_handler,
    delete_event_handler,
    list_calendars_handler,
    list_events_handler,
    update_event_handler,
)


class TestListCalendarsHandler:
    """Test list_calendars_handler."""

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_list_calendars_success(self, mock_get_manager):
        """Test successful calendar listing."""
        mock_manager = MagicMock()
        mock_manager.list_calendar_names.return_value = ["Work", "Personal", "Family"]
        mock_get_manager.return_value = mock_manager

        result = list_calendars_handler({})

        assert "Available calendars:" in result
        assert "- Work" in result
        assert "- Personal" in result
        assert "- Family" in result

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_list_calendars_empty(self, mock_get_manager):
        """Test listing when no calendars exist."""
        mock_manager = MagicMock()
        mock_manager.list_calendar_names.return_value = []
        mock_get_manager.return_value = mock_manager

        result = list_calendars_handler({})

        assert result == "No calendars found"

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_list_calendars_error(self, mock_get_manager):
        """Test error handling in calendar listing."""
        mock_get_manager.side_effect = Exception("Calendar access denied")

        result = list_calendars_handler({})

        assert "Error listing calendars" in result
        assert "Calendar access denied" in result


class TestListEventsHandler:
    """Test list_events_handler."""

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_list_events_success(self, mock_get_manager):
        """Test successful event listing."""
        mock_manager = MagicMock()

        # Create mock events
        event1 = Event(
            title="Meeting",
            start_time=datetime(2025, 11, 5, 10, 0),
            end_time=datetime(2025, 11, 5, 11, 0),
            identifier="event1",
            calendar_name="Work",
        )
        event2 = Event(
            title="Lunch",
            start_time=datetime(2025, 11, 5, 12, 0),
            end_time=datetime(2025, 11, 5, 13, 0),
            identifier="event2",
            calendar_name="Personal",
        )
        mock_manager.list_events.return_value = [event1, event2]
        mock_get_manager.return_value = mock_manager

        params = {
            "start_date": "2025-11-05T00:00:00",
            "end_date": "2025-11-05T23:59:59",
        }
        result = list_events_handler(params)

        assert "2025-11-05" in result
        assert "Meeting" in result
        assert "Lunch" in result
        assert "Total time:" in result

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_list_events_empty(self, mock_get_manager):
        """Test listing when no events exist."""
        mock_manager = MagicMock()
        mock_manager.list_events.return_value = []
        mock_get_manager.return_value = mock_manager

        params = {
            "start_date": "2025-11-05T00:00:00",
            "end_date": "2025-11-05T23:59:59",
        }
        result = list_events_handler(params)

        assert result == "No events found in the specified date range"


class TestCreateEventHandler:
    """Test create_event_handler."""

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_create_event_success(self, mock_get_manager):
        """Test successful event creation."""
        mock_manager = MagicMock()
        created_event = Event(
            title="New Meeting",
            start_time=datetime(2025, 11, 6, 14, 0),
            end_time=datetime(2025, 11, 6, 15, 0),
            identifier="new_event_123",
            calendar_name="Work",
        )
        mock_manager.create_event.return_value = created_event
        mock_get_manager.return_value = mock_manager

        params = {
            "title": "New Meeting",
            "start_time": "2025-11-06T14:00:00",
            "end_time": "2025-11-06T15:00:00",
            "location": "Conference Room",
            "notes": "Important meeting",
        }
        result = create_event_handler(params)

        assert "Successfully created event" in result
        assert "New Meeting" in result
        assert "new_event_123" in result


class TestUpdateEventHandler:
    """Test update_event_handler."""

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_update_event_success(self, mock_get_manager):
        """Test successful event update."""
        mock_manager = MagicMock()
        updated_event = Event(
            title="Updated Meeting",
            start_time=datetime(2025, 11, 6, 15, 0),
            end_time=datetime(2025, 11, 6, 16, 0),
            identifier="event_123",
            calendar_name="Work",
        )
        mock_manager.update_event.return_value = updated_event
        mock_get_manager.return_value = mock_manager

        params = {
            "event_id": "event_123",
            "title": "Updated Meeting",
            "start_time": "2025-11-06T15:00:00",
        }
        result = update_event_handler(params)

        assert "Successfully updated event" in result
        assert "Updated Meeting" in result

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_update_event_missing_id(self, mock_get_manager):
        """Test update without event_id."""
        params = {"title": "New Title"}
        result = update_event_handler(params)

        assert "Error: Missing required parameter (event_id)" in result


class TestDeleteEventHandler:
    """Test delete_event_handler."""

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_delete_event_success(self, mock_get_manager):
        """Test successful event deletion."""
        mock_manager = MagicMock()
        event_to_delete = Event(
            title="Old Meeting",
            start_time=datetime(2025, 11, 6, 10, 0),
            end_time=datetime(2025, 11, 6, 11, 0),
            identifier="event_to_delete",
            calendar_name="Work",
        )
        mock_manager.find_event_by_id.return_value = event_to_delete
        mock_manager.delete_event.return_value = True
        mock_get_manager.return_value = mock_manager

        params = {"event_id": "event_to_delete"}
        result = delete_event_handler(params)

        assert "Successfully deleted event" in result
        assert "Old Meeting" in result

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_delete_event_not_found(self, mock_get_manager):
        """Test deleting non-existent event."""
        mock_manager = MagicMock()
        mock_manager.find_event_by_id.return_value = None
        mock_get_manager.return_value = mock_manager

        params = {"event_id": "nonexistent"}
        result = delete_event_handler(params)

        assert "Event with ID nonexistent not found" in result

    @patch("calendar_mcp.server.get_calendar_manager")
    def test_delete_event_missing_id(self, mock_get_manager):
        """Test delete without event_id."""
        params = {}
        result = delete_event_handler(params)

        assert "Error: Missing required parameter (event_id)" in result
