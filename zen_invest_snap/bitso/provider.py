import requests
import hashlib
import hmac
import time
import json
from decimal import Decimal
from main.providers import AssetProvider
import os

class BitsoProvider(AssetProvider):
    """
    Integration for Bitso Exchange.
    Requires BITSO_API_KEY and BITSO_API_SECRET in .env
    """
    
    def __init__(self):
        self.api_key = os.environ.get('BITSO_API_KEY')
        self.api_secret = os.environ.get('BITSO_API_SECRET')
        self.base_url = "https://api.bitso.com/v3"
        
    def _get_auth_header(self, http_method, request_path, json_payload=''):
        nonce = str(int(round(time.time() * 1000)))
        message = nonce + http_method + request_path + json_payload
        signature = hmac.new(self.api_secret.encode('utf-8'),
                             message.encode('utf-8'),
                             hashlib.sha256).hexdigest()
        
        return f'Bitso {self.api_key}:{nonce}:{signature}'

    def get_holdings(self):
        if not self.api_key or not self.api_secret:
            print("Warning: BITSO_API_KEY or BITSO_API_SECRET not found.")
            return {}
            
        endpoint = "/balance/"
        url = self.base_url + endpoint
        
        try:
            auth_header = self._get_auth_header("GET", endpoint)
            headers = {'Authorization': auth_header}
            
            response = requests.get(url, headers=headers)
            data = response.json()
            
            if not data.get('success'):
                print(f"Bitso API Error: {data.get('error')}")
                return {}
                
            holdings = {}
            # Bitso returns 'balances' list
            for balance in data['payload']['balances']:
                currency = balance['currency'].upper()
                total = Decimal(balance['total'])
                
                # Filter out dust/zero balances
                if total > Decimal('0.00000001'):
                    # Normalize weird tickers if needed, Bitso uses standard codes mostly (btc, eth, mxn)
                    holdings[currency] = total
                    
            return holdings
            
        except Exception as e:
            print(f"Error fetching Bitso holdings: {e}")
            return {}
