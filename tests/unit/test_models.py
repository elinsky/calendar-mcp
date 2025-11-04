"""Unit tests for calendar models."""

from datetime import datetime

import pytest

from calendar_mcp.models import (
    CreateEventRequest,
    Frequency,
    RecurrenceRule,
    UpdateEventRequest,
    Weekday,
)


class TestCreateEventRequest:
    """Test CreateEventRequest model."""

    def test_create_basic_event_request(self):
        """Test creating a basic event request."""
        request = CreateEventRequest(
            title="Test Event",
            start_time=datetime(2025, 11, 5, 10, 0),
            end_time=datetime(2025, 11, 5, 11, 0),
        )
        assert request.title == "Test Event"
        assert request.start_time == datetime(2025, 11, 5, 10, 0)
        assert request.end_time == datetime(2025, 11, 5, 11, 0)
        assert request.calendar_name is None
        assert request.location is None
        assert request.notes is None
        assert request.all_day is False

    def test_create_full_event_request(self):
        """Test creating an event request with all fields."""
        request = CreateEventRequest(
            title="Team Meeting",
            start_time=datetime(2025, 11, 5, 14, 0),
            end_time=datetime(2025, 11, 5, 15, 0),
            calendar_name="Work",
            location="Conference Room A",
            notes="Discuss Q4 planning",
            alarms_minutes_offsets=[15, 60],
            url="https://example.com/meeting",
            all_day=False,
        )
        assert request.title == "Team Meeting"
        assert request.calendar_name == "Work"
        assert request.location == "Conference Room A"
        assert request.notes == "Discuss Q4 planning"
        assert request.alarms_minutes_offsets == [15, 60]
        assert request.url == "https://example.com/meeting"


class TestUpdateEventRequest:
    """Test UpdateEventRequest model."""

    def test_update_single_field(self):
        """Test updating a single field."""
        request = UpdateEventRequest(title="Updated Title")
        assert request.title == "Updated Title"
        assert request.start_time is None
        assert request.end_time is None

    def test_update_multiple_fields(self):
        """Test updating multiple fields."""
        request = UpdateEventRequest(
            title="New Title",
            location="New Location",
            notes="New notes",
        )
        assert request.title == "New Title"
        assert request.location == "New Location"
        assert request.notes == "New notes"


class TestRecurrenceRule:
    """Test RecurrenceRule model."""

    def test_daily_recurrence(self):
        """Test daily recurrence rule."""
        rule = RecurrenceRule(frequency=Frequency.DAILY, interval=1)
        assert rule.frequency == Frequency.DAILY
        assert rule.interval == 1
        assert rule.end_date is None
        assert rule.occurrence_count is None

    def test_weekly_recurrence_with_days(self):
        """Test weekly recurrence with specific days."""
        rule = RecurrenceRule(
            frequency=Frequency.WEEKLY,
            interval=1,
            days_of_week=[Weekday.MONDAY, Weekday.WEDNESDAY, Weekday.FRIDAY],
        )
        assert rule.frequency == Frequency.WEEKLY
        assert rule.days_of_week == [Weekday.MONDAY, Weekday.WEDNESDAY, Weekday.FRIDAY]

    def test_recurrence_with_end_date(self):
        """Test recurrence with end date."""
        end_date = datetime(2025, 12, 31, 23, 59, 59)
        rule = RecurrenceRule(frequency=Frequency.DAILY, interval=1, end_date=end_date)
        assert rule.end_date == end_date
        assert rule.occurrence_count is None

    def test_recurrence_with_occurrence_count(self):
        """Test recurrence with occurrence count."""
        rule = RecurrenceRule(frequency=Frequency.WEEKLY, interval=1, occurrence_count=10)
        assert rule.occurrence_count == 10
        assert rule.end_date is None

    def test_both_end_conditions_raises_error(self):
        """Test that setting both end_date and occurrence_count raises error."""
        with pytest.raises(ValueError, match="Only one of end_date or occurrence_count"):
            RecurrenceRule(
                frequency=Frequency.DAILY,
                interval=1,
                end_date=datetime(2025, 12, 31),
                occurrence_count=10,
            )


class TestWeekday:
    """Test Weekday enum."""

    def test_weekday_values(self):
        """Test weekday integer values."""
        assert Weekday.SUNDAY == 1
        assert Weekday.MONDAY == 2
        assert Weekday.TUESDAY == 3
        assert Weekday.WEDNESDAY == 4
        assert Weekday.THURSDAY == 5
        assert Weekday.FRIDAY == 6
        assert Weekday.SATURDAY == 7


class TestFrequency:
    """Test Frequency enum."""

    def test_frequency_values(self):
        """Test frequency integer values match EventKit constants."""
        assert Frequency.DAILY == 0
        assert Frequency.WEEKLY == 1
        assert Frequency.MONTHLY == 2
        assert Frequency.YEARLY == 3
