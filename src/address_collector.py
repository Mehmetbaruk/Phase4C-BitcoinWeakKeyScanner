"""
Address Collector Module - FIXED VERSION
========================

Gathers Bitcoin addresses from the blockchain using public APIs.
Implements rate limiting, caching, and testnet-only enforcement.

Features:
- Mempool.space API integration
- Exponential backoff retry logic
- Address validation and filtering
- Memory-efficient streaming
"""

import time
import requests
import json
from typing import List, Dict, Optional, Iterator
from datetime import datetime
import logging


class AddressCollector:
    """
    Collects Bitcoin testnet addresses from blockchain APIs.
    
    Implements safe API access with rate limiting and comprehensive
    error handling for production AWS deployment.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the address collector.
        
        Args:
            config: Configuration dictionary with API settings
        """
        self.config = config
        self.api_base_url = config['api']['base_url']
        self.rate_limit = config['api']['rate_limit']
        self.timeout = config['api']['timeout']
        self.retry_attempts = config['api']['retry_attempts']
        self.retry_delay = config['api']['retry_delay']
        self.testnet_only = config['safety']['testnet_only']
        self.allowed_prefixes = config['safety']['allowed_prefixes']
        
        self.logger = logging.getLogger(__name__)
        self.api_call_count = 0
        self.last_api_call = 0
        
        # Validate testnet configuration
        if self.testnet_only and 'testnet' not in self.api_base_url.lower():
            raise ValueError("Testnet-only mode requires testnet API URL")
    
    def _enforce_rate_limit(self):
        """Enforce API rate limiting."""
        elapsed = time.time() - self.last_api_call
        min_interval = 60.0 / self.rate_limit  # seconds between calls
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_api_call = time.time()
    
    def _make_api_request(self, endpoint: str, retry_count: int = 0, parse_json: bool = True):
        """
        Make an API request with retry logic.
        
        Args:
            endpoint: API endpoint to call
            retry_count: Current retry attempt number
            parse_json: Whether to parse response as JSON (False for plain text)
            
        Returns:
            API response as dictionary/string, or None on failure
        """
        self._enforce_rate_limit()
        
        url = f"{self.api_base_url}/{endpoint}"
        
        try:
            self.logger.debug(f"API request: {url}")
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            self.api_call_count += 1
            
            if not response.text:
                return {} if parse_json else ''
            
            if parse_json:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # If JSON parsing fails, return the text content
                    self.logger.debug(f"Response is not JSON, returning as text: {response.text[:100]}")
                    return response.text.strip()
            else:
                return response.text.strip()
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"API request failed: {e}")
            
            if retry_count < self.retry_attempts:
                delay = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                self.logger.info(f"Retrying in {delay} seconds... (attempt {retry_count + 1}/{self.retry_attempts})")
                time.sleep(delay)
                return self._make_api_request(endpoint, retry_count + 1, parse_json)
            
            self.logger.error(f"API request failed after {self.retry_attempts} attempts")
            return None
    
    def _validate_address(self, address: str) -> bool:
        """
        Validate that an address is a valid testnet address.
        
        Args:
            address: Bitcoin address to validate
            
        Returns:
            True if valid testnet address, False otherwise
        """
        if not address:
            return False
        
        # Check testnet prefix
        if self.testnet_only:
            if not any(address.startswith(prefix) for prefix in self.allowed_prefixes):
                self.logger.warning(f"Rejected non-testnet address: {address}")
                return False
        
        # Basic length validation
        if len(address) < 26 or len(address) > 62:
            return False
        
        return True
    
    def get_recent_blocks(self, count: int = 10) -> List[Dict]:
        """
        Get information about recent blocks.
        
        Args:
            count: Number of recent blocks to retrieve
            
        Returns:
            List of block information dictionaries
        """
        self.logger.info(f"Fetching {count} recent blocks")
        
        # Get blocks list directly
        blocks_data = self._make_api_request("blocks")
        if not blocks_data or not isinstance(blocks_data, list):
            return []
        
        return blocks_data[:count]
    
    def get_block_transactions(self, block_hash: str) -> List[str]:
        """
        Get transaction IDs from a specific block.
        
        Args:
            block_hash: Block hash to retrieve transactions from
            
        Returns:
            List of transaction IDs
        """
        self.logger.debug(f"Fetching transactions for block {block_hash[:16]}...")
        
        # Get transaction IDs from block
        tx_ids = self._make_api_request(f"block/{block_hash}/txids")
        if not tx_ids:
            return []
        
        if isinstance(tx_ids, list):
            return tx_ids[:100]  # Limit to first 100
        
        return []
    
    def get_transaction_addresses(self, tx_id: str) -> List[str]:
        """
        Extract addresses from a transaction.
        
        Args:
            tx_id: Transaction ID to analyze
            
        Returns:
            List of unique addresses involved in the transaction
        """
        self.logger.debug(f"Extracting addresses from transaction {tx_id[:16]}...")
        
        tx_data = self._make_api_request(f"tx/{tx_id}")
        if not tx_data or not isinstance(tx_data, dict):
            return []
        
        addresses = set()
        
        # Extract from inputs
        for vin in tx_data.get('vin', []):
            if vin and isinstance(vin, dict):
                prevout = vin.get('prevout')
                if prevout and isinstance(prevout, dict):
                    addr = prevout.get('scriptpubkey_address')
                    if addr and self._validate_address(addr):
                        addresses.add(addr)
        
        # Extract from outputs
        for vout in tx_data.get('vout', []):
            if vout and isinstance(vout, dict):
                addr = vout.get('scriptpubkey_address')
                if addr and self._validate_address(addr):
                    addresses.add(addr)
        
        return list(addresses)
    
    def collect_addresses_stream(self, target_count: int, start_block: Optional[int] = None) -> Iterator[Dict]:
        """
        Stream addresses from the blockchain without loading all into memory.
        
        This is a generator function optimized for AWS long-running execution.
        
        Args:
            target_count: Target number of addresses to collect
            start_block: Starting block height (None = most recent)
            
        Yields:
            Address information dictionaries with metadata
        """
        self.logger.info(f"Starting address collection stream (target: {target_count})")
        
        collected = 0
        seen_addresses = set()
        
        # Get recent blocks
        blocks_data = self._make_api_request("blocks")
        if not blocks_data or not isinstance(blocks_data, list):
            self.logger.error("Failed to get recent blocks")
            return
        
        self.logger.info(f"Retrieved {len(blocks_data)} recent blocks")
        
        for block in blocks_data:
            if collected >= target_count:
                break
            
            block_hash = block.get('id', '')
            block_height = block.get('height', 0)
            
            if not block_hash:
                continue
            
            self.logger.info(f"Processing block {block_height}: {block_hash[:16]}...")
            
            # Get transactions from this block
            tx_ids = self.get_block_transactions(block_hash)
            self.logger.info(f"Block {block_height} has {len(tx_ids)} transactions")
            
            for tx_id in tx_ids:
                if collected >= target_count:
                    break
                
                addresses = self.get_transaction_addresses(tx_id)
                
                for address in addresses:
                    if address not in seen_addresses:
                        seen_addresses.add(address)
                        
                        yield {
                            'address': address,
                            'block_height': block_height,
                            'block_hash': block_hash,
                            'transaction': tx_id,
                            'collected_at': datetime.now().isoformat()
                        }
                        
                        collected += 1
                        
                        if collected % 10 == 0:
                            self.logger.info(f"Collection progress: {collected}/{target_count} addresses")
                        
                        if collected >= target_count:
                            break
        
        self.logger.info(f"Address collection complete: {collected} addresses collected")
    
    def collect_addresses(self, count: int) -> List[Dict]:
        """
        Collect a specific number of addresses.
        
        Args:
            count: Number of addresses to collect
            
        Returns:
            List of address information dictionaries
        """
        return list(self.collect_addresses_stream(count))
    
    def get_address_details(self, address: str) -> Optional[Dict]:
        """
        Get detailed information about a specific address.
        
        Args:
            address: Bitcoin address to query
            
        Returns:
            Address details including balance and transaction count
        """
        if not self._validate_address(address):
            self.logger.warning(f"Invalid address format: {address}")
            return None
        
        addr_data = self._make_api_request(f"address/{address}")
        
        if addr_data:
            return {
                'address': address,
                'balance': addr_data.get('chain_stats', {}).get('funded_txo_sum', 0),
                'tx_count': addr_data.get('chain_stats', {}).get('tx_count', 0),
                'first_seen': addr_data.get('chain_stats', {}).get('funded_txo_count', 0),
                'last_seen': addr_data.get('chain_stats', {}).get('spent_txo_count', 0)
            }
        
        return None
    
    def get_stats(self) -> Dict:
        """
        Get collector statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'api_calls': self.api_call_count,
            'rate_limit': self.rate_limit,
            'testnet_only': self.testnet_only
        }
