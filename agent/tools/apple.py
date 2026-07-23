import subprocess
import sys
from agent.tools import tool
from datetime import datetime

def _osa(script, timeout=30):
    """Run an AppleScript via osascript"""
    if sys.platform != "darwin":
        return "Error: Apple tools only works on macOS"
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "Error: the apple app took to long to respond"
    if result.returncode != 0:
        return f"Error from AppleScript: {result.stderr.strip()}"
    return result.stdout.strip() or "Done"


""" --------------- NOTES -------------- """

CREATE_NOTE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_note",
        "description": "Create a new note in the macOS Notes app.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The notes title (first line)"},
                "body": {"type": "string", "description": "The notes body text"},

            },
            "required": ["title", "body"],
        },
    },
}

@tool(CREATE_NOTE_SCHEMA)
def create_note(title, body):
    script = f'tell application "Notes" to make new note with properties {{body:"{title}" & return & "{body}"}}'
    return _osa(script)


""" --------------- REMINDERS -------------- """

CREATE_REMINDER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_reminder",
        "description": "Create a new reminder in the macOS Reminders app.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The reminder text"},
            },
            "required": ["text"],
        },
    },
}

@tool(CREATE_REMINDER_SCHEMA)
def create_reminder(text):
    script = f'tell application "Reminders" to make new reminder with properties {{name:"{text}"}}'
    return _osa(script)

READ_REMINDERS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_reminders",
        "description": "List all incomplete reminders from the macOS Reminders app.",
        "parameters": {"type": "object", "properties": {}},
    },
}

@tool(READ_REMINDERS_SCHEMA)
def read_reminders():
    script = (
        'tell application "Reminders"\n'
        '    set output to ""\n'
        '    repeat with r in (reminders whose completed is false)\n'
        '        set output to output & name of r & linefeed\n'
        '    end repeat\n'
        '    return output\n'
        'end tell'
    )
    return _osa(script)


""" --------------- CALENDAR -------------- """

DEFAULT_CALENDAR = "Personal"   

CREATE_EVENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_calendar_event",
        "description": "Create an event in the macOS Calendar app.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "start": {"type": "string", "description": "Start time in ISO 8601, e.g. 2026-07-27T15:00"},
                "duration_minutes": {"type": "integer", "description": "Length in minutes (default 60)"},
            },
            "required": ["title", "start"],
        },
    },
}


@tool(CREATE_EVENT_SCHEMA)
def create_calendar_event(title, start, duration_minutes=60):
    try:
        dt = datetime.fromisoformat(start)
    except ValueError:
        return f"Error: could not parse start time '{start}' (need ISO 8601 like 2026-07-27T15:00)."

    script = (
        f'set startDate to current date\n'
        f'set day of startDate to 1\n'
        f'set year of startDate to {dt.year}\n'
        f'set month of startDate to {dt.month}\n'
        f'set day of startDate to {dt.day}\n'
        f'set hours of startDate to {dt.hour}\n'
        f'set minutes of startDate to {dt.minute}\n'
        f'set seconds of startDate to 0\n'
        f'set endDate to startDate + ({duration_minutes} * minutes)\n'
        f'tell application "Calendar" to tell calendar "{DEFAULT_CALENDAR}" '
        f'to make new event with properties {{summary:"{title}", start date:startDate, end date:endDate}}'
    )
    return _osa(script)

READ_CALENDAR_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_calendar",
        "description": "List upcoming events over the next 7 days from the macOS Calendar.",
        "parameters": {"type": "object", "properties": {}},
    },
}


@tool(READ_CALENDAR_SCHEMA)
def read_calendar():
    script = (
        'set rangeStart to current date\n'
        'set rangeEnd to (current date) + (7 * days)\n'
        'set output to ""\n'
        f'tell application "Calendar" to tell calendar "{DEFAULT_CALENDAR}"\n'
        '    set theEvents to (every event whose start date > rangeStart and start date < rangeEnd)\n'
        '    repeat with e in theEvents\n'
        '        set output to output & summary of e & " — " & (start date of e as string) & linefeed\n'
        '    end repeat\n'
        'end tell\n'
        'return output'
    )
    return _osa(script, timeout=45)


