"""
Utility helper functions for the WayPoint Discord bot.
"""
from datetime import datetime


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
