"""
Domain layer - pure, Django-unaware, state machine for measures.
Validates measure transitions as prescribed by business rules.
"""

from django.utils import timezone


class MeasureTransitionError(Exception):
    """Custom exception for invalid state transitions."""

    pass


class MeasurePermissionError(Exception):
    """Custom exception for permission failures on measures."""

    pass


def append_to_notes(measure, user, note_prefix: str, content: str):
    """
    Appends a new, timestamped entry to the measure's 'notes' field.
    e.g., [2025-11-14 09:30 - user@example.com - EVIDENCE]:
    Submitted for review.
    """
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
    new_note = (
        f"[{timestamp} - {user.email} - {note_prefix}]:\n"
        f"{content}\n"
        f"{'-' * 20}\n"
    )

    # Prepend new notes to the top
    measure.notes = new_note + measure.notes
