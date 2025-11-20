"""
Pattern Detector Module
=======================

Identifies weak key generation patterns in Bitcoin addresses.
Implements detection algorithms for common PRNG vulnerabilities.

Detection Methods:
- Sequential key detection (small private key differences)
- Temporal clustering (addresses created near same time)
- Low entropy flagging
- MT19937 PRNG fingerprinting
"""

import hashlib
from typing import Dict, List, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
import logging


class PatternDetector:
    """
    Detects patterns indicating weak key generation in Bitcoin addresses.
    
    Focuses on patterns associated with:
    - Mersenne Twister (MT19937) PRNG
    - Sequential key generation
    - Time-based clustering
    - Low entropy sources
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the pattern detector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.entropy_threshold = config['analysis']['entropy_threshold']
        
        self.logger = logging.getLogger(__name__)
        
        # Pattern tracking
        self.detected_patterns = []
        self.address_timeline = []
    
    def detect_sequential_addresses(self, addresses: List[Dict]) -> List[Dict]:
        """
        Detect addresses that may be sequentially generated.
        
        Sequential generation indicates a predictable PRNG or key derivation.
        
        Args:
            addresses: List of address dictionaries with metadata
            
        Returns:
            List of detected sequential pattern dictionaries
        """
        self.logger.info("Detecting sequential address patterns")
        
        patterns = []
        
        # Sort by collection time
        sorted_addresses = sorted(addresses, key=lambda x: x.get('collected_at', ''))
        
        # Look for sequential patterns in adjacent addresses
        for i in range(len(sorted_addresses) - 1):
            addr1 = sorted_addresses[i]
            addr2 = sorted_addresses[i + 1]
            
            # Compare address hashes for similarity
            hash1 = hashlib.sha256(addr1['address'].encode()).digest()
            hash2 = hashlib.sha256(addr2['address'].encode()).digest()
            
            # Calculate Hamming distance
            hamming = sum(bin(b1 ^ b2).count('1') for b1, b2 in zip(hash1, hash2))
            
            # Low Hamming distance indicates potential correlation
            if hamming < 64:  # Less than 25% bits different
                patterns.append({
                    'type': 'sequential',
                    'address1': addr1['address'],
                    'address2': addr2['address'],
                    'hamming_distance': hamming,
                    'confidence': 1 - (hamming / 256),
                    'block_distance': abs(addr1.get('block_height', 0) - addr2.get('block_height', 0))
                })
        
        self.logger.info(f"Found {len(patterns)} sequential patterns")
        return patterns
    
    def detect_temporal_clustering(self, addresses: List[Dict], window_minutes: int = 60) -> List[Dict]:
        """
        Detect temporal clustering of address creation.
        
        Multiple addresses created in a short time window may indicate
        batch generation from a weak PRNG.
        
        Args:
            addresses: List of address dictionaries with timestamps
            window_minutes: Time window for clustering detection
            
        Returns:
            List of detected cluster dictionaries
        """
        self.logger.info(f"Detecting temporal clusters (window: {window_minutes} minutes)")
        
        clusters = []
        
        # Group by block height (proxy for time)
        block_groups = defaultdict(list)
        for addr in addresses:
            block_height = addr.get('block_height', 0)
            block_groups[block_height].append(addr)
        
        # Detect clusters
        for block_height, addrs in block_groups.items():
            if len(addrs) >= 3:  # 3+ addresses in same block
                clusters.append({
                    'type': 'temporal_cluster',
                    'block_height': block_height,
                    'address_count': len(addrs),
                    'addresses': [a['address'] for a in addrs],
                    'confidence': min(len(addrs) / 10.0, 1.0)  # Normalize to 0-1
                })
        
        # Look for addresses in adjacent blocks
        sorted_blocks = sorted(block_groups.keys())
        for i in range(len(sorted_blocks) - 1):
            block1 = sorted_blocks[i]
            block2 = sorted_blocks[i + 1]
            
            if block2 - block1 <= 5:  # Within 5 blocks (~50 minutes)
                combined_addrs = block_groups[block1] + block_groups[block2]
                if len(combined_addrs) >= 5:
                    clusters.append({
                        'type': 'temporal_cluster_range',
                        'block_range': [block1, block2],
                        'address_count': len(combined_addrs),
                        'addresses': [a['address'] for a in combined_addrs],
                        'confidence': min(len(combined_addrs) / 15.0, 1.0)
                    })
        
        self.logger.info(f"Found {len(clusters)} temporal clusters")
        return clusters
    
    def detect_low_entropy_group(self, analysis_results: List[Dict]) -> List[Dict]:
        """
        Identify groups of addresses with consistently low entropy.
        
        Args:
            analysis_results: List of entropy analysis results
            
        Returns:
            List of low entropy group patterns
        """
        self.logger.info("Detecting low entropy groups")
        
        patterns = []
        
        # Filter weak addresses
        weak_addresses = [r for r in analysis_results 
                         if r.get('shannon_entropy', 8.0) < self.entropy_threshold]
        
        if len(weak_addresses) >= 3:
            patterns.append({
                'type': 'low_entropy_group',
                'count': len(weak_addresses),
                'addresses': [a['address'] for a in weak_addresses],
                'avg_entropy': sum(a['shannon_entropy'] for a in weak_addresses) / len(weak_addresses),
                'confidence': min(len(weak_addresses) / 5.0, 1.0)
            })
        
        self.logger.info(f"Found {len(patterns)} low entropy groups")
        return patterns
    
    def detect_mt19937_fingerprint(self, addresses: List[str]) -> List[Dict]:
        """
        Detect fingerprints of MT19937 PRNG in address generation.
        
        MT19937 has statistical properties that can be detected:
        - 32-bit boundaries in generated numbers
        - Specific periodicity
        - Correlation patterns
        
        Args:
            addresses: List of Bitcoin addresses
            
        Returns:
            List of MT19937 fingerprint patterns
        """
        self.logger.info("Detecting MT19937 PRNG fingerprints")
        
        patterns = []
        
        # Convert addresses to numerical values for analysis
        address_values = []
        for addr in addresses:
            # Hash address and convert to integer
            hash_bytes = hashlib.sha256(addr.encode()).digest()
            value = int.from_bytes(hash_bytes[:4], 'big')  # First 4 bytes as 32-bit int
            address_values.append(value)
        
        # Check for 32-bit boundaries (MT19937 generates 32-bit values)
        boundary_aligned = 0
        for value in address_values:
            if value % (2**16) < 1000:  # Near 32-bit boundaries
                boundary_aligned += 1
        
        if boundary_aligned > len(addresses) * 0.1:  # More than 10% aligned
            patterns.append({
                'type': 'mt19937_boundary',
                'aligned_count': boundary_aligned,
                'total_count': len(addresses),
                'confidence': boundary_aligned / len(addresses),
                'description': 'Addresses show 32-bit boundary alignment consistent with MT19937'
            })
        
        # Check for autocorrelation (sequential values correlation)
        if len(address_values) >= 10:
            correlations = []
            for i in range(len(address_values) - 1):
                # Simplified correlation check
                diff = abs(address_values[i+1] - address_values[i])
                if diff < 2**24:  # Relatively small difference for 32-bit space
                    correlations.append(diff)
            
            if len(correlations) > len(address_values) * 0.2:
                patterns.append({
                    'type': 'mt19937_correlation',
                    'correlation_count': len(correlations),
                    'confidence': len(correlations) / len(address_values),
                    'description': 'Sequential correlation consistent with PRNG state evolution'
                })
        
        self.logger.info(f"Found {len(patterns)} MT19937 fingerprints")
        return patterns
    
    def detect_all_patterns(self, addresses: List[Dict], entropy_results: List[Dict]) -> Dict:
        """
        Run all pattern detection algorithms.
        
        Args:
            addresses: List of address dictionaries with metadata
            entropy_results: List of entropy analysis results
            
        Returns:
            Dictionary containing all detected patterns by type
        """
        self.logger.info("Running comprehensive pattern detection")
        
        # Detect all pattern types
        sequential = self.detect_sequential_addresses(addresses)
        temporal = self.detect_temporal_clustering(addresses)
        low_entropy = self.detect_low_entropy_group(entropy_results)
        mt19937 = self.detect_mt19937_fingerprint([a['address'] for a in addresses])
        
        # Combine results
        all_patterns = {
            'sequential': sequential,
            'temporal_clusters': temporal,
            'low_entropy_groups': low_entropy,
            'mt19937_fingerprints': mt19937,
            'total_patterns': len(sequential) + len(temporal) + len(low_entropy) + len(mt19937)
        }
        
        self.logger.info(f"Pattern detection complete: {all_patterns['total_patterns']} patterns found")
        
        return all_patterns
    
    def identify_high_priority_targets(self, patterns: Dict, entropy_results: List[Dict]) -> List[Dict]:
        """
        Identify high-priority addresses for key recovery attempts.
        
        Prioritizes based on multiple weak indicators.
        
        Args:
            patterns: Dictionary of detected patterns
            entropy_results: List of entropy analysis results
            
        Returns:
            Sorted list of high-priority target addresses
        """
        self.logger.info("Identifying high-priority targets for key recovery")
        
        # Score each address
        address_scores = defaultdict(lambda: {'address': '', 'score': 0, 'indicators': []})
        
        # Score from entropy analysis
        for result in entropy_results:
            addr = result['address']
            score = 0
            indicators = []
            
            if result.get('weakness_level') == 'WEAK':
                score += 10
                indicators.append('weak_entropy')
            elif result.get('weakness_level') == 'SUSPICIOUS':
                score += 5
                indicators.append('suspicious_entropy')
            
            if result.get('patterns_detected', 0) > 0:
                score += result['patterns_detected'] * 2
                indicators.append(f"{result['patterns_detected']}_patterns")
            
            address_scores[addr]['address'] = addr
            address_scores[addr]['score'] += score
            address_scores[addr]['indicators'].extend(indicators)
        
        # Score from pattern detection
        for pattern_list in patterns.values():
            if isinstance(pattern_list, list):
                for pattern in pattern_list:
                    # Extract addresses from pattern
                    addrs = []
                    if 'address1' in pattern:
                        addrs.append(pattern['address1'])
                    if 'address2' in pattern:
                        addrs.append(pattern['address2'])
                    if 'addresses' in pattern:
                        addrs.extend(pattern['addresses'])
                    
                    # Add score to involved addresses
                    confidence_score = int(pattern.get('confidence', 0.5) * 10)
                    for addr in addrs:
                        address_scores[addr]['address'] = addr
                        address_scores[addr]['score'] += confidence_score
                        address_scores[addr]['indicators'].append(pattern['type'])
        
        # Convert to sorted list
        targets = sorted(address_scores.values(), key=lambda x: x['score'], reverse=True)
        
        # Filter to only high-scoring targets
        high_priority = [t for t in targets if t['score'] >= 10]
        
        self.logger.info(f"Identified {len(high_priority)} high-priority targets")
        
        return high_priority
    
    def generate_pattern_report(self, patterns: Dict) -> Dict:
        """
        Generate a comprehensive pattern detection report.
        
        Args:
            patterns: Dictionary of detected patterns
            
        Returns:
            Summary report dictionary
        """
        report = {
            'total_patterns': patterns.get('total_patterns', 0),
            'by_type': {
                'sequential': len(patterns.get('sequential', [])),
                'temporal_clusters': len(patterns.get('temporal_clusters', [])),
                'low_entropy_groups': len(patterns.get('low_entropy_groups', [])),
                'mt19937_fingerprints': len(patterns.get('mt19937_fingerprints', []))
            },
            'confidence_levels': self._calculate_confidence_distribution(patterns),
            'recommendations': self._generate_recommendations(patterns)
        }
        
        return report
    
    def _calculate_confidence_distribution(self, patterns: Dict) -> Dict:
        """Calculate distribution of confidence levels across patterns."""
        confidences = []
        
        for pattern_list in patterns.values():
            if isinstance(pattern_list, list):
                for pattern in pattern_list:
                    if 'confidence' in pattern:
                        confidences.append(pattern['confidence'])
        
        if not confidences:
            return {'high': 0, 'medium': 0, 'low': 0}
        
        return {
            'high': len([c for c in confidences if c >= 0.7]),
            'medium': len([c for c in confidences if 0.4 <= c < 0.7]),
            'low': len([c for c in confidences if c < 0.4])
        }
    
    def _generate_recommendations(self, patterns: Dict) -> List[str]:
        """Generate actionable recommendations based on patterns."""
        recommendations = []
        
        if len(patterns.get('mt19937_fingerprints', [])) > 0:
            recommendations.append("MT19937 fingerprints detected - prioritize PRNG reconstruction attack")
        
        if len(patterns.get('temporal_clusters', [])) > 0:
            recommendations.append("Temporal clustering found - investigate batch generation vulnerability")
        
        if len(patterns.get('sequential', [])) > 0:
            recommendations.append("Sequential patterns detected - analyze key derivation method")
        
        if len(patterns.get('low_entropy_groups', [])) > 0:
            recommendations.append("Low entropy group identified - focus on entropy source weakness")
        
        if not recommendations:
            recommendations.append("No significant patterns detected - addresses appear randomly generated")
        
        return recommendations
