from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Sum, F
from .models import Asset, DailySnapshot, PortfolioValue, Transaction
from .forms import TransactionForm, AssetForm
from .utils import perform_snapshot
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
    latest_portfolio = PortfolioValue.objects.filter(user=request.user).order_by('-date').first()
    
    # 2. Assets grouped by Source
    sources = ['GBM', 'BITSO', 'NU', 'MERCADO_PAGO', 'OTHER']
    
    dashboard_data = [] # List of dicts: {'source': 'GBM', 'total_value': X, 'assets': []}
    
    overall_total_calculated = Decimal('0.0')

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
            
            current_price = snapshot.closing_price if snapshot else Decimal('0.0')
            current_value = qty * current_price
            
            source_data['total_value'] += current_value
            
            source_data['assets_detail'].append({
                'ticker': asset.ticker,
                'name': asset.name,
                'quantity': qty,
                'price': current_price,
                'value': current_value,
                'type': asset.asset_type
            })
            
        dashboard_data.append(source_data)
        overall_total_calculated += source_data['total_value']

    # 3. History for Chart (Last 30 days)
    history = PortfolioValue.objects.filter(user=request.user).order_by('-date')[:30]
    history = sorted(history, key=lambda x: x.date)

    context = {
        'portfolio': latest_portfolio, 
        'dashboard_data': dashboard_data,
        'calculated_total': overall_total_calculated,
        'history': history,
    }
    
    return render(request, 'main/dashboard.html', context)

@login_required
def sync_data(request):
    """View to trigger manual sync."""
    perform_snapshot(request.user)
    messages.success(request, 'Portfolio updated successfully!')
    return redirect('dashboard')
