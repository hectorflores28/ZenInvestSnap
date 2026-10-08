from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from .models import Asset, DailySnapshot, PortfolioValue, Transaction
from .forms import TransactionForm, AssetForm
from .utils import ExchangeRateError, get_usd_mxn_rate, is_usd_quoted, perform_snapshot
from decimal import Decimal


@login_required
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, 'Transaction recorded!')
            return redirect('dashboard')
    else:
        form = TransactionForm(user=request.user)
    return render(request, 'main/form_page.html', {'form': form, 'title': 'Add Transaction'})

@login_required
def add_asset(request):
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.user = request.user
            asset.save()
            messages.success(request, 'Asset added!')
            return redirect('dashboard')
    else:
        form = AssetForm()
    return render(request, 'main/form_page.html', {'form': form, 'title': 'Add New Asset'})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now login.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    """
    Central Dashboard View.
    Displays:
    1. Overall Portfolio Value (Traffic Light).
    2. Breakdown by Source (GBM, Bitso, Nu, Mercado Pago).
    """
    # 1. Overall Portfolio Summary (Last available for this user)
    # 2. Assets grouped by Source
    sources = ['GBM', 'BITSO', 'NU', 'MERCADO_PAGO', 'OTHER']
    
    dashboard_data = [] # List of dicts: {'source': 'GBM', 'total_value': X, 'assets': []}
    
    overall_total_calculated = Decimal('0.0')
    overall_invested_calculated = Decimal('0.0')
    needs_currency_sync = False

    for source in sources:
        assets = Asset.objects.filter(user=request.user, source=source)
        source_data = {
            'source_label': source.replace('_', ' ').title(),
            'source_code': source,
            'total_value': Decimal('0.0'),
            'assets_detail': []
        }
        
        for asset in assets:
            # Get latest snapshot for this asset
            snapshot = asset.daily_snapshots.order_by('-date').first()
            
            # Use the latest quantity (Synched or Calculated)
            qty = asset.latest_quantity
            
            price_is_mxn = bool(
                snapshot
                and (
                    not is_usd_quoted(asset)
                    or snapshot.currency_normalized
                )
            )
            current_price = snapshot.closing_price if price_is_mxn else Decimal('0.0')
            current_value = qty * current_price
            if qty > 0 and is_usd_quoted(asset) and not price_is_mxn:
                needs_currency_sync = True
            
            # Calculate Invested per Asset
            asset_txs = Transaction.objects.filter(asset=asset, user=request.user).order_by('date')
            asset_qty = Decimal('0.0')
            asset_cost = Decimal('0.0')
            for tx in asset_txs:
                if tx.action in ['BUY', 'DEPOSIT']:
                    asset_cost += tx.quantity * tx.price
                    asset_qty += tx.quantity
                elif tx.action in ['SELL', 'WITHDRAWAL']:
                    if asset_qty > 0:
                        avg = asset_cost / asset_qty
                        asset_cost -= tx.quantity * avg
                        asset_qty -= tx.quantity
                    else:
                        asset_qty -= tx.quantity

            source_data['total_value'] += current_value
            overall_invested_calculated += asset_cost
            
            source_data['assets_detail'].append({
                'ticker': asset.ticker,
                'name': asset.name,
                'quantity': qty,
                'price': current_price,
                'value': current_value,
                'invested': asset_cost,
                'type': asset.asset_type,
                'price_is_mxn': price_is_mxn,
            })
            
        dashboard_data.append(source_data)
        overall_total_calculated += source_data['total_value']

    # Keep a year of daily history available for the chart's date-range filters.
    history = PortfolioValue.objects.filter(
        user=request.user,
        currency_normalized=True,
    ).order_by('-date')[:365]
    history = list(reversed(history))
    profitability_percentage = Decimal('0.0')
    if overall_invested_calculated > 0:
        profitability_percentage = (
            (overall_total_calculated - overall_invested_calculated)
            / overall_invested_calculated
        ) * 100

    context = {
        'dashboard_data': dashboard_data,
        'calculated_total': overall_total_calculated,
        'total_invested': overall_invested_calculated,
        'profitability_percentage': profitability_percentage,
        'needs_currency_sync': needs_currency_sync,
        'history': history,
    }
    
    return render(request, 'main/dashboard.html', context)

@login_required
@require_POST
def sync_data(request):
    """View to trigger manual sync."""
    currency_normalized = perform_snapshot(request.user)
    if currency_normalized:
        messages.success(request, 'Portfolio updated successfully!')
    else:
        messages.warning(
            request,
            'Some USD prices could not be converted. Their values remain pending until a successful sync.',
        )
    return redirect('dashboard')


@login_required
@require_GET
def exchange_rate(request):
    """Return the current online USD/MXN exchange rate for the dashboard."""
    try:
        rate = get_usd_mxn_rate()
    except ExchangeRateError:
        return JsonResponse(
            {'error': 'No se pudo obtener el tipo de cambio. Los montos siguen en MXN.'},
            status=503,
        )
    return JsonResponse({'rate': str(rate)})
