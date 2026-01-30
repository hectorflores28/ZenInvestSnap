from django.db import models
from django.contrib.auth.models import User

class Asset(models.Model):
    ASSET_TYPES = [
        ('STOCK', 'Stock'),
        ('CRYPTO', 'Cryptocurrency'),
        ('FIAT', 'Fiat Currency'),
        ('ETF', 'ETF'),
        ('BOND', 'Bond'),
    ]
    SOURCE_CHOICES = [
        ('GBM', 'GBM'),
        ('BITSO', 'Bitso'),
        ('NU', 'Nu'),
        ('MERCADO_PAGO', 'Mercado Pago'),
        ('OTHER', 'Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assets')
    ticker = models.CharField(max_length=20, help_text="e.g., AAPL, BTC, MXN")
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='OTHER')
    
    # Snapshot of the latest known quantity (updated by API or Transactions)
    latest_quantity = models.DecimalField(max_digits=20, decimal_places=10, default=0.0)

    class Meta:
        unique_together = ('user', 'ticker')

    def __str__(self):
        return f"{self.ticker} - {self.name} ({self.source}) - {self.user.username}"

class Transaction(models.Model):
    ACTIONS = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='transactions')
    action = models.CharField(max_length=10, choices=ACTIONS)
    quantity = models.DecimalField(max_digits=20, decimal_places=10, help_text="Positive value")
    price = models.DecimalField(max_digits=20, decimal_places=4, help_text="Price per unit at transaction time")
    date = models.DateTimeField()
    
    def __str__(self):
        return f"{self.action} {self.quantity} {self.asset.ticker} @ {self.price} - {self.user.username}"

class DailySnapshot(models.Model):
    """Stores the closing price of an asset for a specific day."""
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='daily_snapshots')
    date = models.DateField()
    closing_price = models.DecimalField(max_digits=20, decimal_places=4)
    
    class Meta:
        unique_together = ('asset', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.asset.ticker} on {self.date}: {self.closing_price}"

class PortfolioValue(models.Model):
    """Summary of the entire portfolio value for a specific day for a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolio_values')
    date = models.DateField()
    total_market_value = models.DecimalField(max_digits=20, decimal_places=2)
    total_invested = models.DecimalField(max_digits=20, decimal_places=2)
    
    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"Portfolio {self.user.username} on {self.date}: Val {self.total_market_value} / Inv {self.total_invested}"
    
    @property
    def profitability_percentage(self):
        if self.total_invested == 0:
            return 0
        return ((self.total_market_value - self.total_invested) / self.total_invested) * 100
