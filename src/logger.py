"""
Logger Module
=============

Evidence generation and comprehensive logging for the weak key scanner.
Produces JSON reports suitable for AWS CloudWatch and audit trails.

Output Formats:
- JSON evidence reports
- Structured AWS CloudWatch logs
- Human-readable summaries
- Security audit trails
"""

import json
import logging
import os
from typing import Dict, List, Any
from datetime import datetime
import sys


class ScanLogger:
    """
    Comprehensive logging and evidence generation system.
    
    Produces structured logs optimized for AWS CloudWatch monitoring
    and generates detailed JSON reports for audit and analysis.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the scan logger.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.log_dir = config['output']['log_dir']
        self.results_dir = config['output']['results_dir']
        self.log_level = config['output']['log_level']
        self.json_logging = config['output']['json_logging']
        
        # Create output directories
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("ScanLogger initialized")
        
        # Evidence accumulation
        self.scan_start_time = datetime.now()
        self.events = []
    
    def _setup_logging(self):
        """Configure Python logging system."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Convert log level string to logging constant
        numeric_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(os.path.join(self.log_dir, 'scan.log'))
            ]
        )
        
        # Reduce noise from libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    def log_event(self, event_type: str, data: Dict):
        """
        Log a structured event.
        
        Args:
            event_type: Type of event (e.g., 'scan_start', 'address_analyzed')
            data: Event data dictionary
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        
        self.events.append(event)
        
        # Also log to standard logger
        if self.json_logging:
            self.logger.info(json.dumps(event))
        else:
            self.logger.info(f"{event_type}: {json.dumps(data)}")
    
    def log_scan_start(self, target_count: int, config_summary: Dict):
        """
        Log scan initialization.
        
        Args:
            target_count: Number of addresses to scan
            config_summary: Configuration summary
        """
        self.log_event('scan_start', {
            'target_address_count': target_count,
            'config': config_summary,
            'network': self.config['bitcoin_network']
        })
    
    def log_address_collected(self, address: str, metadata: Dict):
        """
        Log address collection.
        
        Args:
            address: Bitcoin address
            metadata: Address metadata
        """
        self.log_event('address_collected', {
            'address': address,
            **metadata
        })
    
    def log_entropy_analysis(self, result: Dict):
        """
        Log entropy analysis result.
        
        Args:
            result: Entropy analysis result dictionary
        """
        self.log_event('entropy_analyzed', {
            'address': result['address'],
            'entropy': result.get('shannon_entropy'),
            'weakness_level': result.get('weakness_level'),
            'is_weak': result.get('is_weak')
        })
    
    def log_pattern_detection(self, patterns: Dict):
        """
        Log pattern detection results.
        
        Args:
            patterns: Pattern detection results
        """
        self.log_event('patterns_detected', {
            'total_patterns': patterns.get('total_patterns', 0),
            'by_type': patterns.get('by_type', {})
        })
    
    def log_key_recovery_attempt(self, address: str, success: bool, details: Dict):
        """
        Log key recovery attempt.
        
        Args:
            address: Target address
            success: Whether recovery succeeded
            details: Recovery details
        """
        self.log_event('key_recovery_attempt', {
            'address': address,
            'success': success,
            **details
        })
    
    def log_checkpoint_saved(self, checkpoint_data: Dict):
        """
        Log checkpoint save.
        
        Args:
            checkpoint_data: Checkpoint information
        """
        self.log_event('checkpoint_saved', {
            'addresses_processed': checkpoint_data.get('addresses_processed', 0),
            'weak_found': checkpoint_data.get('weak_found', 0)
        })
    
    def generate_evidence_report(self, 
                                 addresses_analyzed: List[Dict],
                                 entropy_results: List[Dict],
                                 patterns: Dict,
                                 recovered_keys: List[Dict],
                                 stats: Dict) -> str:
        """
        Generate comprehensive evidence report in JSON format.
        
        Args:
            addresses_analyzed: List of analyzed addresses
            entropy_results: Entropy analysis results
            patterns: Pattern detection results
            recovered_keys: Successfully recovered keys
            stats: Overall statistics
            
        Returns:
            Path to generated report file
        """
        self.logger.info("Generating evidence report")
        
        report = {
            'metadata': {
                'report_type': 'weak_key_scan_evidence',
                'generated_at': datetime.now().isoformat(),
                'scan_start': self.scan_start_time.isoformat(),
                'scan_duration_seconds': (datetime.now() - self.scan_start_time).total_seconds(),
                'network': self.config['bitcoin_network'],
                'testnet_only': self.config['safety']['testnet_only']
            },
            'summary': {
                'total_addresses_analyzed': len(addresses_analyzed),
                'weak_addresses_found': len([r for r in entropy_results if r.get('is_weak', False)]),
                'patterns_detected': patterns.get('total_patterns', 0),
                'keys_recovered': len(recovered_keys),
                **stats
            },
            'addresses_analyzed': addresses_analyzed,
            'entropy_analysis': entropy_results,
            'pattern_detection': patterns,
            'recovered_keys': self._sanitize_keys_for_report(recovered_keys),
            'configuration': {
                'entropy_threshold': self.config['analysis']['entropy_threshold'],
                'seed_space': self.config['prng_attack']['seed_space_test_mode'] if self.config['prng_attack']['mode'] == 'test' else self.config['prng_attack']['seed_space_full_mode'],
                'parallel_workers': self.config['prng_attack']['parallel_workers']
            },
            'events': self.events
        }
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'weak_key_evidence_{timestamp}.json'
        filepath = os.path.join(self.results_dir, filename)
        
        # Write report
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Evidence report generated: {filepath}")
        
        return filepath
    
    def _sanitize_keys_for_report(self, recovered_keys: List[Dict]) -> List[Dict]:
        """
        Sanitize recovered keys for report (mask private keys).
        
        Args:
            recovered_keys: List of recovery results with private keys
            
        Returns:
            Sanitized list with masked private keys
        """
        sanitized = []
        
        for key in recovered_keys:
            sanitized_key = key.copy()
            
            # Mask private key (show first 8 and last 8 characters)
            if 'private_key' in sanitized_key:
                pk = sanitized_key['private_key']
                if len(pk) > 16:
                    sanitized_key['private_key'] = f"{pk[:8]}...{pk[-8:]}"
                sanitized_key['private_key_length'] = len(pk)
            
            sanitized.append(sanitized_key)
        
        return sanitized
    
    def generate_summary_report(self, 
                                addresses_analyzed: int,
                                weak_found: int,
                                patterns: Dict,
                                recovered_keys: int,
                                stats: Dict) -> str:
        """
        Generate human-readable summary report.
        
        Args:
            addresses_analyzed: Number of addresses analyzed
            weak_found: Number of weak addresses found
            patterns: Pattern detection results
            recovered_keys: Number of recovered keys
            stats: Overall statistics
            
        Returns:
            Path to generated summary file
        """
        summary_lines = [
            "=" * 70,
            "BITCOIN WEAK KEY SCANNER - SUMMARY REPORT",
            "=" * 70,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Network: {self.config['bitcoin_network'].upper()}",
            "",
            "SCAN STATISTICS",
            "-" * 70,
            f"Addresses Analyzed:     {addresses_analyzed:,}",
            f"Weak Addresses Found:   {weak_found:,}",
            f"Patterns Detected:      {patterns.get('total_patterns', 0):,}",
            f"Keys Recovered:         {recovered_keys:,}",
            "",
            "PATTERN BREAKDOWN",
            "-" * 70
        ]
        
        # Add pattern details
        if 'by_type' in patterns:
            for pattern_type, count in patterns['by_type'].items():
                summary_lines.append(f"  {pattern_type:25s}: {count}")
        
        summary_lines.extend([
            "",
            "PERFORMANCE METRICS",
            "-" * 70,
            f"Scan Duration:          {stats.get('scan_duration_seconds', 0):.2f} seconds",
            f"API Calls Made:         {stats.get('api_calls', 0):,}",
            "",
            "=" * 70
        ])
        
        summary_text = "\n".join(summary_lines)
        
        # Write summary
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'scan_summary_{timestamp}.txt'
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(summary_text)
        
        self.logger.info(f"Summary report generated: {filepath}")
        
        # Also print to console
        print("\n" + summary_text + "\n")
        
        return filepath
    
    def log_error(self, error_type: str, error_message: str, context: Dict = None):
        """
        Log an error with context.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Optional context dictionary
        """
        self.log_event('error', {
            'error_type': error_type,
            'message': error_message,
            'context': context or {}
        })
        
        self.logger.error(f"{error_type}: {error_message}")
    
    def log_warning(self, warning_type: str, warning_message: str):
        """
        Log a warning.
        
        Args:
            warning_type: Type of warning
            warning_message: Warning message
        """
        self.log_event('warning', {
            'warning_type': warning_type,
            'message': warning_message
        })
        
        self.logger.warning(f"{warning_type}: {warning_message}")
    
    def get_log_summary(self) -> Dict:
        """
        Get summary of logged events.
        
        Returns:
            Summary dictionary
        """
        event_types = {}
        for event in self.events:
            event_type = event['event_type']
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        return {
            'total_events': len(self.events),
            'event_types': event_types,
            'scan_duration': (datetime.now() - self.scan_start_time).total_seconds()
        }
