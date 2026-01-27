from abc import ABC, abstractmethod
from decimal import Decimal

class AssetProvider(ABC):
    """
    Abstract Base Class for Asset Providers (Integrations).
    Each integration (Bitso, GBM, etc.) must implement this.
    """
    
    def __init__(self, **kwargs):
        self.config = kwargs
        
    @abstractmethod
    def get_holdings(self):
        """
        Returns a dictionary of holdings:
        {
            'TICKER': Decimal('quantity'),
            ...
        }
        """
        pass
    
    @abstractmethod
    def get_prices(self, tickers):
        """
        Optional: Returns current prices if the provider supports it.
        {
            'TICKER': Decimal('price'),
            ...
        }
        """
        return {}
