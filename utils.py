"""
Utility helper functions for the WayPoint Discord bot.
"""
from datetime import datetime

def check_cpu_temp():
    try:
        from gpiozero import CPUTemperature
        cpu_temp = CPUTemperature()
    except Exception:
        cpu_temp = None
    return cpu_temp
    
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
    
    days = diff.days
    total_seconds = int(diff.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
    else:
        return f"{hours} hours, {minutes} minutes, {seconds} seconds"


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
