# Django Admin Configuration (Simplified)
# File: journal/admin.py

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import GeminiApiKey, JournalEntry, TradingStats


@admin.register(JournalEntry)
class JournalEntryAdmin(ModelAdmin):
    list_display = ["id", "date", "bias", "array", "pnl", "emotions", "created_at"]
    list_filter = ["date", "created_at"]
    date_hierarchy = "date"


@admin.register(TradingStats)
class TradingStatsAdmin(ModelAdmin):
    list_display = [
        "total_trades",
        "winning_trades",
        "losing_trades",
        "total_pnl",
        "win_rate",
        "updated_at",
    ]
    readonly_fields = [
        "total_trades",
        "winning_trades",
        "losing_trades",
        "total_pnl",
        "win_rate",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GeminiApiKey)
class GeminiApiKeyAdmin(ModelAdmin):
    list_display = [
        "key_preview",
        "is_active",
        "usage_count",
        "last_used",
        "created_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["key"]
    readonly_fields = ["usage_count", "last_used", "created_at"]

    def key_preview(self, obj):
        return f"{obj.key[:10]}..." if obj.key else "No Key"

    key_preview.short_description = "API Key"
