# Bitcoin Weak Key Scanner

**Production-grade implementation for detecting and exploiting weak PRNG vulnerabilities in Bitcoin key generation**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Educational-green.svg)](LICENSE)
[![Network](https://img.shields.io/badge/network-TESTNET%20ONLY-red.svg)](https://testnet.help/)

## Overview

This tool reproduces the **"Milk Sad" vulnerability** that led to $900M+ in compromised Bitcoin addresses. It implements a complete pipeline for:

1. **Address Collection** - Gathering addresses from Bitcoin testnet blockchain
2. **Entropy Analysis** - Statistical detection of weak randomness
3. **Pattern Detection** - Identifying PRNG fingerprints (MT19937, sequential generation)
4. **Key Recovery** - Brute-force PRNG seed reconstruction
5. **Validation** - Cryptographic verification of recovered keys

**⚠️ TESTNET ONLY**: This implementation enforces testnet-only operation at multiple layers for safety.

---

## Architecture

```
weak-key-scanner/
├── src/
│   ├── address_collector.py      # Blockchain API integration
│   ├── entropy_analyzer.py       # Shannon entropy & chi-square tests
│   ├── pattern_detector.py       # Weakness pattern identification
│   ├── prng_reconstructor.py     # MT19937 seed search (parallel)
│   ├── key_recovery.py           # Recovery orchestration
│   ├── validator.py              # Key/address validation
│   ├── logger.py                 # Evidence generation
│   └── main.py                   # Pipeline orchestrator
├── tests/
│   ├── test_entropy_analyzer.py
│   ├── test_prng_reconstructor.py
│   ├── test_key_recovery.py
│   └── test_integration.py
├── config/
│   └── config.yaml               # Configuration (thresholds, modes)
├── logs/                         # Execution logs
├── results/                      # JSON evidence reports
├── requirements.txt
├── install.sh                    # Automated installation
└── run_aws.sh                    # AWS execution script
```

---

## Key Features

### AWS-Optimized Production Deployment

- **Checkpoint/Resume**: Automatic state saving every 100 addresses
- **Graceful Shutdown**: SIGTERM/SIGINT handlers for AWS Spot interruption
- **Memory Efficient**: Streaming architecture for 10,000+ addresses
- **Parallel Processing**: Multi-core PRNG search (configurable workers)
- **CloudWatch Logging**: Structured JSON logs for AWS monitoring

### Statistical Analysis

- **Shannon Entropy**: `H = -Σ p(x) log₂ p(x)` calculation
- **Chi-Square Test**: Uniform distribution validation
- **Pattern Detection**: MT19937 fingerprinting, temporal clustering
- **Weakness Thresholds**: <7.0 bits/byte = WEAK, <7.5 = SUSPICIOUS

### PRNG Reconstruction

- **MT19937 Implementation**: Python's `random.Random()` for seed search
- **Two Modes**:
  - **TEST MODE**: 2²⁰ (1M seeds) - ~1 minute per address
  - **PRODUCTION MODE**: 2³² (4.3B seeds) - ~1-4 hours per address
- **Parallel Search**: Distributes seed space across CPU cores

### Safety Enforcement

- Multiple testnet validation layers
- Configuration validation at startup
- Address prefix checking (`tb1`, `m`, `n`, `2`)
- API endpoint verification
- No mainnet code paths possible

---

## Installation

### Prerequisites

- **Python 3.8+**
- **Ubuntu/Debian Linux** (recommended for AWS EC2)
- **4-8 GB RAM** (depending on address count)
- **Multi-core CPU** (for parallel seed search)

### Quick Install

```bash
# Clone repository
cd weak-key-scanner

# Run automated installer
chmod +x install.sh
./install.sh

# Activate virtual environment
source venv/bin/activate
```

### Manual Installation

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y build-essential libssl-dev python3-dev

# Install Python packages
pip3 install -r requirements.txt

# Create directories
mkdir -p logs results data/test_vectors
```

---

## Configuration

Edit `config/config.yaml`:

```yaml
# Network Configuration
bitcoin_network: "testnet"  # MUST be testnet

# Scanning Parameters
scanning:
  num_addresses: 10000
  checkpoint_interval: 100
  resume_from_checkpoint: true

# Analysis Thresholds
analysis:
  entropy_threshold: 7.0        # Lower = weaker
  suspicious_threshold: 7.5
  chi_square_p_threshold: 0.01

# PRNG Attack Configuration
prng_attack:
  mode: "test"                  # "test" or "production"
  seed_space_test_mode: 1048576      # 2^20 (~1 min/address)
  seed_space_full_mode: 4294967296   # 2^32 (~1-4 hrs/address)
  parallel_workers: 8

# Safety
safety:
  testnet_only: true
  allowed_prefixes: ["m", "n", "2", "tb1"]
```

---

## Usage

### Basic Execution

```bash
cd src
python3 main.py --addresses 1000
```

### AWS Long-Running Execution

```bash
# Run in background with automatic recovery
./run_aws.sh 10000 test 8
#            ↑      ↑    ↑
#            |      |    └─ Parallel workers
#            |      └────── Mode (test/production)
#            └─────────── Number of addresses

# Monitor progress
./monitor.sh

# Check logs
tail -f logs/aws_execution_*.log
```

### Resume from Checkpoint

```bash
# Automatically resumes if checkpoint exists
python3 main.py --addresses 5000

# Force fresh start (clear checkpoint)
python3 main.py --addresses 5000 --clear-checkpoint
```

### Command-Line Options

```bash
python3 main.py [OPTIONS]

Options:
  --config PATH           Configuration file (default: ../config/config.yaml)
  --addresses N           Number of addresses to scan (overrides config)
  --no-checkpoint         Disable checkpoint resume
  --clear-checkpoint      Clear existing checkpoint before starting
```

---

## Expected Results

### Modern Bitcoin Testnet (2024-2025)

**Realistic Expectations**:
- **Weak addresses found**: 0-2 (modern wallets use proper entropy)
- **Keys recovered**: 0-1 (very rare)
- **Purpose**: Demonstrates methodology, validates tool correctness

### Historical Testnet (2013-2016)

**Higher probability** of finding weak keys from:
- Early mobile wallets
- Development/testing tools
- Academic experiments

### Synthetic Validation

Create known weak keys for testing:

```bash
# Generate test weak key with known seed
python3 << EOF
from prng_reconstructor import PRNGReconstructor

config = {...}  # Load config
prng = PRNGReconstructor(config)

seed = 12345
address, privkey = prng.create_weak_key_for_testing(seed)
print(f"Test Address: {address}")
print(f"Seed: {seed}")
EOF
```

---

## Performance Benchmarks

### Test Mode (2²⁰ seed space)

| Addresses | Time      | CPU Cores |
|-----------|-----------|-----------|
| 10        | ~10 min   | 8         |
| 100       | ~1.5 hrs  | 8         |
| 1,000     | ~15 hrs   | 8         |

### Production Mode (2³² seed space)

| Addresses | Time      | CPU Cores |
|-----------|-----------|-----------|
| 1         | 1-4 hrs   | 8         |
| 10        | 10-40 hrs | 8         |
| 100       | Days      | 8         |

**AWS Instance Recommendations**:
- **c5.2xlarge**: 8 vCPU, good cost/performance
- **c5.4xlarge**: 16 vCPU, faster but higher cost
- **Spot Instances**: Use with checkpoint/resume

---

## Output Reports

### JSON Evidence Report

```json
{
  "metadata": {
    "report_type": "weak_key_scan_evidence",
    "generated_at": "2025-11-03T10:30:00",
    "network": "testnet"
  },
  "summary": {
    "total_addresses_analyzed": 10000,
    "weak_addresses_found": 15,
    "patterns_detected": 8,
    "keys_recovered": 3
  },
  "entropy_analysis": [...],
  "pattern_detection": {...},
  "recovered_keys": [...]
}
```

Location: `results/weak_key_evidence_YYYYMMDD_HHMMSS.json`

### Human-Readable Summary

```
======================================================================
BITCOIN WEAK KEY SCANNER - SUMMARY REPORT
======================================================================
Generated: 2025-11-03 10:30:00
Network: TESTNET

SCAN STATISTICS
----------------------------------------------------------------------
Addresses Analyzed:     10,000
Weak Addresses Found:   15
Patterns Detected:      8
Keys Recovered:         3
```

Location: `results/scan_summary_YYYYMMDD_HHMMSS.txt`

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suite

```bash
pytest tests/test_entropy_analyzer.py -v
pytest tests/test_prng_reconstructor.py -v
pytest tests/test_integration.py -v
```

### Test Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

---

## AWS Deployment Guide

### 1. Launch EC2 Instance

```bash
# Recommended: c5.2xlarge (8 vCPU, 16 GB RAM)
# AMI: Ubuntu 22.04 LTS
# Storage: 30 GB EBS
# Security Group: Outbound HTTPS (API calls)
```

### 2. Initial Setup

```bash
# Connect to instance
ssh -i your-key.pem ubuntu@<instance-ip>

# Clone repository
git clone <repository-url>
cd weak-key-scanner

# Install
./install.sh
```

### 3. Start Scan

```bash
# Background execution
./run_aws.sh 10000 test 8

# Disconnect safely (screen or tmux)
screen -S scanner
./run_aws.sh 10000 test 8
# Ctrl+A, D to detach
```

### 4. Monitor from Local Machine

```bash
# SSH with log forwarding
ssh -i your-key.pem ubuntu@<instance-ip> "tail -f weak-key-scanner/logs/*.log"

# Or copy results periodically
scp -i your-key.pem ubuntu@<instance-ip>:weak-key-scanner/results/*.json ./
```

### 5. Spot Instance Handling

The tool automatically handles AWS Spot interruptions:

1. **Signal Handler**: Catches SIGTERM from AWS
2. **Checkpoint Save**: Writes current state
3. **Graceful Exit**: Cleans up resources
4. **Auto-Resume**: Restart script loads checkpoint

---

## Technical Details

### Entropy Calculation

```python
# Shannon Entropy
H = -Σ p(x) log₂ p(x)

# Where:
# p(x) = probability of byte x
# Range: 0-8 bits per byte
# Interpretation:
#   < 7.0: WEAK (predictable)
#   7.0-7.5: SUSPICIOUS
#   7.5-8.0: GOOD
#   = 8.0: Perfect randomness
```

### PRNG Reconstruction

```python
# MT19937 Seed Search
for seed in range(0, 2^32):
    prng = random.Random(seed)
    candidate_key = generate_key(prng)
    candidate_address = derive_address(candidate_key)
    
    if candidate_address == target_address:
        return seed, candidate_key
```

**Parallel Optimization**:
- Divides seed space across N workers
- Each worker searches independent chunk
- Early termination on first match
- Typical speedup: 6-7x on 8 cores

---

## Troubleshooting

### Common Issues

#### 1. API Rate Limiting

```
ERROR: API request failed: 429 Too Many Requests
```

**Solution**: Increase `rate_limit` in config (currently 30 req/min)

#### 2. Memory Issues

```
MemoryError: Unable to allocate array
```

**Solution**: 
- Reduce `batch_size` in config
- Use streaming collection (already default)
- Increase EC2 instance memory

#### 3. Checkpoint Corruption

```
ERROR: Failed to load checkpoint
```

**Solution**:
```bash
python3 main.py --clear-checkpoint
```

#### 4. No Weak Keys Found

**This is normal for modern testnet**. Try:
- Increase address count
- Use synthetic test keys
- Target historical blocks

---

## Security Considerations

### Testnet-Only Enforcement

1. **Config Validation**: Startup checks for `testnet_only: true`
2. **Address Validation**: Rejects non-testnet prefixes
3. **API Validation**: Verifies testnet API endpoints
4. **No Mainnet Paths**: Code structure prevents mainnet use

### Private Key Handling

- **Recovered keys masked** in JSON reports (first 8 + last 8 chars)
- **Full keys available** in checkpoint file (secure appropriately)
- **Export function** includes security warnings
- **Recommendation**: Encrypt sensitive outputs

---

## Research & Educational Use

### Academic Applications

- Cryptographic weakness analysis
- PRNG vulnerability research
- Blockchain security education
- Historical vulnerability reproduction

### Ethical Guidelines

✅ **Acceptable**:
- Testnet analysis
- Academic research
- Security tool development
- Historical reproduction

❌ **Prohibited**:
- Mainnet scanning
- Theft attempts
- Unauthorized access
- Commercial exploitation

---

## Performance Tuning

### For Faster Execution

1. **Increase workers**: `parallel_workers: 16` (if CPU available)
2. **Use test mode**: `mode: "test"` for quick validation
3. **Reduce addresses**: Start with 100-1000 for testing
4. **AWS instance**: c5.4xlarge or higher

### For Memory Efficiency

1. **Reduce batch_size**: `batch_size: 500`
2. **Enable checkpointing**: `checkpoint_interval: 50`
3. **Streaming collection**: (already default)

---

## Project Statistics

- **Lines of Code**: ~3,500
- **Test Coverage**: 28 tests
- **Configuration Options**: 25+
- **Output Formats**: 3 (JSON, TXT, logs)
- **Safety Layers**: 5
- **Supported Algorithms**: Shannon entropy, Chi-square, MT19937

---

## AWS Cost Estimation

### c5.2xlarge (8 vCPU, 16 GB)

| Mode       | Addresses | Hours | On-Demand | Spot     |
|------------|-----------|-------|-----------|----------|
| Test       | 1,000     | ~15   | ~$2.50    | ~$0.75   |
| Test       | 10,000    | ~150  | ~$25      | ~$7.50   |
| Production | 10        | ~30   | ~$5       | ~$1.50   |

**Recommendation**: Use Spot Instances with checkpoint/resume for 70% cost savings.

---

## Contributing

### Development Setup

```bash
# Install dev dependencies
pip3 install -r requirements-dev.txt

# Run linter
pylint src/

# Format code
black src/

# Type checking
mypy src/
```

---

## License

**Educational and Research Use Only**

This tool is provided for educational purposes and security research. Users are responsible for compliance with applicable laws and regulations.

---

## References

- **Milk Sad Vulnerability**: [Research Paper](https://milksad.info/)
- **MT19937**: Mersenne Twister algorithm (Python `random` module)
- **Bitcoin Testnet**: https://testnet.help/
- **Mempool.space API**: https://mempool.space/docs/api

---

## Support & Contact

For questions, issues, or contributions:

- **Issues**: GitHub Issues
- **Documentation**: This README + inline code comments
- **Research**: See Phase 3C technical architecture document

---

## Acknowledgments

- Bitcoin Core developers
- Mempool.space API
- Python bitcoinlib maintainers
- Security research community

---

**⚠️ WARNING**: This tool demonstrates serious cryptographic vulnerabilities. Always use proper entropy sources for real cryptocurrency applications. Never use predictable PRNGs for key generation.
