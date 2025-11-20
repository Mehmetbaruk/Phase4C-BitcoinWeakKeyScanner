"""
Validator Module
================

Validates recovered private keys and their corresponding addresses.
Ensures key recovery results are correct before reporting.

Validation Steps:
1. Private key format validation
2. Address derivation from private key
3. Address format validation (testnet/mainnet)
4. Match verification
"""

import hashlib
from typing import Optional
import logging
from bitcoinlib.keys import Key


class Validator:
    """
    Validates Bitcoin private keys and addresses.
    
    Ensures testnet-only operation and correct key recovery.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the validator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.testnet_only = config['safety']['testnet_only']
        self.allowed_prefixes = config['safety']['allowed_prefixes']
        self.network = 'testnet' if self.testnet_only else 'bitcoin'
        
        self.logger = logging.getLogger(__name__)
        
        if self.testnet_only:
            self.logger.info("Validator initialized in TESTNET-ONLY mode")
    
    def validate_private_key_format(self, private_key_hex: str) -> bool:
        """
        Validate private key format.
        
        Args:
            private_key_hex: Private key as hex string
            
        Returns:
            True if valid format, False otherwise
        """
        try:
            # Check length (should be 64 hex characters = 32 bytes)
            if len(private_key_hex) != 64:
                self.logger.warning(f"Invalid private key length: {len(private_key_hex)}")
                return False
            
            # Check if valid hex
            int(private_key_hex, 16)
            
            # Check if non-zero
            if int(private_key_hex, 16) == 0:
                self.logger.warning("Private key is zero")
                return False
            
            # Check if within valid range (must be < secp256k1 order)
            secp256k1_order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
            if int(private_key_hex, 16) >= secp256k1_order:
                self.logger.warning("Private key exceeds secp256k1 order")
                return False
            
            return True
        
        except ValueError:
            self.logger.warning(f"Invalid hex string: {private_key_hex}")
            return False
    
    def validate_address_format(self, address: str) -> bool:
        """
        Validate Bitcoin address format.
        
        Args:
            address: Bitcoin address to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not address:
            return False
        
        # Check length
        if len(address) < 26 or len(address) > 62:
            self.logger.warning(f"Invalid address length: {len(address)}")
            return False
        
        # Check testnet prefix if in testnet-only mode
        if self.testnet_only:
            if not any(address.startswith(prefix) for prefix in self.allowed_prefixes):
                self.logger.error(f"SECURITY: Non-testnet address rejected: {address}")
                return False
        
        return True
    
    def derive_address_from_private_key(self, private_key_hex: str) -> Optional[str]:
        """
        Derive Bitcoin address from private key.
        
        Args:
            private_key_hex: Private key as hex string
            
        Returns:
            Derived Bitcoin address, or None if derivation fails
        """
        try:
            key = Key(private_key_hex, network=self.network)
            address = key.address()
            
            self.logger.debug(f"Derived address: {address}")
            
            return address
        
        except Exception as e:
            self.logger.error(f"Address derivation failed: {e}")
            return None
    
    def validate_key_address_match(self, private_key_hex: str, expected_address: str) -> bool:
        """
        Validate that a private key produces the expected address.
        
        Args:
            private_key_hex: Private key as hex string
            expected_address: Expected Bitcoin address
            
        Returns:
            True if key produces expected address, False otherwise
        """
        self.logger.debug(f"Validating key/address match for {expected_address}")
        
        # Validate private key format
        if not self.validate_private_key_format(private_key_hex):
            self.logger.error("Private key format validation failed")
            return False
        
        # Validate address format
        if not self.validate_address_format(expected_address):
            self.logger.error("Address format validation failed")
            return False
        
        # Derive address from private key
        derived_address = self.derive_address_from_private_key(private_key_hex)
        
        if derived_address is None:
            self.logger.error("Address derivation failed")
            return False
        
        # Check match
        if derived_address != expected_address:
            self.logger.warning(f"Address mismatch: expected {expected_address}, got {derived_address}")
            return False
        
        self.logger.info(f"Validation successful: key matches address {expected_address}")
        return True
    
    def validate_recovery_result(self, result: dict) -> bool:
        """
        Validate a complete recovery result dictionary.
        
        Args:
            result: Recovery result dictionary
            
        Returns:
            True if all validations pass, False otherwise
        """
        required_fields = ['address', 'private_key', 'seed']
        
        # Check required fields
        for field in required_fields:
            if field not in result:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Validate key/address match
        is_valid = self.validate_key_address_match(
            result['private_key'],
            result['address']
        )
        
        if is_valid:
            self.logger.info(f"Recovery result validated for {result['address']}")
        else:
            self.logger.error(f"Recovery result validation failed for {result['address']}")
        
        return is_valid
    
    def batch_validate(self, results: list) -> dict:
        """
        Validate multiple recovery results.
        
        Args:
            results: List of recovery result dictionaries
            
        Returns:
            Validation summary dictionary
        """
        self.logger.info(f"Batch validating {len(results)} recovery results")
        
        valid_count = 0
        invalid_count = 0
        errors = []
        
        for result in results:
            try:
                if self.validate_recovery_result(result):
                    valid_count += 1
                else:
                    invalid_count += 1
                    errors.append({
                        'address': result.get('address', 'unknown'),
                        'error': 'Validation failed'
                    })
            except Exception as e:
                invalid_count += 1
                errors.append({
                    'address': result.get('address', 'unknown'),
                    'error': str(e)
                })
        
        summary = {
            'total': len(results),
            'valid': valid_count,
            'invalid': invalid_count,
            'success_rate': (valid_count / len(results) * 100) if results else 0,
            'errors': errors
        }
        
        self.logger.info(f"Batch validation complete: {valid_count}/{len(results)} valid")
        
        return summary
