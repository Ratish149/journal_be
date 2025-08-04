
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from datetime import datetime
from .models import JournalEntry, TradingStats
from .serializers import JournalEntrySerializer, TradingStatsSerializer


class JournalEntryListCreateView(generics.ListCreateAPIView):
    serializer_class = JournalEntrySerializer

    def get_queryset(self):
        """Filter queryset by month and year if provided, default to current month"""
        queryset = JournalEntry.objects.all()

        # Get month and year from query parameters
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        show_all = self.request.query_params.get(
            'all', 'false').lower() == 'true'

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
                queryset = queryset.filter(
                    date__year=year,
                    date__month=month
                )
            except ValueError:
                # If invalid parameters, return empty queryset
                return JournalEntry.objects.none()
        else:
            # Default to current month if no parameters provided
            current_date = datetime.now()
            queryset = queryset.filter(
                date__year=current_date.year,
                date__month=current_date.month
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


@api_view(['GET'])
def trading_stats_view(request):
    """Get trading statistics with optional monthly filtering"""
    # Get month and year from query parameters (optional)
    month = request.GET.get('month')
    year = request.GET.get('year')
    show_all = request.GET.get('all', 'false').lower() == 'true'

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
            return Response({
                'error': f'Invalid month or year: {str(e)}'
            }, status=400)

        # Filter entries by month and year
        entries = JournalEntry.objects.filter(
            date__year=year,
            date__month=month
        )

        # Calculate stats for the filtered month
        total_trades = entries.count()
        winning_trades = entries.filter(pnl__gt=0).count()
        losing_trades = entries.filter(pnl__lt=0).count()
        total_pnl = entries.aggregate(Sum('pnl'))['pnl__sum'] or 0
        win_rate = (winning_trades / total_trades *
                    100) if total_trades > 0 else 0

        # Create a temporary stats object for the response
        month_stats = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_pnl': total_pnl,
            'win_rate': round(win_rate, 2),
            'updated_at': datetime.now(),
            'period': {
                'month': month,
                'year': year,
                'month_name': datetime(year, month, 1).strftime('%B %Y')
            }
        }

        return Response(month_stats)

    # If no month/year provided, return current month stats (default behavior)
    current_date = datetime.now()
    entries = JournalEntry.objects.filter(
        date__year=current_date.year,
        date__month=current_date.month
    )

    # Calculate stats for current month
    total_trades = entries.count()
    winning_trades = entries.filter(pnl__gt=0).count()
    losing_trades = entries.filter(pnl__lt=0).count()
    total_pnl = entries.aggregate(Sum('pnl'))['pnl__sum'] or 0
    win_rate = (winning_trades / total_trades *
                100) if total_trades > 0 else 0

    # Create a temporary stats object for the response
    current_month_stats = {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'total_pnl': total_pnl,
        'win_rate': round(win_rate, 2),
        'updated_at': datetime.now(),
        'period': {
            'month': current_date.month,
            'year': current_date.year,
            'month_name': current_date.strftime('%B %Y')
        }
    }

    return Response(current_month_stats)


@api_view(['GET'])
def trading_summary_view(request):
    """Get detailed trading summary and analytics"""
    entries = JournalEntry.objects.all()

    # Basic statistics
    total_entries = entries.count()
    total_pnl = entries.aggregate(Sum('pnl'))['pnl__sum'] or 0
    winning_trades = entries.filter(pnl__gt=0).count()
    losing_trades = entries.filter(pnl__lt=0).count()
    win_rate = (winning_trades / total_entries *
                100) if total_entries > 0 else 0

    # Bias analysis
    buy_trades = entries.filter(bias='buy')
    sell_trades = entries.filter(bias='sell')
    buy_pnl = buy_trades.aggregate(Sum('pnl'))['pnl__sum'] or 0
    sell_pnl = sell_trades.aggregate(Sum('pnl'))['pnl__sum'] or 0

    # Emotion analysis
    emotions_data = entries.exclude(emotions='').values('emotions').annotate(
        count=Count('emotions'),
        total_pnl=Sum('pnl')
    ).order_by('-count')

    # Array analysis
    array_data = entries.exclude(array='').values('array').annotate(
        count=Count('array'),
        total_pnl=Sum('pnl'),
        win_rate=Count('id', filter=Q(pnl__gt=0)) * 100.0 / Count('id')
    ).order_by('-count')

    return Response({
        'overview': {
            'total_entries': total_entries,
            'total_pnl': float(total_pnl),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
        },
        'bias_analysis': {
            'buy_trades': {
                'count': buy_trades.count(),
                'total_pnl': float(buy_pnl),
            },
            'sell_trades': {
                'count': sell_trades.count(),
                'total_pnl': float(sell_pnl),
            }
        },
        'emotions_breakdown': [
            {
                'emotion': item['emotions'],
                'count': item['count'],
                'total_pnl': float(item['total_pnl'] or 0)
            }
            for item in emotions_data
        ],
        'array_performance': [
            {
                'array': item['array'],
                'count': item['count'],
                'total_pnl': float(item['total_pnl'] or 0),
                'win_rate': round(item['win_rate'] or 0, 2)
            }
            for item in array_data
        ]
    })


@api_view(['POST'])
def refresh_stats_view(request):
    """Manually refresh trading statistics"""
    stats, created = TradingStats.objects.get_or_create(id=1)
    stats.update_stats()

    serializer = TradingStatsSerializer(stats)
    return Response({
        'message': 'Statistics refreshed successfully',
        'stats': serializer.data
    })
