from datetime import datetime, timezone
from config.logging import logger


def format_date_human_readable(date_input):
    """
    Converts a date string or datetime object to a human-readable format.

    Parameters:
        date_input (str | datetime): The date to format. Can be:
            - A string in ISO 8601 format: "YYYY-MM-DDTHH:MM:SSZ".
            - A datetime object.

    Returns:
        str: The date formatted as "Month DaySuffix, Year at HH:MM AM/PM UTC".
            Example: "December 2nd, 2024 at 11:45 AM UTC".
            Returns "Invalid Date" if the input is not a valid date format.
    """
    try:
        if isinstance(date_input, datetime):
            # Ensure datetime is in UTC
            date = date_input.astimezone(timezone.utc)
        else:
            # Parse string to datetime object
            date = datetime.strptime(date_input, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

        # Add ordinal suffix to day
        day = date.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        # Format date
        formatted_time = date.strftime(f"%B {day}{suffix}, %Y at %-I:%M %p UTC")
        return formatted_time
    except Exception as e:
        logger.error(f"Error formatting date: {date_input}, error: {e}")
        return "Invalid Date"