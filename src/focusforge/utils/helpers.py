"""Utility functions."""
from datetime import datetime, timedelta


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def get_motivational_quote() -> str:
    """Get a random motivational quote."""
    quotes = [
        "Focus is the gateway to thinking.",
        "Productivity is never an accident.",
        "Success is the sum of small efforts.",
        "You are in control of your time.",
        "Deep work produces deep results.",
        "Discipline equals freedom.",
        "Progress, not perfection.",
        "One task at a time.",
        "Your focus determines your reality.",
        "Stay committed to your decisions."
    ]
    import random
    return random.choice(quotes)


def calculate_productivity_score(productive_seconds: float, total_seconds: float) -> float:
    """Calculate productivity score (0-100)."""
    if total_seconds == 0:
        return 0
    return min(100, (productive_seconds / total_seconds) * 100)
