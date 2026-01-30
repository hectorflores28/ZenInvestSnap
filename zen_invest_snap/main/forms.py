from django import forms
from .models import Transaction, Asset

class TransactionForm(forms.ModelForm):
    # Optional: Allow user to select existing asset or provide details for a new one?
    # For simplicity, let's start with selecting existing assets for this user.
    
    class Meta:
        model = Transaction
        fields = ['asset', 'action', 'quantity', 'price', 'date']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['asset'].queryset = Asset.objects.filter(user=user)

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['ticker', 'name', 'asset_type', 'source']
