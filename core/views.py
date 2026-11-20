from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Q, Sum
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .ai_service import analyze_trade_images, get_chat_response
from .models import JournalEntry, JournalEntryChat, TradingStats
from .serializers import (
    JournalEntryChatSerializer,
    JournalEntrySerializer,
    TradingStatsSerializer,
)


def _filter_entries_queryset(request):
    """Filter journal entries by month/year/all query params."""
    queryset = JournalEntry.objects.all()
    month = request.GET.get("month")
    year = request.GET.get("year")
    show_all = request.GET.get("all", "false").lower() == "true"

    if show_all:
        return queryset, {"all": True}

    if month and year:
        try:
            month = int(month)
            year = int(year)
            if month < 1 or month > 12:
                raise ValueError("Month must be between 1 and 12")
            queryset = queryset.filter(date__year=year, date__month=month)
            return queryset, {
                "month": month,
                "year": year,
                "month_name": datetime(year, month, 1).strftime("%B %Y"),
            }
        except ValueError:
            return JournalEntry.objects.none(), None

    current_date = datetime.now()
    queryset = queryset.filter(
        date__year=current_date.year, date__month=current_date.month
    )
    return queryset, {
        "month": current_date.month,
        "year": current_date.year,
        "month_name": current_date.strftime("%B %Y"),
    }


def _is_open_trade(entry):
    results = (entry.results or "").lower()
    return "open" in [part.strip() for part in results.split(",") if part.strip()]


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


class JournalEntryListCreateView(generics.ListCreateAPIView):
    serializer_class = JournalEntrySerializer

    def get_queryset(self):
        """Filter queryset by month and year if provided, default to current month"""
        queryset = JournalEntry.objects.all()

        # Get month and year from query parameters
        month = self.request.query_params.get("month")
        year = self.request.query_params.get("year")
        show_all = self.request.query_params.get("all", "false").lower() == "true"

        # If show_all is true, return all entries without filtering
        if show_all:
            return queryset

        # If both month and year are provided, filter by month
        if month and year:
            try:
                month = int(month)
                year = int(year)
                if month < 1 or month > 12:
                    raise ValueError("Month must be between 1 and 12")

                # Filter entries by month and year
                queryset = queryset.filter(date__year=year, date__month=month)
            except ValueError:
                # If invalid parameters, return empty queryset
                return JournalEntry.objects.none()
        else:
            # Default to current month if no parameters provided
            current_date = datetime.now()
            queryset = queryset.filter(
                date__year=current_date.year, date__month=current_date.month
            )

        return queryset

    def perform_create(self, serializer):
        """Save the journal entry and update stats"""
        serializer.save()
        self.update_trading_stats()

    def update_trading_stats(self):
        """Update or create trading statistics"""
        stats, created = TradingStats.objects.get_or_create(id=1)
        stats.update_stats()


class JournalEntryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific journal entry
    PUT/PATCH: Update a journal entry
    DELETE: Delete a journal entry
    """

    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer

    def perform_update(self, serializer):
        """Update journal entry and refresh stats"""
        serializer.save()
        self.update_trading_stats()

    def perform_destroy(self, instance):
        """Delete journal entry and refresh stats"""
        instance.delete()
        self.update_trading_stats()

    def update_trading_stats(self):
        """Update or create trading statistics"""
        stats, created = TradingStats.objects.get_or_create(id=1)
        stats.update_stats()


@api_view(["GET"])
def trading_stats_view(request):
    """Get trading statistics with optional monthly filtering"""
    # Get month and year from query parameters (optional)
    month = request.GET.get("month")
    year = request.GET.get("year")
    show_all = request.GET.get("all", "false").lower() == "true"

    # If show_all is true, return overall stats for all data
    if show_all:
        stats, created = TradingStats.objects.get_or_create(id=1)
        if created:
            stats.update_stats()

        serializer = TradingStatsSerializer(stats)
        return Response(serializer.data)

    # If both month and year are provided, filter by month
    if month and year:
        try:
            month = int(month)
            year = int(year)
            if month < 1 or month > 12:
                raise ValueError("Month must be between 1 and 12")
        except ValueError as e:
            return Response({"error": f"Invalid month or year: {str(e)}"}, status=400)

        # Filter entries by month and year
        entries = JournalEntry.objects.filter(date__year=year, date__month=month)

        # Calculate stats for the filtered month
        total_trades = entries.count()
        winning_trades = entries.filter(pnl__gt=0).count()
        losing_trades = entries.filter(pnl__lt=0).count()
        total_pnl = entries.aggregate(Sum("pnl"))["pnl__sum"] or 0
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Create a temporary stats object for the response
        month_stats = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "total_pnl": total_pnl,
            "win_rate": round(win_rate, 2),
            "updated_at": datetime.now(),
            "period": {
                "month": month,
                "year": year,
                "month_name": datetime(year, month, 1).strftime("%B %Y"),
            },
        }

        return Response(month_stats)

    # If no month/year provided, return current month stats (default behavior)
    current_date = datetime.now()
    entries = JournalEntry.objects.filter(
        date__year=current_date.year, date__month=current_date.month
    )

    # Calculate stats for current month
    total_trades = entries.count()
    winning_trades = entries.filter(pnl__gt=0).count()
    losing_trades = entries.filter(pnl__lt=0).count()
    total_pnl = entries.aggregate(Sum("pnl"))["pnl__sum"] or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    # Create a temporary stats object for the response
    current_month_stats = {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "total_pnl": total_pnl,
        "win_rate": round(win_rate, 2),
        "updated_at": datetime.now(),
        "period": {
            "month": current_date.month,
            "year": current_date.year,
            "month_name": current_date.strftime("%B %Y"),
        },
    }

    return Response(current_month_stats)


@api_view(["GET"])
def trading_summary_view(request):
    """Get detailed trading summary and analytics"""
    entries = JournalEntry.objects.all()

    # Basic statistics
    total_entries = entries.count()
    total_pnl = entries.aggregate(Sum("pnl"))["pnl__sum"] or 0
    winning_trades = entries.filter(pnl__gt=0).count()
    losing_trades = entries.filter(pnl__lt=0).count()
    win_rate = (winning_trades / total_entries * 100) if total_entries > 0 else 0

    # Bias analysis
    buy_trades = entries.filter(Q(bias="buy") | Q(bias="Buy"))
    sell_trades = entries.filter(Q(bias="sell") | Q(bias="Sell"))
    buy_pnl = buy_trades.aggregate(Sum("pnl"))["pnl__sum"] or 0
    sell_pnl = sell_trades.aggregate(Sum("pnl"))["pnl__sum"] or 0

    # Emotion analysis
    emotions_data = (
        entries.exclude(emotions="")
        .values("emotions")
        .annotate(count=Count("emotions"), total_pnl=Sum("pnl"))
        .order_by("-count")
    )

    # Array analysis
    array_data = (
        entries.exclude(array="")
        .values("array")
        .annotate(
            count=Count("array"),
            total_pnl=Sum("pnl"),
            win_rate=Count("id", filter=Q(pnl__gt=0)) * 100.0 / Count("id"),
        )
        .order_by("-count")
    )

    return Response(
        {
            "overview": {
                "total_entries": total_entries,
                "total_pnl": float(total_pnl),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
            },
            "bias_analysis": {
                "buy_trades": {
                    "count": buy_trades.count(),
                    "total_pnl": float(buy_pnl),
                },
                "sell_trades": {
                    "count": sell_trades.count(),
                    "total_pnl": float(sell_pnl),
                },
            },
            "emotions_breakdown": [
                {
                    "emotion": item["emotions"],
                    "count": item["count"],
                    "total_pnl": float(item["total_pnl"] or 0),
                }
                for item in emotions_data
            ],
            "array_performance": [
                {
                    "array": item["array"],
                    "count": item["count"],
                    "total_pnl": float(item["total_pnl"] or 0),
                    "win_rate": round(item["win_rate"] or 0, 2),
                }
                for item in array_data
            ],
        }
    )


@api_view(["POST"])
def refresh_stats_view(request):
    """Manually refresh trading statistics"""
    stats, created = TradingStats.objects.get_or_create(id=1)
    stats.update_stats()

    serializer = TradingStatsSerializer(stats)
    return Response(
        {"message": "Statistics refreshed successfully", "stats": serializer.data}
    )


@api_view(["GET"])
def dashboard_view(request):
    """
    Dashboard analytics for the trading journal UI.

    Query params:
      - month, year: filter by month
      - all=true: include all trades
      - (default): current month
    """
    entries, period = _filter_entries_queryset(request)
    if period is None:
        return Response({"error": "Invalid month or year"}, status=400)

    entries = list(entries.order_by("date", "created_at"))
    closed = [e for e in entries if not _is_open_trade(e)]

    wins = [e for e in closed if e.pnl > 0]
    losses = [e for e in closed if e.pnl < 0]
    breakeven = [e for e in closed if e.pnl == 0]

    gross_win = sum((e.pnl for e in wins), Decimal("0"))
    gross_loss = abs(sum((e.pnl for e in losses), Decimal("0")))
    net_pnl = sum((e.pnl for e in closed), Decimal("0"))

    total_closed = len(closed)
    win_rate = (len(wins) / total_closed * 100) if total_closed else None
    # No losses + wins => infinite profit factor (frontend can show ∞)
    if gross_loss > 0:
        profit_factor = float(gross_win / gross_loss)
    elif gross_win > 0:
        profit_factor = None  # perfect / infinite — signaled via has_wins_no_losses
    else:
        profit_factor = None
    avg_win = float(gross_win / len(wins)) if wins else None
    avg_loss = float(-(gross_loss / len(losses))) if losses else None

    daily = defaultdict(lambda: Decimal("0"))
    for entry in closed:
        if not entry.date:
            continue
        key = entry.date.isoformat()
        daily[key] += entry.pnl

    daily_pnl = [
        {"date": day, "value": _to_float(value)}
        for day, value in sorted(daily.items())
    ]
    green_days = sum(1 for d in daily_pnl if d["value"] > 0)
    trading_days = len(daily_pnl)
    day_win_rate = (
        (green_days / trading_days * 100) if trading_days else None
    )

    # Per-trade cumulative so same-day trades still draw a curve
    running = Decimal("0")
    cumulative = []
    for index, entry in enumerate(closed, start=1):
        running += entry.pnl
        trade_date = entry.date.isoformat() if entry.date else f"trade-{index}"
        cumulative.append(
            {
                "date": trade_date,
                "label": f"#{index}",
                "value": _to_float(running),
            }
        )

    buy_count = sum(
        1 for e in entries if (e.bias or "").lower() == "buy"
    )
    sell_count = sum(
        1 for e in entries if (e.bias or "").lower() == "sell"
    )

    recent_qs = sorted(
        entries,
        key=lambda e: (
            e.date or datetime.min.date(),
            e.created_at or datetime.min,
        ),
        reverse=True,
    )[:5]
    recent = JournalEntrySerializer(recent_qs, many=True).data

    return Response(
        {
            "net_pnl": _to_float(net_pnl) or 0,
            "total_trades": total_closed,
            "wins": len(wins),
            "losses": len(losses),
            "breakeven": len(breakeven),
            "win_rate": round(win_rate, 2) if win_rate is not None else None,
            "profit_factor": (
                round(profit_factor, 2) if profit_factor is not None else None
            ),
            "profit_factor_infinite": bool(gross_win > 0 and gross_loss == 0),
            "avg_win": round(avg_win, 2) if avg_win is not None else None,
            "avg_loss": round(avg_loss, 2) if avg_loss is not None else None,
            "day_win_rate": (
                round(day_win_rate, 2) if day_win_rate is not None else None
            ),
            "green_days": green_days,
            "trading_days": trading_days,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "cumulative": cumulative,
            "daily_pnl": daily_pnl,
            "recent": recent,
            "period": period,
        }
    )


class AIPredictionView(generics.GenericAPIView):
    """
    POST: Trigger AI analysis of the trade images
    """

    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer

    def post(self, request, *args, **kwargs):
        instance = self.get_object()

        # Analyze images - pass both URLs
        bias, analysis = analyze_trade_images(
            ltf_url=instance.ltf,
            htf_url=instance.htf,
        )

        # Save results
        instance.ai_bias_prediction = bias
        instance.ai_analysis = analysis
        instance.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ChatListCreateView(generics.ListCreateAPIView):
    """
    GET: List chat history for an entry
    POST: Send a message and get AI response
    """

    serializer_class = JournalEntryChatSerializer

    def get_queryset(self):
        return JournalEntryChat.objects.filter(entry_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        entry = JournalEntry.objects.get(pk=self.kwargs["pk"])
        user_message = serializer.validated_data["content"]

        # Save user message
        serializer.save(entry=entry, role="user")

        # Get AI response
        chat_history = JournalEntryChat.objects.filter(entry=entry).order_by(
            "created_at"
        )
        ai_response_text = get_chat_response(entry, user_message, chat_history)

        # Save AI response
        JournalEntryChat.objects.create(
            entry=entry, role="assistant", content=ai_response_text
        )
