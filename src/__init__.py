"""
Bitcoin Weak Key Scanner
========================

Production-ready implementation for detecting and exploiting weak PRNG vulnerabilities
in Bitcoin key generation. Reproduces the "Milk Sad" vulnerability ($900M+ impact).

AWS-Optimized Features:
- Checkpoint/resume capability for long-running scans
- Memory-efficient streaming architecture
- Comprehensive logging for CloudWatch
- Graceful shutdown handling
- Parallel processing support

Author: Security Research Team
Date: November 2025
License: Educational/Research Only
"""

__version__ = "1.0.0"
__all__ = [
    "AddressCollector",
    "EntropyAnalyzer",
    "PatternDetector",
    "PRNGReconstructor",
    "KeyRecovery",
    "Validator",
    "Logger",
]
