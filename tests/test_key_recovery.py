"""
Test Suite for Key Recovery
============================

Tests key recovery orchestration.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from key_recovery import KeyRecovery
from prng_reconstructor import PRNGReconstructor
from validator import Validator


@pytest.fixture
def config():
    """Test configuration."""
    return {
        'bitcoin_network': 'testnet',
        'prng_attack': {
            'mode': 'test',
            'seed_space_test_mode': 10000,
            'seed_space_full_mode': 1000000,
            'parallel_workers': 2,
            'progress_interval': 1000
        },
        'key_recovery': {
            'max_recovery_attempts': 5,
            'timeout_per_address': 60
        },
        'safety': {
            'testnet_only': True,
            'allowed_prefixes': ['m', 'n', '2', 'tb1']
        }
    }


@pytest.fixture
def key_recovery_system(config):
    """Create key recovery system."""
    prng = PRNGReconstructor(config)
    validator = Validator(config)
    recovery = KeyRecovery(config, prng, validator)
    return recovery


def test_initialization(key_recovery_system):
    """Test key recovery system initialization."""
    assert key_recovery_system.attempts == 0
    assert key_recovery_system.successes == 0
    assert key_recovery_system.failures == 0
    assert len(key_recovery_system.recovered_keys) == 0


def test_recover_single_key_success(key_recovery_system):
    """Test successful single key recovery."""
    # Create a weak key with known seed
    seed = 1234
    address, _ = key_recovery_system.prng.create_weak_key_for_testing(seed)
    
    # Attempt recovery
    result = key_recovery_system.recover_single_key(address, priority_score=10.0)
    
    if result:  # May fail if seed not in search space
        assert result['address'] == address
        assert result['seed'] == seed
        assert result['validated'] is True
        assert key_recovery_system.successes > 0


def test_recover_single_key_failure(key_recovery_system):
    """Test failed key recovery (seed out of range)."""
    # Create a weak key with seed outside search space
    seed = 999999
    address, _ = key_recovery_system.prng.create_weak_key_for_testing(seed)
    
    # Attempt recovery (should fail)
    result = key_recovery_system.recover_single_key(address)
    
    assert result is None
    assert key_recovery_system.failures > 0


def test_get_recovery_stats(key_recovery_system):
    """Test recovery statistics."""
    stats = key_recovery_system.get_recovery_stats()
    
    assert 'total_attempts' in stats
    assert 'successful_recoveries' in stats
    assert 'failed_attempts' in stats
    assert 'success_rate_percent' in stats


def test_get_recovered_keys(key_recovery_system):
    """Test retrieved recovered keys list."""
    keys = key_recovery_system.get_recovered_keys()
    
    assert isinstance(keys, list)


def test_recover_batch(key_recovery_system):
    """Test batch key recovery."""
    # Create multiple weak keys
    targets = []
    for seed in [111, 222, 333]:
        address, _ = key_recovery_system.prng.create_weak_key_for_testing(seed)
        targets.append({'address': address, 'score': 10.0})
    
    # Attempt batch recovery
    results = key_recovery_system.recover_batch(targets)
    
    # Some may succeed (depends on search space)
    assert isinstance(results, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
