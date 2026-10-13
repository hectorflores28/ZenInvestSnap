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
    """Return whether the price fetched for an asset needs USD/MXN conversion."""
    ticker = asset.ticker.upper()
    if asset.asset_type == 'FIAT':
        return ticker == 'USD'
    if asset.asset_type == 'CRYPTO':
        return True
    return asset.asset_type in ['STOCK', 'ETF'] and not ticker.endswith('.MX')


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


def calculate_asset_position(asset):
    """Calculate an asset's remaining quantity and invested cost from its transactions."""
    quantity = Decimal('0')
    invested_cost = Decimal('0')
    transactions = asset.transactions.filter(user=asset.user).order_by('date', 'pk')

    for transaction in transactions:
        amount = transaction.quantity * transaction.price
        if transaction.action in ['BUY', 'DEPOSIT']:
            quantity += transaction.quantity
            invested_cost += amount
        elif transaction.action in ['SELL', 'WITHDRAWAL']:
            if quantity > 0:
                sold_quantity = min(transaction.quantity, quantity)
                average_cost = invested_cost / quantity
                invested_cost -= sold_quantity * average_cost
                quantity -= sold_quantity

    return quantity, invested_cost


def get_current_price(ticker, asset_type):
    """
    Fetches the current price of an asset based on its type.
    For STOCK, ETF, and CRYPTO, it uses yfinance.
    """
    if asset_type in ['STOCK', 'ETF', 'CRYPTO']:
        lookup_ticker = ticker.upper()
        if asset_type == 'CRYPTO':
            crypto, separator, quote_currency = lookup_ticker.partition('-')
            if not separator or quote_currency == 'MXN':
                lookup_ticker = f'{crypto}-USD'

        try:
            ticker_obj = yf.Ticker(lookup_ticker)
        except Exception:
            logger.warning(
                'Unable to initialize Yahoo Finance for %s.',
                ticker,
                exc_info=True,
            )
            return None
        try:
            price = ticker_obj.fast_info.last_price
        except Exception:
            logger.debug('Yahoo fast quote unavailable for %s.', lookup_ticker, exc_info=True)
            price = None

        if price is not None:
            try:
                decimal_price = Decimal(str(price))
                if decimal_price.is_finite() and decimal_price > 0:
                    return decimal_price
            except (InvalidOperation, TypeError, ValueError):
                pass

        try:
            history = ticker_obj.history(period='1d')
            if not history.empty:
                decimal_price = Decimal(str(history['Close'].iloc[-1]))
                if decimal_price.is_finite() and decimal_price > 0:
                    return decimal_price
        except Exception:
            logger.warning(
                'Unable to fetch price for %s from Yahoo Finance.',
                ticker,
                exc_info=True,
            )
            return None

        logger.warning('No valid Yahoo Finance price found for %s.', ticker)
    return None


def perform_snapshot(user):
    """
    Core logic to sync and calculate portfolio status for a specific user.
    """
    from .models import Asset, DailySnapshot, PortfolioValue
    
    today = timezone.localtime().date()

    # Update public prices and transaction-derived balances for registered assets.
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
        current_qty, calc_cost = calculate_asset_position(asset)
        asset.latest_quantity = current_qty
        asset.save(update_fields=['latest_quantity'])
        
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
                'Skipping snapshot for %s because a valid MXN price could not be retrieved.',
                asset.ticker,
            )
            price = Decimal('0.0')
        
        total_market_value += (current_qty * price)
        total_invested += calc_cost

    # Save the user's daily portfolio entry.
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
