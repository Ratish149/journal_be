
from django.db import models


class JournalEntry(models.Model):
    BIAS_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('', 'Not Set'),
    ]

    # Basic fields
    date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Simple URL fields
    ltf = models.TextField(blank=True, help_text="LTF Chart URL")
    htf = models.TextField(blank=True, help_text="HTF Chart URL")

    # Trading details
    bias = models.CharField(max_length=10, choices=BIAS_CHOICES, blank=True)
    array = models.TextField(
        blank=True, help_text="Comma-separated array values")
    results = models.TextField(
        blank=True, help_text="Comma-separated result values")

    # Performance
    pnl = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Profit and Loss"
    )

    # Psychology and analysis
    emotions = models.TextField(
        blank=True, null=True, help_text="Comma-separated emotion values")
    before_trade_emotions = models.TextField(
        blank=True, null=True, help_text="Comma-separated emotion values")
    in_trade_emotions = models.TextField(
        blank=True, null=True, help_text="Comma-separated emotion values")
    after_trade_emotions = models.TextField(
        blank=True, null=True, help_text="Comma-separated emotion values")

    mistake = models.TextField(
        blank=True, null=True, help_text="Comma-separated emotion values")
    reason = models.TextField(
        blank=True, null=True, help_text="Why did you take this trade?")

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"

    def __str__(self):
        date_str = self.date.strftime('%Y-%m-%d') if self.date else 'No Date'
        return f"{date_str} - {self.bias.title() if self.bias else 'No Bias'} - P&L: {self.pnl}"

    @property
    def is_profitable(self):
        return self.pnl > 0

    @property
    def is_loss(self):
        return self.pnl < 0

# Simple stats model


class TradingStats(models.Model):
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    total_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def update_stats(self):
        """Update stats based on all journal entries"""
        from django.db.models import Sum
        entries = JournalEntry.objects.all()

        self.total_trades = entries.count()
        self.winning_trades = entries.filter(pnl__gt=0).count()
        self.losing_trades = entries.filter(pnl__lt=0).count()
        self.total_pnl = entries.aggregate(Sum('pnl'))['pnl__sum'] or 0
        self.win_rate = (self.winning_trades / self.total_trades *
                         100) if self.total_trades > 0 else 0
        self.save()

    def __str__(self):
        return f"Trading Stats - {self.total_trades} trades"
