# aptos_api.py
import requests
import logging
from typing import Dict, List, Optional, Union

# Configure Logging
logger = logging.getLogger(__name__)

class AptosAPI:
    def __init__(self, api_url="https://fullnode.mainnet.aptoslabs.com/v1"):
        self.api_url = api_url
        self.headers = {"accept": "application/json"}
    
    def get_account_resources(self, address: str) -> Optional[List[Dict]]:
        """Fetch all resources owned by a specific address."""
        try:
            url = f"{self.api_url}/accounts/{address}/resources"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch account resources: {response.text}")
                return None

            return response.json()
        except Exception as e:
            logger.exception(f"Error fetching account resources: {str(e)}")
            return None
    
    def get_account_transactions(self, address: str, limit: int = 25) -> Optional[List[Dict]]:
        """Fetch recent transactions for an address."""
        try:
            url = f"{self.api_url}/accounts/{address}/transactions?limit={limit}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch transactions: {response.text}")
                return None

            return response.json()
        except Exception as e:
            logger.exception(f"Error fetching transactions: {str(e)}")
            return None
    
    def get_collection_data(self, creator_address: str, collection_name: str) -> Optional[Dict]:
        """Fetch data for a specific collection."""
        try:
            # This endpoint may vary based on Aptos implementation
            url = f"{self.api_url}/accounts/{creator_address}/resource/0x3::token::Collections"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch collection data: {response.text}")
                return None

            collections_data = response.json().get("data", {}).get("collections", {})
            
            # Find the specified collection
            for collection in collections_data.values():
                if collection.get("name") == collection_name:
                    return collection
                    
            logger.info(f"Collection '{collection_name}' not found for creator {creator_address}")
            return None
        except Exception as e:
            logger.exception(f"Error fetching collection data: {str(e)}")
            return None