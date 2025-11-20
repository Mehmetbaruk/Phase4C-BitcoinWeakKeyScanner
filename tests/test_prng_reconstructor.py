"""
Test Suite for PRNG Reconstructor
==================================

Tests MT19937 PRNG reconstruction and seed search.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from prng_reconstructor import PRNGReconstructor


@pytest.fixture
def config():
    """Test configuration."""
    return {
        'bitcoin_network': 'testnet',
        'prng_attack': {
            'mode': 'test',
            'seed_space_test_mode': 10000,  # Small for testing
            'seed_space_full_mode': 1000000,
            'parallel_workers': 2,
            'progress_interval': 1000
        }
    }


@pytest.fixture
def reconstructor(config):
    """Create PRNG reconstructor instance."""
    return PRNGReconstructor(config)


def test_generate_private_key(reconstructor):
    """Test private key generation from seed."""
    seed = 12345
    key = reconstructor.generate_private_key_from_seed(seed)
    
    assert len(key) == 32, "Private key should be 32 bytes"
    assert isinstance(key, bytes)


def test_deterministic_key_generation(reconstructor):
    """Test that same seed produces same key."""
    seed = 54321
    key1 = reconstructor.generate_private_key_from_seed(seed)
    key2 = reconstructor.generate_private_key_from_seed(seed)
    
    assert key1 == key2, "Same seed should produce same key"


def test_different_seeds_different_keys(reconstructor):
    """Test that different seeds produce different keys."""
    key1 = reconstructor.generate_private_key_from_seed(100)
    key2 = reconstructor.generate_private_key_from_seed(200)
    
    assert key1 != key2, "Different seeds should produce different keys"


def test_create_weak_key(reconstructor):
    """Test creation of weak key for testing."""
    seed = 99999
    address, private_key = reconstructor.create_weak_key_for_testing(seed)
    
    assert address is not None
    assert len(private_key) == 32
    assert isinstance(address, str)


def test_verify_seed(reconstructor):
    """Test seed verification."""
    # Create a weak key
    seed = 77777
    address, private_key = reconstructor.create_weak_key_for_testing(seed)
    
    # Verify the seed produces the address
    is_valid = reconstructor.verify_seed(seed, address)
    
    assert is_valid, "Seed should verify against its own address"


def test_verify_seed_wrong(reconstructor):
    """Test seed verification with wrong seed."""
    # Create a weak key
    seed = 11111
    address, _ = reconstructor.create_weak_key_for_testing(seed)
    
    # Try to verify with wrong seed
    is_valid = reconstructor.verify_seed(22222, address)
    
    assert not is_valid, "Wrong seed should not verify"


def test_test_seed_single(reconstructor):
    """Test single seed testing."""
    # Create a weak key
    test_seed = 55555
    address, _ = reconstructor.create_weak_key_for_testing(test_seed)
    
    # Test the seed
    result = reconstructor.test_seed_single(test_seed, address)
    
    assert result == test_seed, "Correct seed should be found"


def test_search_seed_range_found(reconstructor):
    """Test seed range search when seed is in range."""
    # Create a weak key with known seed
    target_seed = 1000
    address, _ = reconstructor.create_weak_key_for_testing(target_seed)
    
    # Search range containing the seed
    result = reconstructor.search_seed_range(900, 1100, address)
    
    assert result is not None, "Seed should be found in range"
    assert result[0] == target_seed, "Found seed should match target"


def test_search_seed_range_not_found(reconstructor):
    """Test seed range search when seed is not in range."""
    # Create a weak key
    target_seed = 5000
    address, _ = reconstructor.create_weak_key_for_testing(target_seed)
    
    # Search range not containing the seed
    result = reconstructor.search_seed_range(0, 100, address)
    
    assert result is None, "Seed should not be found outside range"


def test_sequential_search(reconstructor):
    """Test sequential seed reconstruction."""
    # Create a weak key with low seed (findable in test mode)
    target_seed = 500
    address, _ = reconstructor.create_weak_key_for_testing(target_seed)
    
    # Search with small max_seed
    result = reconstructor.reconstruct_seed_sequential(address, max_seed=1000)
    
    assert result is not None, "Seed should be found"
    assert result[0] == target_seed


def test_estimate_search_time(reconstructor):
    """Test search time estimation."""
    estimate = reconstructor.estimate_search_time(10000)
    
    assert 'seed_space' in estimate
    assert 'seeds_per_second' in estimate
    assert 'estimated_time_parallel' in estimate
    assert estimate['seed_space'] == 10000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
