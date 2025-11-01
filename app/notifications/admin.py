"""
Django admin and customizations for models of notifications app.
"""

from django.contrib import admin
from .models import Notification, UserNotification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for the Notification model."""

    list_display = (
        "id",
        "entity_type",
        "entity_id",
        "event_type",
        "recipient",
        "recipient_role",
        "status",
        "created_at",
    )
    list_filter = ("status", "event_type", "entity_type", "created_at")
    search_fields = ("entity_id", "payload")


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    """Admin configuration for the UserNotification model."""

    list_display = ("id", "notification", "user", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__email", "notification__id")
