"""
Entropy Analyzer Module
=======================

Statistical analysis of Bitcoin addresses for randomness quality.
Implements Shannon entropy, chi-square tests, and other statistical measures.

Core Algorithms:
- Shannon entropy: H = -Σ p(x) log₂ p(x)
- Chi-square test for uniform distribution
- Byte frequency analysis
- Pattern detection in hex representations
"""

import math
import hashlib
from typing import Dict, Tuple, List
from collections import Counter
import logging
from scipy import stats
import numpy as np


class EntropyAnalyzer:
    """
    Analyzes cryptographic entropy in Bitcoin addresses and keys.
    
    Detects weak randomness that could indicate PRNG vulnerabilities.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the entropy analyzer.
        
        Args:
            config: Configuration dictionary with analysis thresholds
        """
        self.config = config
        self.entropy_threshold = config['analysis']['entropy_threshold']
        self.suspicious_threshold = config['analysis']['suspicious_threshold']
        self.chi_square_threshold = config['analysis']['chi_square_p_threshold']
        
        self.logger = logging.getLogger(__name__)
    
    def calculate_shannon_entropy(self, data: bytes) -> float:
        """
        Calculate Shannon entropy of byte data.
        
        Formula: H = -Σ p(x) log₂ p(x)
        where p(x) is the probability of byte x
        
        Args:
            data: Bytes to analyze
            
        Returns:
            Entropy in bits per byte (0-8.0)
        """
        if not data:
            return 0.0
        
        # Count byte frequencies
        byte_counts = Counter(data)
        length = len(data)
        
        # Calculate probabilities and entropy
        entropy = 0.0
        for count in byte_counts.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def chi_square_test(self, data: bytes) -> Tuple[float, float]:
        """
        Perform chi-square test for uniform distribution.
        
        Tests whether byte frequencies match expected uniform distribution.
        Low p-value indicates non-random data.
        
        Args:
            data: Bytes to analyze
            
        Returns:
            Tuple of (chi_square_statistic, p_value)
        """
        if not data:
            return 0.0, 1.0
        
        # Count byte frequencies
        byte_counts = Counter(data)
        
        # Expected frequency for uniform distribution
        expected_freq = len(data) / 256.0
        
        # Observed frequencies for all 256 possible bytes
        observed = [byte_counts.get(i, 0) for i in range(256)]
        expected = [expected_freq] * 256
        
        # Perform chi-square test
        chi_stat, p_value = stats.chisquare(observed, expected)
        
        return chi_stat, p_value
    
    def byte_frequency_analysis(self, data: bytes) -> Dict[str, any]:
        """
        Analyze byte frequency distribution.
        
        Args:
            data: Bytes to analyze
            
        Returns:
            Dictionary with frequency statistics
        """
        if not data:
            return {'unique_bytes': 0, 'most_common': [], 'least_common': []}
        
        byte_counts = Counter(data)
        
        return {
            'unique_bytes': len(byte_counts),
            'total_bytes': len(data),
            'most_common': byte_counts.most_common(5),
            'least_common': byte_counts.most_common()[:-6:-1],
            'max_frequency': max(byte_counts.values()) if byte_counts else 0,
            'min_frequency': min(byte_counts.values()) if byte_counts else 0
        }
    
    def analyze_hex_patterns(self, hex_string: str) -> Dict[str, any]:
        """
        Detect patterns in hexadecimal representation.
        
        Args:
            hex_string: Hexadecimal string to analyze
            
        Returns:
            Dictionary with pattern detection results
        """
        if not hex_string:
            return {'patterns_found': []}
        
        patterns = []
        
        # Check for repeated sequences
        for length in [2, 4, 8]:
            for i in range(len(hex_string) - length * 2 + 1):
                chunk = hex_string[i:i+length]
                if hex_string[i+length:i+length*2] == chunk:
                    patterns.append({
                        'type': 'repetition',
                        'length': length,
                        'value': chunk,
                        'position': i
                    })
        
        # Check for sequential patterns
        sequential_count = 0
        for i in range(len(hex_string) - 1):
            try:
                if int(hex_string[i+1], 16) == int(hex_string[i], 16) + 1:
                    sequential_count += 1
                else:
                    if sequential_count >= 3:
                        patterns.append({
                            'type': 'sequential',
                            'length': sequential_count + 1,
                            'position': i - sequential_count
                        })
                    sequential_count = 0
            except ValueError:
                sequential_count = 0
        
        # Check for all same character
        char_counts = Counter(hex_string)
        for char, count in char_counts.items():
            if count > len(hex_string) * 0.3:  # More than 30% same character
                patterns.append({
                    'type': 'repeated_character',
                    'character': char,
                    'frequency': count / len(hex_string)
                })
        
        return {
            'patterns_found': patterns,
            'pattern_count': len(patterns)
        }
    
    def analyze_address(self, address: str) -> Dict[str, any]:
        """
        Comprehensive entropy analysis of a Bitcoin address.
        
        Args:
            address: Bitcoin address to analyze
            
        Returns:
            Dictionary with complete analysis results
        """
        self.logger.debug(f"Analyzing address: {address}")
        
        # Convert address to bytes for analysis
        address_bytes = address.encode('utf-8')
        
        # Hash the address for additional entropy source
        address_hash = hashlib.sha256(address_bytes).digest()
        
        # Calculate Shannon entropy
        entropy = self.calculate_shannon_entropy(address_bytes)
        hash_entropy = self.calculate_shannon_entropy(address_hash)
        
        # Perform chi-square test
        chi_stat, p_value = self.chi_square_test(address_hash)
        
        # Frequency analysis
        freq_analysis = self.byte_frequency_analysis(address_hash)
        
        # Pattern detection
        patterns = self.analyze_hex_patterns(address_hash.hex())
        
        # Determine weakness classification
        weakness_level = self._classify_weakness(entropy, p_value, patterns['pattern_count'])
        
        result = {
            'address': address,
            'shannon_entropy': round(entropy, 4),
            'hash_entropy': round(hash_entropy, 4),
            'chi_square_statistic': round(chi_stat, 4),
            'chi_square_p_value': round(p_value, 6),
            'unique_bytes': freq_analysis['unique_bytes'],
            'patterns_detected': patterns['pattern_count'],
            'pattern_details': patterns['patterns_found'],
            'weakness_level': weakness_level,
            'is_weak': weakness_level in ['WEAK', 'SUSPICIOUS']
        }
        
        self.logger.debug(f"Analysis complete: entropy={entropy:.2f}, weakness={weakness_level}")
        
        return result
    
    def _classify_weakness(self, entropy: float, p_value: float, pattern_count: int) -> str:
        """
        Classify the weakness level of an address.
        
        Args:
            entropy: Shannon entropy value
            p_value: Chi-square test p-value
            pattern_count: Number of detected patterns
            
        Returns:
            Weakness classification: STRONG, GOOD, SUSPICIOUS, or WEAK
        """
        # Multiple indicators of weakness
        weak_indicators = 0
        
        if entropy < self.entropy_threshold:
            weak_indicators += 2  # Strong indicator
        elif entropy < self.suspicious_threshold:
            weak_indicators += 1
        
        if p_value < self.chi_square_threshold:
            weak_indicators += 1
        
        if pattern_count > 3:
            weak_indicators += 1
        
        # Classify based on indicators
        if weak_indicators >= 3:
            return "WEAK"
        elif weak_indicators >= 2:
            return "SUSPICIOUS"
        elif weak_indicators >= 1:
            return "GOOD"
        else:
            return "STRONG"
    
    def batch_analyze(self, addresses: List[str]) -> List[Dict]:
        """
        Analyze multiple addresses in batch.
        
        Args:
            addresses: List of Bitcoin addresses
            
        Returns:
            List of analysis results
        """
        self.logger.info(f"Batch analyzing {len(addresses)} addresses")
        
        results = []
        for i, address in enumerate(addresses):
            try:
                result = self.analyze_address(address)
                results.append(result)
                
                if (i + 1) % 100 == 0:
                    self.logger.info(f"Analyzed {i + 1}/{len(addresses)} addresses")
            
            except Exception as e:
                self.logger.error(f"Failed to analyze address {address}: {e}")
                results.append({
                    'address': address,
                    'error': str(e),
                    'is_weak': False
                })
        
        return results
    
    def get_weak_addresses(self, analysis_results: List[Dict]) -> List[Dict]:
        """
        Filter analysis results to return only weak addresses.
        
        Args:
            analysis_results: List of analysis result dictionaries
            
        Returns:
            Filtered list containing only weak addresses
        """
        weak = [r for r in analysis_results if r.get('is_weak', False)]
        
        self.logger.info(f"Found {len(weak)} weak addresses out of {len(analysis_results)} total")
        
        return weak
    
    def generate_entropy_report(self, analysis_results: List[Dict]) -> Dict:
        """
        Generate statistical summary report of entropy analysis.
        
        Args:
            analysis_results: List of analysis result dictionaries
            
        Returns:
            Summary statistics dictionary
        """
        if not analysis_results:
            return {'total_analyzed': 0}
        
        entropies = [r['shannon_entropy'] for r in analysis_results if 'shannon_entropy' in r]
        weakness_counts = Counter(r.get('weakness_level', 'UNKNOWN') for r in analysis_results)
        
        report = {
            'total_analyzed': len(analysis_results),
            'weak_count': len([r for r in analysis_results if r.get('is_weak', False)]),
            'weakness_distribution': dict(weakness_counts),
            'entropy_stats': {
                'mean': round(np.mean(entropies), 4) if entropies else 0,
                'median': round(np.median(entropies), 4) if entropies else 0,
                'min': round(min(entropies), 4) if entropies else 0,
                'max': round(max(entropies), 4) if entropies else 0,
                'std_dev': round(np.std(entropies), 4) if entropies else 0
            },
            'thresholds': {
                'weak': self.entropy_threshold,
                'suspicious': self.suspicious_threshold
            }
        }
        
        return report
