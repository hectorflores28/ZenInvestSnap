import yfinance as yf
import logging
import requests
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from .models import Asset, DailySnapshot, PortfolioValue, Transaction

logger = logging.getLogger(__name__)


class ExchangeRateError(Exception):
    """Raised when the online USD/MXN exchange rate cannot be retrieved."""


def get_usd_mxn_rate():
    """Return Yahoo Finance's latest USD/MXN market quote."""
    try:
        response = requests.get(
            'https://query1.finance.yahoo.com/v8/finance/chart/MXN=X',
            params={'range': '1d', 'interval': '1m'},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=(3, 5),
        )
        response.raise_for_status()
        rate = Decimal(
            str(response.json()['chart']['result'][0]['meta']['regularMarketPrice'])
        )
    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        InvalidOperation,
    ) as exc:
        raise ExchangeRateError('Unable to retrieve the USD/MXN exchange rate.') from exc

    if not rate.is_finite() or rate <= 0:
        raise ExchangeRateError('The USD/MXN exchange rate was invalid.')
    return rate


def is_usd_quoted(asset):
    """Yahoo Finance quotes are USD unless the ticker indicates MXN."""
    ticker = asset.ticker.upper()
    return (
        (asset.asset_type == 'FIAT' and ticker == 'USD')
        or (
            asset.asset_type in ['STOCK', 'ETF', 'CRYPTO']
            and not ticker.endswith(('.MX', '-MXN'))
        )
    )


def calculate_savings_balance(asset, as_of_date=None):
    """Calculate simple daily interest on the net principal of a savings asset."""
    as_of_date = as_of_date or timezone.localdate()
    rate_changes = list(
        asset.savings_rate_changes.filter(effective_date__lte=as_of_date).order_by(
            'effective_date',
            'pk',
        )
    )
    annual_rate = (
        rate_changes[0].annual_yield_rate
        if rate_changes
        else asset.annual_yield_rate
    ) / Decimal('100')
    principal = Decimal('0')
    interest = Decimal('0')
    previous_date = None

    transactions = asset.transactions.filter(user=asset.user).order_by('date', 'pk')
    events = [
        (rate.effective_date, 0, rate)
        for rate in rate_changes
    ]
    for transaction in transactions:
        transaction_date = timezone.localtime(transaction.date).date()
        if transaction_date > as_of_date:
            break
        events.append((transaction_date, 1, transaction))
    events.sort(key=lambda event: (event[0], event[1]))

    for event_date, event_type, event in events:
        if previous_date is not None:
            elapsed_days = (event_date - previous_date).days
            interest += principal * annual_rate * elapsed_days / Decimal('365')

        if event_type == 0:
            annual_rate = event.annual_yield_rate / Decimal('100')
        else:
            amount = event.quantity * event.price
            if event.action in ['BUY', 'DEPOSIT']:
                principal += amount
            elif event.action in ['SELL', 'WITHDRAWAL']:
                principal -= amount
        previous_date = event_date

    if previous_date is not None:
        elapsed_days = (as_of_date - previous_date).days
        interest += principal * annual_rate * elapsed_days / Decimal('365')

    return principal, principal + interest


def get_current_price(ticker, asset_type):
    """
    Fetches the current price of an asset based on its type.
    For STOCK, ETF, and CRYPTO, it uses yfinance.
    """
    if asset_type in ['STOCK', 'ETF', 'CRYPTO']:
        try:
            lookup_ticker = ticker
            if asset_type == 'CRYPTO' and '-' not in ticker:
                lookup_ticker = f"{ticker}-USD"
            
            ticker_obj = yf.Ticker(lookup_ticker)
            price = ticker_obj.fast_info.last_price
            if price is None:
                 hist = ticker_obj.history(period="1d")
                 if not hist.empty:
                     price = hist['Close'].iloc[-1]
            
            if price:
                return Decimal(str(price))
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None
    return None

def perform_snapshot(user):
    """
    Core logic to sync and calculate portfolio status for a specific user.
    """
    from bitso.provider import BitsoProvider
    from .models import Asset, DailySnapshot, PortfolioValue
    
    today = timezone.localtime().date()
    
    # 1. Sync Holdings (Placeholder for multi-user keys, using provider logic)
    # In a real app, BitsoProvider would take user credentials.
    providers = {
        'BITSO': BitsoProvider(),
    }
    
    for source, provider in providers.items():
        try:
            holdings = provider.get_holdings()
            for ticker, qty in holdings.items():
                asset, created = Asset.objects.get_or_create(
                    user=user,
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
        except:
            # Skip if provider fails
            pass

    # 2. Update Prices and Snapshots
    total_market_value = Decimal('0.0')
    total_invested = Decimal('0.0')
    currency_normalized = True

    assets = list(Asset.objects.filter(user=user))
    usd_mxn_rate = None
    if any(is_usd_quoted(asset) for asset in assets):
        try:
            usd_mxn_rate = get_usd_mxn_rate()
        except ExchangeRateError:
            logger.warning('Unable to get USD/MXN rate; using saved MXN snapshots where available.')
    
    for asset in assets:
        # Calculate Cost Basis from Transactions
        txs = asset.transactions.filter(user=user).order_by('date')
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
        
        # Determine Quantity to use
        if asset.source in providers:
            current_qty = asset.latest_quantity
        else:
            current_qty = calc_qty
            asset.latest_quantity = calc_qty
            asset.save()
        
        # Fetch Price
        price = None
        if asset.asset_type == 'SAVINGS':
            _, current_qty = calculate_savings_balance(asset, today)
            asset.latest_quantity = current_qty
            asset.save(update_fields=['latest_quantity'])
            price = Decimal('1.0')
        elif current_qty <= 0:
            price = Decimal('0.0')
        elif asset.asset_type == 'FIAT' and asset.ticker.upper() == 'MXN':
            price = Decimal('1.0')
        elif asset.asset_type == 'FIAT' and asset.ticker.upper() == 'USD':
            if usd_mxn_rate is not None:
                price = usd_mxn_rate
        else:
            fetched_price = get_current_price(asset.ticker, asset.asset_type)
            if fetched_price is not None:
                if is_usd_quoted(asset):
                    if usd_mxn_rate is not None:
                        price = fetched_price * usd_mxn_rate
                else:
                    price = fetched_price

        if price is None:
            last_snapshot = asset.daily_snapshots.order_by('-date').first()
            if last_snapshot and (
                not is_usd_quoted(asset) or last_snapshot.currency_normalized
            ):
                price = last_snapshot.closing_price

        if price is not None:
            DailySnapshot.objects.update_or_create(
                asset=asset,
                date=today,
                defaults={
                    'closing_price': price,
                    'currency_normalized': True,
                }
            )
        else:
            currency_normalized = False
            logger.warning(
                'Skipping snapshot for %s because its USD price could not be converted to MXN.',
                asset.ticker,
            )
            price = Decimal('0.0')
        
        total_market_value += (current_qty * price)
        total_invested += calc_cost

    # 3. Save Portfolio Global Entry
    PortfolioValue.objects.update_or_create(
        user=user,
        date=today,
        defaults={
            'total_market_value': total_market_value,
            'total_invested': total_invested,
            'currency_normalized': currency_normalized,
        }
    )
    return currency_normalized
