from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Asset, DailySnapshot, PortfolioValue, Transaction
from main.utils import get_current_price

class Command(BaseCommand):
    help = 'Runs the daily snapshot: fetches prices, calculates portfolio value, and saves snapshots.'

    def handle(self, *args, **options):
        self.stdout.write("Starting daily snapshot...")
        today = timezone.localtime().date()

        total_market_value = Decimal('0.0')
        total_invested = Decimal('0.0')

        assets = Asset.objects.all()
        
        for asset in assets:
            # 1. Calculate current quantity and cost basis (Average Cost method)
            txs = asset.transactions.all().order_by('date')
            
            current_qty = Decimal('0.0')
            current_cost = Decimal('0.0')
            
            for tx in txs:
                if tx.action in ['BUY', 'DEPOSIT']:
                    current_cost += tx.quantity * tx.price
                    current_qty += tx.quantity
                elif tx.action in ['SELL', 'WITHDRAWAL']:
                    if current_qty > 0:
                        # Reduce cost proportionally (Average Cost)
                        avg_price = current_cost / current_qty
                        cost_reduction = tx.quantity * avg_price
                        current_cost -= cost_reduction
                        current_qty -= tx.quantity
                    else:
                        current_qty -= tx.quantity

            # Handle small floating point inaccuracies
            if current_qty < Decimal('0.00000001'):
                current_qty = Decimal('0.0')
                current_cost = Decimal('0.0')

            # 2. Fetch Current Price
            price = Decimal('0.0')
            if current_qty > 0:
                self.stdout.write(f"Fetching price for {asset.ticker}...")
                fetched_price = get_current_price(asset.ticker, asset.asset_type)
                
                if fetched_price is not None:
                    price = fetched_price
                else:
                    self.stdout.write(self.style.WARNING(f"Could not fetch price for {asset.ticker}. Using last transaction price."))
                    last_tx = txs.last()
                    price = last_tx.price if last_tx else Decimal('0.0')
            else:
                 # Asset not held, price might not matter for portfolio value, 
                 # but good to record if we want to track it.
                 # For now, let's just create snapshot with 0 or skip?
                 # If we have 0 qty, the value is 0.
                 pass

            # 3. Save DailySnapshot
            # We record the snapshot even if quantity is 0, to have price history if we want, 
            # OR we only record if active. Let's record.
            if price == 0 and current_qty == 0:
                # Try to fetch price even if not held? 
                # User might want to track watchlist. 
                # For now, let's just proceed.
                pass

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
