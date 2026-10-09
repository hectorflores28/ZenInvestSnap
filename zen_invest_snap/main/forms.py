from django import forms
from decimal import Decimal
from .models import Transaction, Asset

class TransactionForm(forms.ModelForm):
    # Optional: Allow user to select existing asset or provide details for a new one?
    # For simplicity, let's start with selecting existing assets for this user.
    
    class Meta:
        model = Transaction
        fields = ['asset', 'action', 'quantity', 'price', 'date']
        labels = {
            'price': 'Price per unit (MXN)',
        }
        help_texts = {
            'price': 'Enter the transaction price in Mexican pesos (MXN).',
        }
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['asset'].queryset = Asset.objects.filter(user=user)
            asset_id = self.data.get('asset') or getattr(self.instance, 'asset_id', None)
            asset = self.fields['asset'].queryset.filter(pk=asset_id).first()
            if asset and asset.asset_type == 'SAVINGS':
                self.fields['quantity'].label = 'Amount (MXN)'
                self.fields['quantity'].help_text = 'Amount deposited or withdrawn.'
                self.fields['price'].required = False
                self.fields['price'].initial = Decimal('1')
                self.fields['price'].widget = forms.HiddenInput()
        self.fields['price'].help_text = (
            'For a savings account, the unit price is fixed to 1 MXN.'
            if self.fields['price'].widget.is_hidden
            else 'For a savings account, enter 1 MXN; it is fixed automatically after selection.'
        )

    def clean(self):
        cleaned_data = super().clean()
        asset = cleaned_data.get('asset')
        if asset and asset.asset_type == 'SAVINGS':
            cleaned_data['price'] = Decimal('1')
            action = cleaned_data.get('action')
            quantity = cleaned_data.get('quantity')
            if action == 'WITHDRAWAL' and quantity is not None:
                principal = Decimal('0')
                for transaction in asset.transactions.order_by('date', 'pk'):
                    amount = transaction.quantity * transaction.price
                    if transaction.action in ['BUY', 'DEPOSIT']:
                        principal += amount
                    elif transaction.action in ['SELL', 'WITHDRAWAL']:
                        principal -= amount
                if quantity > principal:
                    self.add_error(
                        'quantity',
                        'The withdrawal cannot exceed the current principal balance.',
                    )
        return cleaned_data

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['ticker', 'name', 'asset_type', 'source', 'annual_yield_rate']
        labels = {
            'annual_yield_rate': 'Annual yield rate (%)',
        }
        help_texts = {
            'ticker': 'Use a unique code for each apartado, e.g. MP-CAJITA-EMERGENCIA.',
            'annual_yield_rate': 'Simple annual rate; update it to match the rate currently offered.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['annual_yield_rate'].required = False
        source = self.data.get('source') if self.is_bound else self.initial.get('source')
        if not self.is_bound and not self.instance.pk:
            self.initial.setdefault(
                'annual_yield_rate',
                Decimal('10.00') if source == 'MERCADO_PAGO' else (
                    Decimal('6.50') if source == 'NU' else Decimal('0.00')
                ),
            )
        self.fields['annual_yield_rate'].widget.attrs.update({
            'min': '0',
            'max': '100',
            'step': '0.01',
        })

    def clean(self):
        cleaned_data = super().clean()
        asset_type = cleaned_data.get('asset_type')
        rate = cleaned_data.get('annual_yield_rate')
        if asset_type == 'SAVINGS':
            if rate is None or rate <= 0 or rate > 100:
                self.add_error(
                    'annual_yield_rate',
                    'Enter an annual rate greater than 0 and no more than 100%.',
                )
        else:
            cleaned_data['annual_yield_rate'] = Decimal('0')
        return cleaned_data
