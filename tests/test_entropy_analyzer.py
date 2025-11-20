"""
Test Suite for Entropy Analyzer
================================

Tests statistical analysis functionality.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from entropy_analyzer import EntropyAnalyzer


@pytest.fixture
def config():
    """Test configuration."""
    return {
        'analysis': {
            'entropy_threshold': 7.0,
            'suspicious_threshold': 7.5,
            'chi_square_p_threshold': 0.01
        }
    }


@pytest.fixture
def analyzer(config):
    """Create analyzer instance."""
    return EntropyAnalyzer(config)


def test_shannon_entropy_high(analyzer):
    """Test Shannon entropy calculation for high entropy data."""
    # Random-looking bytes should have high entropy
    data = bytes([i % 256 for i in range(256)])
    entropy = analyzer.calculate_shannon_entropy(data)
    
    assert entropy >= 7.5, "High entropy data should score >= 7.5"


def test_shannon_entropy_low(analyzer):
    """Test Shannon entropy calculation for low entropy data."""
    # Repeated bytes should have low entropy
    data = b'A' * 100
    entropy = analyzer.calculate_shannon_entropy(data)
    
    assert entropy < 1.0, "Low entropy data should score < 1.0"


def test_shannon_entropy_empty(analyzer):
    """Test Shannon entropy with empty data."""
    entropy = analyzer.calculate_shannon_entropy(b'')
    assert entropy == 0.0


def test_chi_square_uniform(analyzer):
    """Test chi-square test with uniform distribution."""
    # Create uniform distribution
    data = bytes([i % 256 for i in range(256 * 10)])
    chi_stat, p_value = analyzer.chi_square_test(data)
    
    # High p-value indicates uniform distribution
    assert p_value > 0.05, "Uniform data should have high p-value"


def test_chi_square_nonuniform(analyzer):
    """Test chi-square test with non-uniform distribution."""
    # Create biased distribution
    data = bytes([0] * 500 + [1] * 10)
    chi_stat, p_value = analyzer.chi_square_test(data)
    
    # Low p-value indicates non-uniform distribution
    assert p_value < 0.01, "Non-uniform data should have low p-value"


def test_analyze_address(analyzer):
    """Test complete address analysis."""
    # Test with a testnet address
    address = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"
    result = analyzer.analyze_address(address)
    
    assert 'address' in result
    assert 'shannon_entropy' in result
    assert 'chi_square_p_value' in result
    assert 'weakness_level' in result
    assert 'is_weak' in result
    assert result['address'] == address


def test_weakness_classification(analyzer):
    """Test weakness level classification."""
    # Test address with good entropy
    good_address = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx"
    result = analyzer.analyze_address(good_address)
    
    assert result['weakness_level'] in ['STRONG', 'GOOD', 'SUSPICIOUS', 'WEAK']


def test_batch_analyze(analyzer):
    """Test batch address analysis."""
    addresses = [
        "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx",
        "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7",
        "tb1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqthqst8"
    ]
    
    results = analyzer.batch_analyze(addresses)
    
    assert len(results) == len(addresses)
    assert all('address' in r for r in results)


def test_get_weak_addresses(analyzer):
    """Test filtering weak addresses."""
    analysis_results = [
        {'address': 'addr1', 'is_weak': True, 'shannon_entropy': 6.5},
        {'address': 'addr2', 'is_weak': False, 'shannon_entropy': 7.8},
        {'address': 'addr3', 'is_weak': True, 'shannon_entropy': 6.0}
    ]
    
    weak = analyzer.get_weak_addresses(analysis_results)
    
    assert len(weak) == 2
    assert all(r['is_weak'] for r in weak)


def test_entropy_report(analyzer):
    """Test entropy report generation."""
    analysis_results = [
        {'shannon_entropy': 7.5, 'weakness_level': 'GOOD', 'is_weak': False},
        {'shannon_entropy': 6.5, 'weakness_level': 'WEAK', 'is_weak': True},
        {'shannon_entropy': 7.8, 'weakness_level': 'STRONG', 'is_weak': False}
    ]
    
    report = analyzer.generate_entropy_report(analysis_results)
    
    assert report['total_analyzed'] == 3
    assert report['weak_count'] == 1
    assert 'entropy_stats' in report
    assert 'mean' in report['entropy_stats']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
