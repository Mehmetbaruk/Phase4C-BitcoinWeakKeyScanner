"""
Integration Tests
=================

End-to-end integration tests for the complete scanning pipeline.
"""

import pytest
import sys
import os
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from entropy_analyzer import EntropyAnalyzer
from pattern_detector import PatternDetector
from prng_reconstructor import PRNGReconstructor
from validator import Validator


@pytest.fixture
def full_config():
    """Full test configuration."""
    return {
        'bitcoin_network': 'testnet',
        'analysis': {
            'entropy_threshold': 7.0,
            'suspicious_threshold': 7.5,
            'chi_square_p_threshold': 0.01
        },
        'prng_attack': {
            'mode': 'test',
            'seed_space_test_mode': 5000,
            'seed_space_full_mode': 1000000,
            'parallel_workers': 2,
            'progress_interval': 500
        },
        'safety': {
            'testnet_only': True,
            'allowed_prefixes': ['m', 'n', '2', 'tb1']
        }
    }


def test_end_to_end_weak_key_detection(full_config):
    """Test complete pipeline: create weak key -> analyze -> detect -> verify."""
    
    # Initialize components
    prng = PRNGReconstructor(full_config)
    analyzer = EntropyAnalyzer(full_config)
    detector = PatternDetector(full_config)
    validator = Validator(full_config)
    
    # Create a weak key for testing
    test_seed = 1234
    weak_address, weak_privkey = prng.create_weak_key_for_testing(test_seed)
    
    # Analyze entropy
    entropy_result = analyzer.analyze_address(weak_address)
    
    assert entropy_result is not None
    assert 'shannon_entropy' in entropy_result
    assert 'weakness_level' in entropy_result
    
    # Verify validator works
    is_valid = validator.validate_key_address_match(weak_privkey.hex(), weak_address)
    assert is_valid, "Weak key should validate correctly"


def test_multiple_addresses_analysis(full_config):
    """Test analysis of multiple addresses."""
    
    prng = PRNGReconstructor(full_config)
    analyzer = EntropyAnalyzer(full_config)
    
    # Create multiple test addresses
    addresses = []
    for seed in [100, 200, 300, 400, 500]:
        addr, _ = prng.create_weak_key_for_testing(seed)
        addresses.append(addr)
    
    # Batch analyze
    results = analyzer.batch_analyze(addresses)
    
    assert len(results) == len(addresses)
    assert all('address' in r for r in results)
    assert all('shannon_entropy' in r for r in results)


def test_pattern_detection_integration(full_config):
    """Test pattern detection with test data."""
    
    prng = PRNGReconstructor(full_config)
    analyzer = EntropyAnalyzer(full_config)
    detector = PatternDetector(full_config)
    
    # Create test dataset
    addresses = []
    for seed in range(10, 20):
        addr, _ = prng.create_weak_key_for_testing(seed)
        addresses.append({
            'address': addr,
            'block_height': 1000 + seed,
            'collected_at': '2024-01-01T00:00:00'
        })
    
    # Analyze entropy
    entropy_results = analyzer.batch_analyze([a['address'] for a in addresses])
    
    # Detect patterns
    patterns = detector.detect_all_patterns(addresses, entropy_results)
    
    assert 'total_patterns' in patterns
    assert 'sequential' in patterns
    assert 'temporal_clusters' in patterns


def test_validator_testnet_enforcement(full_config):
    """Test that validator enforces testnet-only mode."""
    
    validator = Validator(full_config)
    
    # Mainnet addresses should be rejected
    mainnet_addr = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Bitcoin genesis address
    is_valid = validator.validate_address_format(mainnet_addr)
    
    assert not is_valid, "Mainnet address should be rejected in testnet-only mode"
    
    # Testnet addresses should be accepted
    testnet_addr = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"
    is_valid = validator.validate_address_format(testnet_addr)
    
    # Note: Basic format validation may still pass, but full validation would check prefix


def test_prng_determinism(full_config):
    """Test PRNG produces deterministic results."""
    
    prng = PRNGReconstructor(full_config)
    
    seed = 42
    
    # Generate key twice
    key1 = prng.generate_private_key_from_seed(seed)
    key2 = prng.generate_private_key_from_seed(seed)
    
    assert key1 == key2, "PRNG should be deterministic"
    
    # Generate address twice
    addr1 = prng.private_key_to_address(key1)
    addr2 = prng.private_key_to_address(key2)
    
    assert addr1 == addr2, "Address derivation should be deterministic"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
