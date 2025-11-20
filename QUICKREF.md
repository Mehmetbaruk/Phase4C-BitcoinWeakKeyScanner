# Quick Reference Guide

## One-Page Cheat Sheet for Bitcoin Weak Key Scanner

### Installation (5 minutes)
```bash
git clone <repo-url>
cd weak-key-scanner
chmod +x install.sh
./install.sh
source venv/bin/activate
```

### Basic Usage
```bash
# Test run (10 addresses, ~10 minutes)
cd src
python3 main.py --addresses 10

# Production scan (1000 addresses, ~15 hours)
./run_aws.sh 1000 test 8

# Monitor progress
./monitor.sh
```

### Configuration Quick Reference
Location: `config/config.yaml`

| Setting | Values | Default | Notes |
|---------|--------|---------|-------|
| `mode` | test / production | test | test=2²⁰ seeds, production=2³² seeds |
| `num_addresses` | 1-100000 | 10000 | More = longer scan |
| `parallel_workers` | 1-32 | 8 | Match your CPU cores |
| `entropy_threshold` | 0-8 | 7.0 | Lower = weaker detection |
| `checkpoint_interval` | 10-1000 | 100 | Save progress every N addresses |

### Command-Line Options
```bash
python3 main.py [OPTIONS]

--addresses N          Number of addresses to scan
--config PATH          Config file path
--clear-checkpoint     Start fresh (ignore saved progress)
--no-checkpoint        Disable checkpointing
```

### File Locations
```
weak-key-scanner/
├── config/config.yaml         # Edit settings here
├── logs/                      # Execution logs
│   └── aws_execution_*.log    # Tail this for progress
├── results/                   # Output reports
│   ├── weak_key_evidence_*.json   # Full results
│   └── scan_summary_*.txt         # Quick summary
├── checkpoint.json            # Resume state
└── src/main.py               # Entry point
```

### Common Tasks

#### Resume from checkpoint
```bash
# Just run again - automatically resumes
./run_aws.sh 10000 test 8
# Output: "Checkpoint loaded: 3,456 addresses already processed"
```

#### Change scan size mid-run
```bash
# Stop current scan
kill -TERM <pid>

# Edit config
nano config/config.yaml
# Change: num_addresses: 5000

# Restart - keeps what's already scanned
./run_aws.sh 5000 test 8
```

#### Check progress
```bash
# Real-time monitoring
./monitor.sh

# Or tail log
tail -f logs/aws_execution_*.log

# Check checkpoint
cat checkpoint.json | grep addresses_processed
```

#### Clean up and start fresh
```bash
# Remove old data
rm checkpoint.json
rm logs/*.log
rm results/*

# Start new scan
./run_aws.sh 10000 test 8
```

### Performance Expectations

#### Test Mode (2²⁰ = 1M seeds)
| Addresses | 8-core Time |
|-----------|-------------|
| 10        | 10 min      |
| 100       | 1.5 hours   |
| 1,000     | 15 hours    |
| 10,000    | 150 hours   |

#### Production Mode (2³² = 4.3B seeds)
| Addresses | 8-core Time |
|-----------|-------------|
| 1         | 1-4 hours   |
| 10        | 10-40 hours |
| 100       | Days        |

### AWS Quick Commands

#### Launch spot instance
```bash
# Via console: EC2 → Launch → c5.2xlarge → Spot
# Via CLI:
aws ec2 request-spot-instances \
    --instance-count 1 \
    --type "one-time" \
    --launch-specification file://spot-spec.json
```

#### Connect to instance
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<instance-ip>
```

#### Monitor from local machine
```bash
# Stream logs
ssh -i ~/.ssh/your-key.pem ubuntu@<ip> \
    "tail -f weak-key-scanner/logs/*.log"

# Copy results
scp -i ~/.ssh/your-key.pem \
    ubuntu@<ip>:weak-key-scanner/results/*.json ./
```

#### Stop/start instance
```bash
# Stop (preserves data)
aws ec2 stop-instances --instance-ids i-xxxxxxxx

# Start
aws ec2 start-instances --instance-ids i-xxxxxxxx
```

### Troubleshooting

#### Scanner not starting
```bash
# Check Python
python3 --version  # Should be 3.8+

# Check dependencies
pip3 list | grep bitcoinlib

# Reinstall if needed
pip3 install -r requirements.txt
```

#### API rate limiting
```yaml
# In config.yaml, increase delay:
api:
  rate_limit: 20  # Reduce from 30 to 20 requests/min
  retry_delay: 5  # Increase from 2 to 5 seconds
```

#### Out of memory
```yaml
# In config.yaml, reduce batch size:
scanning:
  batch_size: 500  # Reduce from 1000 to 500
```

#### No weak keys found
This is normal! Modern wallets use proper entropy.
```bash
# Create synthetic test key
python3 << EOF
from prng_reconstructor import PRNGReconstructor
config = {...}
prng = PRNGReconstructor(config)
addr, key = prng.create_weak_key_for_testing(12345)
print(f"Test address: {addr}")
EOF
```

### Test Suite

#### Run all tests
```bash
pytest tests/ -v
```

#### Run specific test
```bash
pytest tests/test_entropy_analyzer.py -v
```

#### Check coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Output Interpretation

#### JSON Evidence Report
```json
{
  "summary": {
    "total_addresses_analyzed": 1000,
    "weak_addresses_found": 5,
    "patterns_detected": 3,
    "keys_recovered": 1
  }
}
```

#### Text Summary
```
Addresses Analyzed:     1,000
Weak Addresses Found:   5
Patterns Detected:      3
Keys Recovered:         1
```

### Safety Checks

#### Verify testnet-only
```bash
# Check config
grep testnet_only config/config.yaml
# Should show: testnet_only: true

# Check network
grep bitcoin_network config/config.yaml
# Should show: bitcoin_network: "testnet"
```

#### Verify API endpoint
```bash
grep base_url config/config.yaml
# Should contain "testnet"
```

### Cost Calculator

#### AWS c5.2xlarge Spot (~$0.10/hour)
| Duration | Cost |
|----------|------|
| 1 hour   | $0.10 |
| 10 hours | $1.00 |
| 100 hours| $10.00 |
| 1 day    | $2.40 |
| 1 week   | $16.80 |

Add ~$0.02/day for 30 GB EBS storage

### Important Paths

| File | Purpose |
|------|---------|
| `src/main.py` | Entry point - start here |
| `config/config.yaml` | All settings - edit this |
| `checkpoint.json` | Resume state - don't delete during scan |
| `logs/*.log` | Progress info - tail for monitoring |
| `results/*.json` | Final output - this is what you want |

### Environment Variables (Optional)

```bash
# Set custom config
export WEAK_KEY_CONFIG=/path/to/custom/config.yaml

# Set log level
export WEAK_KEY_LOG_LEVEL=DEBUG

# Use in main.py
python3 main.py --config $WEAK_KEY_CONFIG
```

### Signal Handling

| Signal | Action |
|--------|--------|
| SIGINT (Ctrl+C) | Save checkpoint, exit gracefully |
| SIGTERM (AWS) | Save checkpoint, exit gracefully |
| SIGHUP | Continue running (ignore) |

### Screen/Tmux Usage

#### Using screen
```bash
# Start session
screen -S scanner

# Run scanner
./run_aws.sh 10000 test 8

# Detach: Ctrl+A, then D
# Reattach: screen -r scanner
# List: screen -ls
```

#### Using tmux
```bash
# Start session
tmux new -s scanner

# Run scanner
./run_aws.sh 10000 test 8

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t scanner
# List: tmux ls
```

### Quick Diagnostics

```bash
# Is scanner running?
ps aux | grep python | grep main.py

# How many addresses processed?
cat checkpoint.json | python3 -m json.tool | grep addresses_processed

# Recent errors?
tail -n 100 logs/*.log | grep ERROR

# Disk space?
df -h | grep /

# Memory usage?
free -h

# CPU usage?
top -b -n 1 | grep python
```

### Getting Help

1. **README.md** - Complete documentation
2. **AWS_DEPLOYMENT.md** - AWS-specific guide
3. **PROJECT_SUMMARY.md** - Technical overview
4. **Inline code comments** - Detailed explanations
5. **Test files** - Usage examples

### One-Liner Examples

```bash
# Quick 10-address test
cd src && python3 main.py --addresses 10

# Full scan with custom config
python3 main.py --config ~/my-config.yaml --addresses 5000

# Resume from checkpoint
python3 main.py --addresses 10000

# Fresh start
python3 main.py --addresses 1000 --clear-checkpoint

# Debug mode
python3 main.py --addresses 100 2>&1 | tee debug.log
```

---

**Pro Tip**: Bookmark this file for quick reference during scans!
