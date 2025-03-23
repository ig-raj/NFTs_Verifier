# nft_verifier.py
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime, timedelta

from aptos_api import AptosAPI
from db import get_known_scammers

# Configure Logging
logger = logging.getLogger(__name__)

class NFTVerifier:
    def __init__(self):
        self.aptos_api = AptosAPI()
        self.known_scammers = get_known_scammers()
    
    def get_nft_data_by_owner(self, owner_address: str) -> Dict:
        """Fetch and verify all NFTs owned by an address."""
        resources = self.aptos_api.get_account_resources(owner_address)
        if not resources:
            return {"nfts": [], "is_verified": False, "reason": "No resources found"}
        
        # Parse NFTs
        nfts = []
        for resource in resources:
            if "token" in resource.get("type", ""):
                raw_data = resource.get("data", {})
                
                # Log the raw data structure for debugging
                logger.debug(f"Raw NFT data: {raw_data}")
                
                # Extract and format NFT data to match frontend expectations
                formatted_nft = {
                    "name": raw_data.get("name", "Unnamed NFT"),
                    "id": raw_data.get("token_id", raw_data.get("id", "N/A")),
                    "collection": raw_data.get("collection_name", raw_data.get("collection", "N/A")),
                    "creator": raw_data.get("creator_address", raw_data.get("creator", "N/A")),
                    "metadata": raw_data,  # Keep all raw data in metadata for reference
                }
                
                # Include any additional fields from the original data
                formatted_nft["resource_type"] = resource.get("type")
                
                # Add URI if available
                if "uri" in raw_data:
                    formatted_nft["uri"] = raw_data["uri"]
                
                # Add description if available
                if "description" in raw_data:
                    formatted_nft["description"] = raw_data["description"]
                
                nfts.append(formatted_nft)
        
        # Parse token/coin balances
        token_balances = []
        for resource in resources:
            if "coin" in resource.get("type", "").lower() or "token" in resource.get("type", "").lower():
                raw_data = resource.get("data", {})
                if "value" in raw_data or "amount" in raw_data:
                    token_name = self._extract_token_name(resource.get("type", ""))
                    token_balance = {
                        "name": token_name,
                        "amount": raw_data.get("value", raw_data.get("amount", 0)),
                        "resource_type": resource.get("type", "")
                    }
                    token_balances.append(token_balance)
        
        # Get transaction history for risk analysis and activity parsing
        tx_history = self.aptos_api.get_account_transactions(owner_address)
        
        # Parse account activities
        account_activities = self._parse_account_activities(tx_history)
        
        # Create verification result
        verification_result = self._verify_nfts(nfts, tx_history)
        
        # Compile the complete account information
        account_info = {
            "owner_address": owner_address,
            "nfts": nfts,
            "token_balances": token_balances,
            "account_activities": account_activities,
            "is_scammer": owner_address in self.known_scammers,
            "verification_results": verification_result
        }
        
        # Log the number of NFTs found
        logger.info(f"Found {len(nfts)} NFTs for owner {owner_address}")
        logger.info(f"Found {len(token_balances)} token balances for owner {owner_address}")
        
        return account_info
    
    def get_nft_data_by_collection(self, creator_address: str, collection_name: str, token_id: Optional[str] = None) -> Dict:
        """
        Fetch and verify NFTs for a specific collection, optionally filtering by token ID.
        
        Args:
            creator_address: Address of the collection creator
            collection_name: Name of the collection
            token_id: Optional token ID to filter by
            
        Returns:
            Dictionary containing collection data and verification results
        """
        collection_data = self.aptos_api.get_collection_data(creator_address, collection_name)
        if not collection_data:
            return {"collection_data": None, "is_verified": False, "reason": "Collection not found"}
        
        # Format collection items to match frontend expectations
        if "items" in collection_data and isinstance(collection_data["items"], list):
            formatted_items = []
            for item in collection_data["items"]:
                formatted_item = {
                    "name": item.get("name", "Unnamed Item"),
                    "id": item.get("token_id", item.get("id", "N/A")),
                    "owner": item.get("owner", "N/A"),
                    "metadata": item  # Keep the original data
                }
                formatted_items.append(formatted_item)
            
            collection_data["items"] = formatted_items
        
        # Get transaction history for risk analysis
        tx_history = self.aptos_api.get_account_transactions(creator_address)
        
        verification_result = {
            "creator_address": creator_address,
            "collection_name": collection_name,
            "collection_data": collection_data,
            "is_scammer": creator_address in self.known_scammers,
            "verification_results": self._verify_collection(collection_data, tx_history)
        }
        
        # If token_id is provided, filter collection tokens to get the specific one
        if token_id:
            logger.info(f"Filtering collection for token ID: {token_id}")
            tokens = collection_data.get("tokens", [])
            filtered_tokens = [token for token in tokens if str(token.get("id")) == token_id]
            
            if filtered_tokens:
                token_data = filtered_tokens[0]
                
                # Format token data
                formatted_token = {
                    "name": token_data.get("name", "Unnamed Token"),
                    "id": token_data.get("token_id", token_data.get("id", "N/A")),
                    "owner": token_data.get("owner", "N/A"),
                    "creator": creator_address,
                    "collection": collection_name,
                    "metadata": token_data
                }
                
                verification_result["token_data"] = formatted_token
                # Add token-specific verification
                token_risk = self._analyze_nft_risk(formatted_token, tx_history)
                verification_result["token_verification"] = {
                    "risk_assessment": token_risk,
                    "is_verified": not token_risk["is_high_risk"]
                }
                logger.info(f"Token ID {token_id} found and verified")
            else:
                verification_result["token_data"] = None
                verification_result["token_verification"] = {
                    "is_verified": False,
                    "reason": "Token ID not found in collection"
                }
                logger.warning(f"Token ID {token_id} not found in collection {collection_name}")
        
        return verification_result
    
    def _extract_token_name(self, resource_type: str) -> str:
        """Extract token name from resource type string."""
        # Example: "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>" -> "AptosCoin"
        try:
            if "<" in resource_type and ">" in resource_type:
                inside_brackets = resource_type.split("<")[1].split(">")[0]
                if "::" in inside_brackets:
                    return inside_brackets.split("::")[-1]
            
            parts = resource_type.split("::")
            if len(parts) >= 3:
                return parts[2].split("<")[0]
                
            return resource_type.split("::")[-1]
        except Exception as e:
            logger.error(f"Error extracting token name from {resource_type}: {e}")
            return resource_type
    
    def _parse_account_activities(self, tx_history: List[Dict]) -> Dict:
        """Parse account activities from transaction history."""
        activities = {
            "nft_staking": False,
            "token_swaps": {
                "swap_count": 0,
                "listing_count": 0
            },
            "nft_transfers": {
                "deposit_count": 0,
                "withdraw_count": 0
            },
            "property_modifications": 0,
            "recent_transactions": []
        }
        
        # Process each transaction to identify activities
        for tx in tx_history:
            tx_type = tx.get("type", "").lower()
            events = tx.get("events", [])
            
            # Check for NFT staking
            if "stake" in tx_type or any("stake" in e.get("type", "").lower() for e in events):
                activities["nft_staking"] = True
                
            # Count token swaps
            if "swap" in tx_type or any("swap" in e.get("type", "").lower() for e in events):
                activities["token_swaps"]["swap_count"] += 1
                
            # Count listings
            if "list" in tx_type or any("list" in e.get("type", "").lower() for e in events):
                activities["token_swaps"]["listing_count"] += 1
                
            # Count NFT transfers
            for event in events:
                event_type = event.get("type", "").lower()
                if "deposit" in event_type:
                    activities["nft_transfers"]["deposit_count"] += 1
                if "withdraw" in event_type:
                    activities["nft_transfers"]["withdraw_count"] += 1
                    
            # Count property modifications
            property_events = [e for e in events if "property" in e.get("type", "").lower()]
            activities["property_modifications"] += len(property_events)
            
            # Add to recent transactions (limit to 5)
            if len(activities["recent_transactions"]) < 5:
                activities["recent_transactions"].append({
                    "type": tx.get("type", "Unknown"),
                    "timestamp": tx.get("timestamp", ""),
                    "success": tx.get("success", True)
                })
        
        return activities
    
    def _verify_nfts(self, nfts: List[Dict], tx_history: Optional[List[Dict]]) -> Dict:
        """Verify authenticity of a list of NFTs."""
        risk_scores = []
        questionable_nfts = []
        
        for nft in nfts:
            risk_result = self._analyze_nft_risk(nft, tx_history)
            risk_scores.append(risk_result["risk_score"])
            
            if risk_result["is_high_risk"]:
                questionable_nfts.append({
                    "nft_data": nft,
                    "risk_assessment": risk_result
                })
        
        return {
            "average_risk_score": sum(risk_scores) / len(risk_scores) if risk_scores else 0,
            "questionable_nfts": questionable_nfts,
            "is_verified": not questionable_nfts,
            "verification_timestamp": datetime.now().isoformat()
        }
    
    def _verify_collection(self, collection_data: Dict, tx_history: Optional[List[Dict]]) -> Dict:
        """Verify authenticity of a collection."""
        # Check for common signs of copied/fake collections
        risk_factors = []
        risk_score = 0
        
        # Check account age (if transaction history available)
        if tx_history:
            oldest_tx = min(tx_history, key=lambda x: x.get("timestamp", datetime.now().isoformat()))
            account_age_days = (datetime.now() - datetime.fromisoformat(oldest_tx.get("timestamp"))).days
            
            if account_age_days < 30:
                risk_score += 25
                risk_factors.append("NEW_CREATOR_ACCOUNT")
        
        # Check supply metrics
        supply = collection_data.get("supply", 0)
        if supply == 0:
            risk_factors.append("ZERO_SUPPLY")
            risk_score += 50
        elif supply < 5:
            risk_factors.append("VERY_LOW_SUPPLY")
            risk_score += 15
        
        # Check metadata completeness
        if not collection_data.get("description") or not collection_data.get("uri"):
            risk_factors.append("INCOMPLETE_METADATA")
            risk_score += 30
            
        is_high_risk = risk_score >= 60
        
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "is_high_risk": is_high_risk,
            "is_verified": not is_high_risk,
            "verification_timestamp": datetime.now().isoformat()
        }
    
    def _analyze_nft_risk(self, nft_data: Dict, tx_history: Optional[List[Dict]]) -> Dict:
        """Analyze risk factors for a single NFT."""
        risk_score = 0
        risk_factors = []
        
        # Check metadata completeness
        if not self._verify_nft_metadata(nft_data):
            risk_score += 40
            risk_factors.append("INCOMPLETE_METADATA")
        
        # Check transfer patterns if transaction history is available
        if tx_history:
            # Count NFT transfers
            transfer_count = sum(1 for tx in tx_history if self._is_nft_transfer(tx, nft_data))
            if transfer_count > 3:
                risk_score += 20 * (transfer_count - 3)
                risk_factors.append("HIGH_TRANSFER_VELOCITY")
        
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "is_high_risk": risk_score >= 70
        }
    
    def _verify_nft_metadata(self, nft_data: Dict) -> bool:
        """Check if NFT has complete metadata."""
        # Adjust these fields based on Aptos NFT structure
        # For the formatted data in our application
        basic_fields = ["name", "id"]  # These should be present in our formatted data
        
        # Check if basic fields exist
        if not all(field in nft_data for field in basic_fields):
            return False
            
        # The original metadata might have different requirements
        if "metadata" in nft_data:
            original_metadata = nft_data["metadata"]
            expected_fields = {"uri", "description"}
            if not any(field in original_metadata for field in expected_fields):
                return False
                
        return True
    
    def _is_nft_transfer(self, tx: Dict, nft_data: Dict) -> bool:
        """Check if a transaction is a transfer for the specified NFT."""
        # Logic to identify NFT transfers in transaction data
        # This will need adjustment based on Aptos transaction format
        if "transfer" not in tx.get("type", "").lower():
            return False
            
        # Additional checks could compare token IDs, collection names, etc.
        return True