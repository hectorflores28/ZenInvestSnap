import json
from decimal import Decimal
from unittest.mock import PropertyMock, patch

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Asset, DailySnapshot, PortfolioValue, SavingsRateChange, Transaction
from .utils import ExchangeRateError
from .views import exchange_rate


class AssetManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='investor', password='test-password')
        self.client.force_login(self.user)
        self.asset = Asset.objects.create(
            user=self.user,
            ticker='NVIDIA',
            name='NVIDIA',
            asset_type='CRYPTO',
            source='GBM',
        )

    def test_asset_can_be_corrected_to_the_public_market_symbol_and_type(self):
        response = self.client.post(
            reverse('edit_asset', args=[self.asset.pk]),
            {
                'ticker': 'nvda',
                'name': 'NVIDIA',
                'asset_type': 'STOCK',
                'source': 'GBM',
                'annual_yield_rate': '0',
            },
        )

        self.assertRedirects(
            response,
            reverse('dashboard'),
            fetch_redirect_response=False,
        )
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.ticker, 'NVDA')
        self.assertEqual(self.asset.asset_type, 'STOCK')

    def test_transaction_form_prevents_selling_more_than_the_registered_balance(self):
        Transaction.objects.create(
            user=self.user,
            asset=self.asset,
            action='BUY',
            quantity=Decimal('2'),
            price=Decimal('100'),
            date=timezone.now(),
        )
        from .forms import TransactionForm

        form = TransactionForm(
            {
                'asset': str(self.asset.pk),
                'action': 'SELL',
                'quantity': '3',
                'price': '100',
                'date': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)


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


class CurrentPriceUtilityTests(TestCase):
    @patch('main.utils.yf.Ticker')
    def test_crypto_pair_quoted_in_mxn_uses_the_yahoo_usd_symbol(self, ticker):
        from .utils import get_current_price

        ticker.return_value.fast_info.last_price = 123

        self.assertEqual(get_current_price('BTC-MXN', 'CRYPTO'), Decimal('123'))
        ticker.assert_called_once_with('BTC-USD')

    @patch('main.utils.yf.Ticker')
    def test_history_is_used_when_fast_info_raises(self, ticker):
        from .utils import get_current_price

        ticker_object = ticker.return_value
        fast_info = PropertyMock(side_effect=KeyError('currentTradingPeriod'))
        with patch.object(type(ticker_object), 'fast_info', fast_info, create=True):
            history = ticker_object.history.return_value
            history.empty = False
            history.__getitem__.return_value.iloc.__getitem__.return_value = 42

            self.assertEqual(get_current_price('NVDA', 'STOCK'), Decimal('42'))

        ticker_object.history.assert_called_once_with(period='1d')


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

    @patch('main.utils.get_current_price', return_value=Decimal('10'))
    @patch('main.utils.get_usd_mxn_rate', return_value=Decimal('18'))
    def test_sync_stores_usd_quotes_and_portfolio_totals_in_mxn(
        self, get_rate, get_current_price
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

    @patch('main.utils.get_current_price', return_value=Decimal('10'))
    @patch('main.utils.get_usd_mxn_rate', side_effect=ExchangeRateError('Offline'))
    def test_sync_does_not_relabel_an_old_usd_snapshot_as_mxn(
        self, get_rate, get_current_price
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

    @patch('main.utils.get_current_price', return_value=Decimal('1000000'))
    @patch('main.utils.get_usd_mxn_rate', return_value=Decimal('18'))
    def test_mxn_quoted_crypto_is_converted_from_yahoo_usd(
        self, get_rate, get_current_price
    ):
        from .utils import perform_snapshot

        self.assertTrue(perform_snapshot(self.user))

        snapshot = DailySnapshot.objects.get(asset=self.asset)
        portfolio = PortfolioValue.objects.get(user=self.user)
        self.assertEqual(snapshot.closing_price, Decimal('18000000'))
        self.assertTrue(snapshot.currency_normalized)
        self.assertEqual(portfolio.total_market_value, Decimal('180.00'))
        get_current_price.assert_called_once_with('BTC-MXN', 'CRYPTO')
        get_rate.assert_called_once_with()

    @patch('main.utils.get_current_price', return_value=Decimal('1000000'))
    @patch('main.utils.get_usd_mxn_rate', return_value=Decimal('18'))
    def test_same_crypto_on_different_platforms_keeps_separate_transaction_balances(
        self, get_rate, get_current_price
    ):
        from datetime import timedelta

        from .utils import perform_snapshot

        bitso_asset = Asset.objects.create(
            user=self.user,
            ticker='BTC-MXN',
            name='Bitcoin en Bitso',
            asset_type='CRYPTO',
            source='BITSO',
            latest_quantity=Decimal('0.5'),
        )
        bought_at = timezone.now() - timedelta(days=1)
        Transaction.objects.create(
            user=self.user,
            asset=bitso_asset,
            action='BUY',
            quantity=Decimal('0.5'),
            price=Decimal('1000000'),
            date=bought_at,
        )
        Transaction.objects.create(
            user=self.user,
            asset=bitso_asset,
            action='SELL',
            quantity=Decimal('0.5'),
            price=Decimal('1100000'),
            date=bought_at + timedelta(hours=1),
        )

        self.assertTrue(perform_snapshot(self.user))

        bitso_asset.refresh_from_db()
        self.asset.refresh_from_db()
        mercado_pago_snapshot = DailySnapshot.objects.get(asset=self.asset)
        bitso_snapshot = DailySnapshot.objects.get(asset=bitso_asset)
        portfolio = PortfolioValue.objects.get(user=self.user)
        self.assertEqual(self.asset.latest_quantity, Decimal('0.00001'))
        self.assertEqual(bitso_asset.latest_quantity, Decimal('0'))
        self.assertEqual(mercado_pago_snapshot.closing_price, Decimal('18000000'))
        self.assertEqual(bitso_snapshot.closing_price, Decimal('0'))
        self.assertEqual(portfolio.total_market_value, Decimal('180.00'))
        get_current_price.assert_called_once_with('BTC-MXN', 'CRYPTO')
        get_rate.assert_called_once_with()

        from .views import dashboard

        request = RequestFactory().get(reverse('dashboard'))
        request.user = self.user
        with patch(
            'main.views.render',
            side_effect=lambda request, template, context: context,
        ):
            dashboard_context = dashboard(request)
        bitso_data = next(
            source for source in dashboard_context['dashboard_data']
            if source['source_code'] == 'BITSO'
        )
        self.assertEqual(bitso_data['assets_detail'][0]['quantity'], Decimal('0'))


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

    def test_sync_saves_savings_balance_as_a_normalized_mxn_snapshot(self):
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
