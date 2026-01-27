from django.contrib import admin
from .models import Asset, Transaction, DailySnapshot, PortfolioValue

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'name', 'asset_type', 'source')
    list_filter = ('asset_type', 'source')
    search_fields = ('ticker', 'name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'action', 'asset', 'quantity', 'price')
    list_filter = ('action', 'asset', 'date')
    search_fields = ('asset__ticker',)

@admin.register(DailySnapshot)
class DailySnapshotAdmin(admin.ModelAdmin):
    list_display = ('date', 'asset', 'closing_price')
    list_filter = ('date', 'asset')

@admin.register(PortfolioValue)
class PortfolioValueAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_market_value', 'total_invested', 'profitability_percentage')
    list_filter = ('date',)
