import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Asset, DailySnapshot, PortfolioValue, SavingsRateChange, Transaction
from .utils import ExchangeRateError
from .views import exchange_rate


class ExchangeRateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='investor', password='test-password')
        self.client.force_login(self.user)

    @patch('main.views.get_usd_mxn_rate', return_value=Decimal('17.25'))
    def test_returns_online_rate(self, get_rate):
        response = self.client.get(reverse('exchange_rate'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'rate': '17.25'})
        get_rate.assert_called_once_with()

    @patch(
        'main.views.get_usd_mxn_rate',
        side_effect=ExchangeRateError('Rate unavailable'),
    )
    def test_rate_failure_is_reported_without_a_fallback(self, get_rate):
        request = RequestFactory().get(reverse('exchange_rate'))
        request.user = self.user
        response = exchange_rate(request)

        self.assertEqual(response.status_code, 503)
        self.assertIn('error', json.loads(response.content))
        get_rate.assert_called_once_with()

    def test_sync_requires_post(self):
        response = self.client.get(reverse('sync_data'))

        self.assertEqual(response.status_code, 405)


class ExchangeRateUtilityTests(TestCase):
    @patch('main.utils.requests.get')
    def test_get_usd_mxn_rate_uses_latest_yahoo_market_quote(self, get):
        from .utils import get_usd_mxn_rate

        response = get.return_value
        response.json.return_value = {
            'chart': {
                'result': [
                    {'meta': {'regularMarketPrice': 18.41}},
                ],
            },
        }

        self.assertEqual(get_usd_mxn_rate(), Decimal('18.41'))
        get.assert_called_once_with(
            'https://query1.finance.yahoo.com/v8/finance/chart/MXN=X',
            params={'range': '1d', 'interval': '1m'},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=(3, 5),
        )

    @patch('main.utils.requests.get')
    def test_get_usd_mxn_rate_rejects_invalid_market_quote(self, get):
        from .utils import ExchangeRateError, get_usd_mxn_rate

        response = get.return_value
        response.json.return_value = {
            'chart': {
                'result': [
                    {'meta': {'regularMarketPrice': 0}},
                ],
            },
        }
        response.raise_for_status.return_value = None

        with self.assertRaises(ExchangeRateError):
            get_usd_mxn_rate()


class PortfolioCurrencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='investor', password='test-password')
        asset = Asset.objects.create(
            user=self.user,
            ticker='AAPL',
            name='Apple',
            asset_type='STOCK',
            source='GBM',
            latest_quantity=Decimal('2'),
        )
        Transaction.objects.create(
            user=self.user,
            asset=asset,
            action='BUY',
            quantity=Decimal('2'),
            price=Decimal('100'),
            date=timezone.now(),
        )

    @patch('bitso.provider.BitsoProvider.get_holdings', return_value={})
    @patch('main.utils.get_current_price', return_value=Decimal('10'))
    @patch('main.utils.get_usd_mxn_rate', return_value=Decimal('18'))
    def test_sync_stores_usd_quotes_and_portfolio_totals_in_mxn(
        self, get_rate, get_current_price, get_holdings
    ):
        from .utils import perform_snapshot

        self.assertTrue(perform_snapshot(self.user))

        snapshot = DailySnapshot.objects.get(asset__ticker='AAPL')
        portfolio = PortfolioValue.objects.get(user=self.user)
        self.assertEqual(snapshot.closing_price, Decimal('180'))
        self.assertTrue(snapshot.currency_normalized)
        self.assertEqual(portfolio.total_market_value, Decimal('360'))
        self.assertEqual(portfolio.total_invested, Decimal('200'))
        self.assertTrue(portfolio.currency_normalized)
        get_rate.assert_called_once_with()
        get_current_price.assert_called_once_with('AAPL', 'STOCK')

    @patch('bitso.provider.BitsoProvider.get_holdings', return_value={})
    @patch('main.utils.get_current_price', return_value=Decimal('10'))
    @patch('main.utils.get_usd_mxn_rate', side_effect=ExchangeRateError('Offline'))
    def test_sync_does_not_relabel_an_old_usd_snapshot_as_mxn(
        self, get_rate, get_current_price, get_holdings
    ):
        from datetime import timedelta

        from .utils import perform_snapshot

        asset = Asset.objects.get(ticker='AAPL')
        old_snapshot = DailySnapshot.objects.create(
            asset=asset,
            date=timezone.localdate() - timedelta(days=1),
            closing_price=Decimal('10'),
        )

        self.assertFalse(perform_snapshot(self.user))

        old_snapshot.refresh_from_db()
        portfolio = PortfolioValue.objects.get(user=self.user)
        self.assertFalse(old_snapshot.currency_normalized)
        self.assertFalse(portfolio.currency_normalized)
        self.assertEqual(portfolio.total_market_value, Decimal('0'))
        self.assertFalse(
            DailySnapshot.objects.filter(asset=asset, date=timezone.localdate()).exists()
        )
        get_rate.assert_called_once_with()
        get_current_price.assert_called_once_with('AAPL', 'STOCK')


class MxnQuotedAssetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='investor', password='test-password')
        self.asset = Asset.objects.create(
            user=self.user,
            ticker='BTC-MXN',
            name='Bitcoin',
            asset_type='CRYPTO',
            source='MERCADO_PAGO',
        )
        Transaction.objects.create(
            user=self.user,
            asset=self.asset,
            action='BUY',
            quantity=Decimal('0.00001'),
            price=Decimal('1000000'),
            date=timezone.now(),
        )

    @patch('bitso.provider.BitsoProvider.get_holdings', return_value={})
    @patch('main.utils.get_usd_mxn_rate')
    @patch('main.utils.get_current_price', return_value=Decimal('1000000'))
    def test_mxn_quoted_crypto_does_not_require_usd_conversion(
        self, get_current_price, get_rate, get_holdings
    ):
        from .utils import perform_snapshot

        self.assertTrue(perform_snapshot(self.user))

        snapshot = DailySnapshot.objects.get(asset=self.asset)
        portfolio = PortfolioValue.objects.get(user=self.user)
        self.assertEqual(snapshot.closing_price, Decimal('1000000'))
        self.assertTrue(snapshot.currency_normalized)
        self.assertEqual(portfolio.total_market_value, Decimal('10.00'))
        get_current_price.assert_called_once_with('BTC-MXN', 'CRYPTO')
        get_rate.assert_not_called()


class SavingsYieldTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='investor', password='test-password')
        self.asset = Asset.objects.create(
            user=self.user,
            ticker='MP-CAJITA',
            name='Cajita de emergencia',
            asset_type='SAVINGS',
            source='MERCADO_PAGO',
            annual_yield_rate=Decimal('10'),
        )

    def test_simple_daily_yield_uses_each_contribution_date_and_withdrawal(self):
        from datetime import date, datetime, timezone as datetime_timezone

        from .utils import calculate_savings_balance

        Transaction.objects.create(
            user=self.user,
            asset=self.asset,
            action='DEPOSIT',
            quantity=Decimal('1000'),
            price=Decimal('1'),
            date=datetime(2026, 1, 1, tzinfo=datetime_timezone.utc),
        )
        Transaction.objects.create(
            user=self.user,
            asset=self.asset,
            action='WITHDRAWAL',
            quantity=Decimal('200'),
            price=Decimal('1'),
            date=datetime(2026, 1, 11, tzinfo=datetime_timezone.utc),
        )

        principal, balance = calculate_savings_balance(self.asset, date(2026, 1, 21))

        expected_interest = (
            Decimal('1000') * Decimal('.10') * 10 / 365
            + Decimal('800') * Decimal('.10') * 10 / 365
        )
        self.assertEqual(principal, Decimal('800'))
        self.assertEqual(balance, Decimal('800') + expected_interest)

    def test_rate_change_applies_only_from_its_effective_date(self):
        from datetime import date, datetime, timezone as datetime_timezone

        from .utils import calculate_savings_balance

        SavingsRateChange.objects.create(
            asset=self.asset,
            effective_date=date(2026, 1, 1),
            annual_yield_rate=Decimal('10'),
        )
        SavingsRateChange.objects.create(
            asset=self.asset,
            effective_date=date(2026, 1, 11),
            annual_yield_rate=Decimal('20'),
        )
        Transaction.objects.create(
            user=self.user,
            asset=self.asset,
            action='DEPOSIT',
            quantity=Decimal('1000'),
            price=Decimal('1'),
            date=datetime(2026, 1, 1, tzinfo=datetime_timezone.utc),
        )

        principal, balance = calculate_savings_balance(self.asset, date(2026, 1, 21))

        expected_interest = (
            Decimal('1000') * Decimal('.10') * 10 / 365
            + Decimal('1000') * Decimal('.20') * 10 / 365
        )
        self.assertEqual(principal, Decimal('1000'))
        self.assertEqual(balance, Decimal('1000') + expected_interest)

    @patch('bitso.provider.BitsoProvider.get_holdings', return_value={})
    def test_sync_saves_savings_balance_as_a_normalized_mxn_snapshot(self, get_holdings):
        from .utils import perform_snapshot

        Transaction.objects.create(
            user=self.user,
            asset=self.asset,
            action='DEPOSIT',
            quantity=Decimal('1000'),
            price=Decimal('1'),
            date=timezone.now(),
        )

        self.assertTrue(perform_snapshot(self.user))

        snapshot = DailySnapshot.objects.get(asset=self.asset)
        portfolio = PortfolioValue.objects.get(user=self.user)
        self.assertEqual(snapshot.closing_price, Decimal('1.0'))
        self.assertTrue(snapshot.currency_normalized)
        self.assertEqual(portfolio.total_market_value, Decimal('1000'))
        self.assertEqual(portfolio.total_invested, Decimal('1000'))
        self.assertTrue(portfolio.currency_normalized)
