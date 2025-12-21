from rest_framework import serializers

from .models import JournalEntry, JournalEntryChat, TradingStats


class JournalEntryChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntryChat
        fields = ["id", "entry", "role", "content", "created_at"]
        read_only_fields = ["id", "entry", "role", "created_at"]


class JournalEntrySerializer(serializers.ModelSerializer):
    chats = JournalEntryChatSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "date",
            "ltf",
            "htf",
            "ltf_image",
            "htf_image",
            "bias",
            "array",
            "kill_zone",
            "pnl",
            "emotions",
            "mistake",
            "before_trade_emotions",
            "in_trade_emotions",
            "after_trade_emotions",
            "reason",
            "results",
            "ai_bias_prediction",
            "ai_analysis",
            "chats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "chats"]


class TradingStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingStats
        fields = [
            "total_trades",
            "winning_trades",
            "losing_trades",
            "total_pnl",
            "win_rate",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
