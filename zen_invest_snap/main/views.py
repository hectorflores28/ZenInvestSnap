from django.shortcuts import render
from django.db.models import Sum, F
from .models import Asset, DailySnapshot, PortfolioValue, Transaction
from decimal import Decimal

def dashboard(request):
    """
    Central Dashboard View.
    Displays:
    1. Overall Portfolio Value (Traffic Light).
    2. Breakdown by Source (GBM, Bitso, Nu, Mercado Pago).
    """
    # 1. Overall Portfolio Summary (Last available)
    latest_portfolio = PortfolioValue.objects.order_by('-date').first()
    
    # 2. Assets grouped by Source
    sources = ['GBM', 'BITSO', 'NU', 'MERCADO_PAGO', 'OTHER']
    
    dashboard_data = [] # List of dicts: {'source': 'GBM', 'total_value': X, 'assets': []}
    
    overall_total_calculated = Decimal('0.0')

    for source in sources:
        assets = Asset.objects.filter(source=source)
        source_data = {
            'source_label': source.replace('_', ' ').title(),
            'source_code': source,
            'total_value': Decimal('0.0'),
            'assets_detail': []
        }
        
        for asset in assets:
            # Get latest snapshot for this asset
            snapshot = asset.daily_snapshots.order_by('-date').first()
            
            # Calculate Quantity held (simplified logic for view, duplicate of command logic ideally refactored)
            # For view speed, maybe we should store 'current_quantity' on Asset?
            # For now, let's recalculate quickly or just show price.
            # Ideally, the Snapshot contains the value. But Snapshot only has 'closing_price'.
            # We need Quantity to know the Value.
            # Let's Calculate Quantity on the fly. available in Transaction.
            # TODO: Refactor 'get_current_quantity' to model or utils.
            
            txs = asset.transactions.all()
            qty = Decimal('0.0')
            invested = Decimal('0.0') # Simple sum of buys? Or Avg Cost?
            # Let's do simple qty sum for now to get value
            for tx in txs:
                if tx.action in ['BUY', 'DEPOSIT']:
                    qty += tx.quantity
                elif tx.action in ['SELL', 'WITHDRAWAL']:
                    qty -= tx.quantity
            
            if qty < 0: qty = Decimal('0.0') # Should not happen
            
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

    context = {
        'portfolio': latest_portfolio, 
        # Note: latest_portfolio.total_market_value might differ slightly if snapshots updated 
        # but portfolio record didn't. 
        'dashboard_data': dashboard_data,
        'calculated_total': overall_total_calculated
    }
    
    return render(request, 'main/dashboard.html', context)
