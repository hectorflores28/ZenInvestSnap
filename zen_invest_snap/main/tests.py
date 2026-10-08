import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Asset, DailySnapshot, PortfolioValue, Transaction
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
