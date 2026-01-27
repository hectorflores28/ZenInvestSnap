from django.db import models

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
    ticker = models.CharField(max_length=20, unique=True, help_text="e.g., AAPL, BTC, MXN")
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='OTHER')
    
    def __str__(self):
        return f"{self.ticker} - {self.name} ({self.source})"

class Transaction(models.Model):
    ACTIONS = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='transactions')
    action = models.CharField(max_length=10, choices=ACTIONS)
    quantity = models.DecimalField(max_digits=20, decimal_places=10, help_text="Positive value")
    price = models.DecimalField(max_digits=20, decimal_places=4, help_text="Price per unit at transaction time")
    date = models.DateTimeField()
    
    def __str__(self):
        return f"{self.action} {self.quantity} {self.asset.ticker} @ {self.price}"

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
    """Summary of the entire portfolio value for a specific day."""
    date = models.DateField(unique=True)
    total_market_value = models.DecimalField(max_digits=20, decimal_places=2)
    total_invested = models.DecimalField(max_digits=20, decimal_places=2)
    
    def __str__(self):
        return f"Portfolio on {self.date}: Val {self.total_market_value} / Inv {self.total_invested}"
    
    @property
    def profitability_percentage(self):
        if self.total_invested == 0:
            return 0
        return ((self.total_market_value - self.total_invested) / self.total_invested) * 100
