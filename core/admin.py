# Django Admin Configuration (Simplified)
# File: journal/admin.py

from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import JournalEntry, TradingStats


@admin.register(JournalEntry)
class JournalEntryAdmin(ModelAdmin):
    list_display = [
        'id', 'date', 'bias', 'array', 'pnl',
        'emotions', 'created_at'
    ]
    list_filter = [
        'bias', 'array', 'emotions', 'date', 'created_at'
    ]
    search_fields = [
        'reason', 'mistake', 'ltf', 'htf'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    list_per_page = 25

    fieldsets = (
        ('Basic Information', {
            'fields': ('date',)
        }),
        ('Trading Details', {
            'fields': ('bias', 'array', 'pnl')
        }),
        ('Chart URLs', {
            'fields': ('ltf', 'htf'),
            'description': 'Enter chart URLs for LTF and HTF'
        }),
        ('Analysis', {
            'fields': ('emotions', 'reason', 'mistake')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TradingStats)
class TradingStatsAdmin(ModelAdmin):
    list_display = [
        'total_trades', 'winning_trades', 'losing_trades',
        'total_pnl', 'win_rate', 'updated_at'
    ]
    readonly_fields = [
        'total_trades', 'winning_trades', 'losing_trades',
        'total_pnl', 'win_rate', 'updated_at'
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
