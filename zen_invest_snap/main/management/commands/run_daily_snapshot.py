from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Asset, DailySnapshot, PortfolioValue, Transaction
from main.utils import get_current_price
from bitso.provider import BitsoProvider

class Command(BaseCommand):
    help = 'Runs the daily snapshot: syncs holdings from APIs, fetches prices, and calculates portfolio value.'

    def handle(self, *args, **options):
        self.stdout.write("Starting daily snapshot...")
        today = timezone.localtime().date()

        # 0. Sync Holdings from APIs
        self.stdout.write("Syncing holdings...")
        
        # Initialize Providers
        providers = {
            'BITSO': BitsoProvider(),
            # 'GBM': GbmProvider(), # Placeholder
        }
        
        # Fetch data from providers
        # This returns { 'BITSO': { 'BTC': 0.5, 'MXN': 1000 }, ... }
        synced_data = {} 
        for source, provider in providers.items():
            self.stdout.write(f"Querying {source}...")
            holdings = provider.get_holdings()
            synced_data[source] = holdings
            
            # Update Assets in DB based on API data
            for ticker, qty in holdings.items():
                # Find or Create Asset? 
                # Better to only update existing, or create if we are sure about types.
                # Let's try to get asset by Ticker + Source
                asset, created = Asset.objects.get_or_create(
                     ticker=ticker, 
                     source=source,
                     defaults={
                         'name': f"{ticker} ({source})",
                         'asset_type': 'CRYPTO' if source == 'BITSO' and ticker != 'MXN' else 'FIAT',
                         'latest_quantity': qty
                     }
                )
                if not created:
                    asset.latest_quantity = qty
                    asset.save()
                    
        total_market_value = Decimal('0.0')
        total_invested = Decimal('0.0')

        assets = Asset.objects.all()
        
        for asset in assets:
            # 1. Determine Quantity
            # If source is in our synced list, use latest_quantity (API Truth)
            # Else (OTHER, or API failed/not implemented), use Transaction Calculation (Manual Truth)
            
            current_qty = Decimal('0.0')
            current_cost = Decimal('0.0')
            
            # We ALWAYS calculate cost basis from transactions effectively
            # But what about Quantity?
            
            txs = asset.transactions.all().order_by('date')
            calc_qty = Decimal('0.0')
            calc_cost = Decimal('0.0')
            
            for tx in txs:
                if tx.action in ['BUY', 'DEPOSIT']:
                    calc_cost += tx.quantity * tx.price
                    calc_qty += tx.quantity
                elif tx.action in ['SELL', 'WITHDRAWAL']:
                     if calc_qty > 0:
                        avg_price = calc_cost / calc_qty
                        cost_reduction = tx.quantity * avg_price
                        calc_cost -= cost_reduction
                        calc_qty -= tx.quantity
                     else:
                        calc_qty -= tx.quantity
            
            # Decide which Qty to use for Market Value
            if asset.source in providers:
                # Use API quantity
                current_qty = asset.latest_quantity
            else:
                # Use Calculated quantity
                current_qty = calc_qty
                # Also update latest_quantity field for consistency
                asset.latest_quantity = calc_qty
                asset.save()
            
            # The 'Invested' amount is always what we put in (calc_cost), 
            # unless we withdrew everything from API but didn't record withdrawal tx?
            # That would break the logic. 
            # Assumption: User records Deposits/Withdrawals manually. 
            # API updates Market Variations (Price & Accrued Interest/Staking that increases Qty).
            
            current_cost = calc_cost

            # 2. Fetch Current Price
            price = Decimal('0.0')
            
            # Special case for FIAT (MXN, USD) - Price is 1 (relative to base currency usually)
            # Assuming Base Currency is Local (MXN)
            if asset.asset_type == 'FIAT' and asset.ticker == 'MXN':
                price = Decimal('1.0')
            elif current_qty > 0:
                self.stdout.write(f"Fetching price for {asset.ticker}...")
                fetched_price = get_current_price(asset.ticker, asset.asset_type)
                
                if fetched_price is not None:
                    price = fetched_price
                else:
                    self.stdout.write(self.style.WARNING(f"Could not fetch price for {asset.ticker}."))
                    last_tx = txs.last()
                    price = last_tx.price if last_tx else Decimal('0.0')

            DailySnapshot.objects.update_or_create(
                asset=asset,
                date=today,
                defaults={'closing_price': price}
            )
            
            market_value = current_qty * price
            total_market_value += market_value
            total_invested += current_cost
            
            self.stdout.write(f"{asset.ticker}: Qty {current_qty} | Price {price} | Val {market_value} | Inv {current_cost}")

        # 4. Save Portfolio Value
        PortfolioValue.objects.update_or_create(
            date=today,
            defaults={
                'total_market_value': total_market_value,
                'total_invested': total_invested
            }
        )
        
        self.stdout.write(self.style.SUCCESS(f"Daily snapshot completed. Total Market: {total_market_value}, Total Invested: {total_invested}"))
