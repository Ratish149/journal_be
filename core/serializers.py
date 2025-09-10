# Django REST Framework Serializers
# File: journal/serializers.py

from rest_framework import serializers
from .models import JournalEntry, TradingStats


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = [
            'id', 'date', 'ltf', 'htf', 'bias', 'array',
            'pnl', 'emotions', 'mistake', 'before_trade_emotions', 'in_trade_emotions', 'after_trade_emotions', 'reason', 'results',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TradingStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingStats
        fields = [
            'total_trades', 'winning_trades', 'losing_trades',
            'total_pnl', 'win_rate', 'updated_at'
        ]
        read_only_fields = ['updated_at']
