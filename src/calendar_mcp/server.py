"""MCP server for Apple Calendar integration."""

import json
from datetime import datetime
from functools import lru_cache
from textwrap import dedent

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from calendar_mcp.calendar_manager import CalendarManager
from calendar_mcp.models import CreateEventRequest, UpdateEventRequest


# Initialize the CalendarManager on demand to only request calendar permission
# when a calendar tool is invoked instead of on launch
@lru_cache(maxsize=None)
def get_calendar_manager() -> CalendarManager:
    """Get or initialize the calendar manager with proper error handling."""
    try:
        return CalendarManager()
    except ValueError as e:
        error_msg = dedent("""\
        Calendar access is not granted. Please follow these steps:

        1. Open System Preferences/Settings
        2. Go to Privacy & Security > Calendar
        3. Check the box next to your terminal application or Claude Desktop
        4. Restart Claude Desktop

        Once you've granted access, try your calendar operation again.
        """)
        raise ValueError(error_msg) from e


def list_calendars_handler(params: dict) -> str:
    """
    Handle list_calendars tool invocation.

    Args:
        params: Tool parameters (none)

    Returns:
        Formatted list of available calendars
    """
    try:
        manager = get_calendar_manager()
        calendars = manager.list_calendar_names()
        if not calendars:
            return "No calendars found"

        return "Available calendars:\n" + "\n".join(f"- {calendar}" for calendar in calendars)

    except Exception as e:
        return f"Error listing calendars: {str(e)}"


def list_events_handler(params: dict) -> str:
    """
    Handle list_events tool invocation.

    Args:
        params: Tool parameters (start_date, end_date, calendar_name?)

    Returns:
        Formatted list of events or JSON with event details
    """
    try:
        manager = get_calendar_manager()

        # Parse datetime parameters
        start_date = datetime.fromisoformat(params.get("start_date"))
        end_date = datetime.fromisoformat(params.get("end_date"))
        calendar_name = params.get("calendar_name")

        events = manager.list_events(start_date, end_date, calendar_name)
        if not events:
            return "No events found in the specified date range"

        # Group events by date for better readability
        from collections import defaultdict

        events_by_date = defaultdict(list)
        for event in events:
            date_key = event.start_time.strftime("%Y-%m-%d")
            events_by_date[date_key].append(event)

        # Format output
        output_lines = []
        total_minutes = 0

        for date_key in sorted(events_by_date.keys()):
            output_lines.append(f"\n{date_key}:")
            day_minutes = 0
            for event in sorted(events_by_date[date_key], key=lambda e: e.start_time):
                output_lines.append(f"  {event.to_summary_string()}")
                if event.notes:
                    # Indent notes
                    notes_preview = event.notes[:100] + "..." if len(event.notes) > 100 else event.notes
                    output_lines.append(f"    Notes: {notes_preview}")
                day_minutes += event.duration_minutes
                total_minutes += event.duration_minutes
            output_lines.append(f"  Daily total: {day_minutes} minutes ({day_minutes / 60:.1f} hours)")

        output_lines.append(f"\nTotal time: {total_minutes} minutes ({total_minutes / 60:.1f} hours)")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error listing events: {str(e)}"


def create_event_handler(params: dict) -> str:
    """
    Handle create_event tool invocation.

    Args:
        params: Tool parameters (title, start_time, end_time, etc.)

    Returns:
        Success or error message
    """
    try:
        manager = get_calendar_manager()

        # Create the request object
        create_request = CreateEventRequest(
            title=params.get("title"),
            start_time=datetime.fromisoformat(params.get("start_time")),
            end_time=datetime.fromisoformat(params.get("end_time")),
            calendar_name=params.get("calendar_name"),
            location=params.get("location"),
            notes=params.get("notes"),
            alarms_minutes_offsets=params.get("alarms_minutes_offsets"),
            url=params.get("url"),
            all_day=params.get("all_day", False),
            recurrence_rule=params.get("recurrence_rule"),
        )

        event = manager.create_event(create_request)
        if not event:
            return "Failed to create event. Please check calendar permissions and try again."

        return f"Successfully created event: {event.title} (ID: {event.identifier})"

    except Exception as e:
        return f"Error creating event: {str(e)}"


def update_event_handler(params: dict) -> str:
    """
    Handle update_event tool invocation.

    Args:
        params: Tool parameters (event_id, and optional fields to update)

    Returns:
        Success or error message
    """
    try:
        manager = get_calendar_manager()

        event_id = params.get("event_id")
        if not event_id:
            return "Error: Missing required parameter (event_id)"

        # Build update request with only provided fields
        update_data = {}
        if "title" in params:
            update_data["title"] = params["title"]
        if "start_time" in params:
            update_data["start_time"] = datetime.fromisoformat(params["start_time"])
        if "end_time" in params:
            update_data["end_time"] = datetime.fromisoformat(params["end_time"])
        if "calendar_name" in params:
            update_data["calendar_name"] = params["calendar_name"]
        if "location" in params:
            update_data["location"] = params["location"]
        if "notes" in params:
            update_data["notes"] = params["notes"]
        if "alarms_minutes_offsets" in params:
            update_data["alarms_minutes_offsets"] = params["alarms_minutes_offsets"]
        if "url" in params:
            update_data["url"] = params["url"]
        if "all_day" in params:
            update_data["all_day"] = params["all_day"]
        if "recurrence_rule" in params:
            update_data["recurrence_rule"] = params["recurrence_rule"]

        update_request = UpdateEventRequest(**update_data)
        event = manager.update_event(event_id, update_request)

        if not event:
            return f"Failed to update event. Event with ID {event_id} not found or update failed."

        return f"Successfully updated event: {event.title}"

    except Exception as e:
        return f"Error updating event: {str(e)}"


def delete_event_handler(params: dict) -> str:
    """
    Handle delete_event tool invocation.

    Args:
        params: Tool parameters (event_id)

    Returns:
        Success or error message
    """
    try:
        manager = get_calendar_manager()

        event_id = params.get("event_id")
        if not event_id:
            return "Error: Missing required parameter (event_id)"

        # Get event details before deletion for confirmation message
        event = manager.find_event_by_id(event_id)
        if not event:
            return f"Event with ID {event_id} not found"

        event_title = event.title

        success = manager.delete_event(event_id)
        if success:
            return f"Successfully deleted event: {event_title}"
        else:
            return f"Failed to delete event: {event_title}"

    except Exception as e:
        return f"Error deleting event: {str(e)}"


async def main():
    """Run the MCP server."""
    server = Server("calendar-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="list_calendars",
                description="List all available calendars that can be used with calendar operations.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="list_events",
                description="List calendar events in a date range. Returns events grouped by date with time totals. Use for daily summaries, weekly reviews, and planning.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in ISO8601 format (YYYY-MM-DDTHH:MM:SS). For full day queries, use 00:00:00 for the time.",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in ISO8601 format (YYYY-MM-DDTHH:MM:SS). For full day queries, use 23:59:59 for the time.",
                        },
                        "calendar_name": {
                            "type": "string",
                            "description": "Optional calendar name to filter by. Use list_calendars to see available calendars.",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            Tool(
                name="create_event",
                description="Create a new calendar event with title, time, location, notes, and other metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Event title"},
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "calendar_name": {
                            "type": "string",
                            "description": "Optional calendar name. If not specified, uses default calendar.",
                        },
                        "location": {"type": "string", "description": "Optional event location"},
                        "notes": {"type": "string", "description": "Optional event notes/description"},
                        "alarms_minutes_offsets": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Optional list of minutes before event to trigger reminders (e.g., [15, 60] for 15 min and 1 hour before)",
                        },
                        "url": {"type": "string", "description": "Optional URL associated with event"},
                        "all_day": {
                            "type": "boolean",
                            "description": "Whether this is an all-day event (default: false)",
                        },
                        "recurrence_rule": {
                            "type": "object",
                            "description": "Optional recurrence rule for repeating events",
                        },
                    },
                    "required": ["title", "start_time", "end_time"],
                },
            ),
            Tool(
                name="update_event",
                description="Update an existing calendar event. Only provide the fields you want to change.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "Unique identifier of the event to update (from list_events)",
                        },
                        "title": {"type": "string", "description": "New event title"},
                        "start_time": {
                            "type": "string",
                            "description": "New start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "New end time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "calendar_name": {"type": "string", "description": "New calendar name"},
                        "location": {"type": "string", "description": "New event location"},
                        "notes": {"type": "string", "description": "New event notes/description"},
                        "alarms_minutes_offsets": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "New list of reminder offsets in minutes",
                        },
                        "url": {"type": "string", "description": "New URL"},
                        "all_day": {"type": "boolean", "description": "New all-day flag"},
                        "recurrence_rule": {
                            "type": "object",
                            "description": "New recurrence rule",
                        },
                    },
                    "required": ["event_id"],
                },
            ),
            Tool(
                name="delete_event",
                description="Delete a calendar event by its identifier.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "Unique identifier of the event to delete (from list_events)",
                        }
                    },
                    "required": ["event_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        if name == "list_calendars":
            result = list_calendars_handler(arguments)
            return [TextContent(type="text", text=result)]
        elif name == "list_events":
            result = list_events_handler(arguments)
            return [TextContent(type="text", text=result)]
        elif name == "create_event":
            result = create_event_handler(arguments)
            return [TextContent(type="text", text=result)]
        elif name == "update_event":
            result = update_event_handler(arguments)
            return [TextContent(type="text", text=result)]
        elif name == "delete_event":
            result = delete_event_handler(arguments)
            return [TextContent(type="text", text=result)]
        else:
            raise ValueError(f"Unknown tool: {name}")

    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
