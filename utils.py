"""
Utility helper functions for the WayPoint Discord bot.
"""
from datetime import datetime


def check_cpu_temp():
    """Return a gpiozero CPUTemperature instance on Raspberry Pi, or None elsewhere."""
    try:
        from gpiozero import CPUTemperature
        cpu_temp = CPUTemperature()
    except Exception:
        cpu_temp = None
    return cpu_temp


def parse_timestamp(value, tz=None):
    """Parse an ISO timestamp string or datetime into a datetime object."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value)
    else:
        return None

    if tz is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt


def format_time_difference(start_time, end_time):
    """
    Format time difference in a human-readable way.

    Args:
        start_time (datetime): The starting timestamp
        end_time (datetime): The ending timestamp

    Returns:
        str: Human-readable time difference string
    """
    diff = end_time - start_time
    if diff.total_seconds() < 0:
        return "0 hours, 0 minutes, 0 seconds"

    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
    return f"{hours} hours, {minutes} minutes, {seconds} seconds"


def format_duration_short(start_time, end_time):
    """Format a compact duration string like '45 minutes' or '2h 15m'."""
    total_seconds = max(0, int((end_time - start_time).total_seconds()))
    minutes = total_seconds // 60
    if minutes < 60:
        label = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {label}"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m" if mins else f"{hours}h"


def format_rp_per_hour(rp_change, start_time, end_time):
    """
    Format RP change as an hourly average.

    Args:
        rp_change (int): Signed RP change over the session
        start_time (datetime): The starting timestamp
        end_time (datetime): The ending timestamp

    Returns:
        str: Signed RP-per-hour string
    """
    elapsed_seconds = (end_time - start_time).total_seconds()
    if elapsed_seconds <= 0:
        return "0.0 RP/hr"

    rp_per_hour = rp_change / (elapsed_seconds / 3600)
    if rp_per_hour == 0:
        return "0.0 RP/hr"

    return f"{rp_per_hour:+.1f} RP/hr"
