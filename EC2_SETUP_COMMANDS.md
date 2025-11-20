# Complete EC2 Setup and Installation Commands

## Copy these commands ONE BY ONE to your EC2 instance after SSH connection

---

## PART 1: Initial Setup (Run these first)

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install required system packages
sudo apt-get install -y python3 python3-pip python3-venv git curl

# Verify Python version (should be 3.10+)
python3 --version
```

**Expected output**: `Python 3.10.X` or higher

---

## PART 2: Create Project Directory

```bash
# Create project directory
mkdir -p ~/bitcoin-weak-key-scanner
cd ~/bitcoin-weak-key-scanner

# Verify location
pwd
```

**Expected output**: `[REDACTED_PRIVATE_KEY]`

---

## PART 3: Download Project Files

Since you have all files on your local machine, we'll upload them from Windows to EC2.

### Option A: Using SCP from Windows PowerShell

Open **NEW** PowerShell window (keep SSH connection open in another window):

```powershell
# Navigate to your project folder
cd "d:\OzelProje2\Round 3\Coding\Phase4C"

# Upload all files to EC2 (replace <INSTANCE-IP> with your actual IP)
scp -i "$env:USERPROFILE\.ssh\weak-key-scanner.pem" -r * ubuntu@<INSTANCE-IP>:~/bitcoin-weak-key-scanner/
```

**Example**:
```powershell
scp -i "$env:USERPROFILE\.ssh\weak-key-scanner.pem" -r * ubuntu@54.123.45.67:~/bitcoin-weak-key-scanner/
```

This uploads all files (src/, tests/, config/, scripts, docs, etc.)

### Option B: Clone from GitHub (if you have a repo)

```bash
# If you pushed to GitHub
git clone https://github.com/your-username/bitcoin-weak-key-scanner.git
cd bitcoin-weak-key-scanner
```

### Option C: Manual File Creation (if above don't work)

I can provide commands to create each file directly on EC2 if needed.

---

## PART 4: Run Installation Script

**Back in your SSH connection window**:

```bash
# Make installation script executable
chmod +x install.sh

# Run installer
./install.sh
```

**What this does**:
- Creates Python virtual environment
- Installs all dependencies from requirements.txt
- Creates necessary directories (logs/, data/, results/)
- Verifies installation

**Expected output** (at the end):
```
========================================
Installation Complete!
========================================
```

---

## PART 5: Verify Installation

```bash
# Activate virtual environment
source venv/bin/activate

# Your prompt should change to:
# (venv) ubuntu@ip-172-31-XX-XX:~$

# Test imports
python3 -c "import bitcoinlib; print('✓ bitcoinlib OK')"
python3 -c "import ecdsa; print('✓ ecdsa OK')"
python3 -c "import requests; print('✓ requests OK')"
python3 -c "import yaml; print('✓ yaml OK')"
python3 -c "import numpy; print('✓ numpy OK')"
python3 -c "import scipy; print('✓ scipy OK')"

# Test main module
python3 -c "from src.main import WeakKeyScanner; print('✓ Scanner module OK')"
```

**Expected**: All print `✓ ... OK`

---

## PART 6: Configure for Your Instance

Your instance has **2 vCPU**, so let's optimize the configuration:

```bash
# Edit config file
nano config/config.yaml
```

**Find and change these lines**:

```yaml
# Line ~15: Reduce parallel workers for 2 vCPU
parallel:
  num_workers: 2  # Change from 8 to 2

# Line ~45: Use test mode for faster scanning
prng_attack:
  mode: 'test'  # Keep as 'test' (searches 2^20 seeds, not 2^32)
  max_seed_search_space: 1048576  # 2^20 for testing
```

**Save**: Press `Ctrl+X`, then `Y`, then `Enter`

---

## PART 7: Run First Test (100 Addresses)

```bash
# Make run script executable
chmod +x run_aws.sh

# Start test scan (100 addresses, test mode, 2 workers)
./run_aws.sh 100 test 2
```

**Expected output**:
```
Starting Bitcoin Weak Key Scanner on AWS...
Configuration:
  Addresses to scan: 100
  PRNG mode: test
  Workers: 2
  Log file: logs/aws_execution_20251103_120345.log

Scanner started with PID: 12345
Monitor with: tail -f logs/aws_execution_20251103_120345.log
```

---

## PART 8: Monitor Progress

**Option 1**: Use monitor script (opens in watch mode)
```bash
./monitor.sh
```

**Option 2**: Tail the log file
```bash
# Use the log filename from previous step
tail -f logs/aws_execution_*.log
```

**Option 3**: Check checkpoint file
```bash
# Every ~30 seconds
watch -n 30 cat checkpoint.json
```

**What you'll see**:
```json
{
  "last_processed_address": "tb1q...",
  "addresses_processed": 45,
  "weak_addresses_found": 2,
  "patterns_detected": 1,
  "last_checkpoint_time": "2025-11-03T12:15:30Z"
}
```

---

## PART 9: View Results (After Completion)

```bash
# Check if scanner is still running
ps aux | grep python

# When completed, view results
ls -lh results/

# View evidence report
cat results/evidence_report_*.json | python3 -m json.tool

# View summary
cat results/summary_report_*.txt

# View logs
tail -n 100 logs/weak_key_scanner_*.log
```

---

## Performance Expectations for m7i-flex.large (2 vCPU, 8GB)

### Test Mode (2^20 seed space):

| Addresses | Expected Time | Cost (On-Demand) | Cost (Spot ~70% off) |
|-----------|---------------|------------------|---------------------|
| 100 | ~1-2 hours | ~$0.23 | ~$0.07 |
| 500 | ~5-8 hours | ~$1.15 | ~$0.35 |
| 1,000 | ~10-15 hours | ~$2.30 | ~$0.70 |
| 10,000 | ~100-150 hours | ~$23 | ~$7 |

### Notes:
- Your 2 vCPU instance is **~4x slower** than recommended 8 vCPU for PRNG reconstruction
- Address collection and entropy analysis are **not affected** (API-limited)
- Consider starting with **100-500 addresses** for first test
- Can upgrade to larger instance later if needed

---

## Troubleshooting

### Installation fails with "permission denied"

```bash
# Check if install.sh is executable
ls -l install.sh

# Make it executable
chmod +x install.sh

# Try again
./install.sh
```

### "Module not found" errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Out of disk space

```bash
# Check disk usage
df -h

# If low, clean up
sudo apt-get clean
sudo apt-get autoremove -y

# Check again
df -h
```

### Scanner not starting

```bash
# Check if already running
ps aux | grep python

# If stuck, kill and restart
pkill -9 python3
./run_aws.sh 100 test 2
```

### Can't connect to mempool.space API

```bash
# Test internet connectivity
curl -I https://mempool.space/testnet/api/blocks/tip/height

# Should return: HTTP/2 200

# Test DNS
nslookup mempool.space

# Check security group allows HTTPS outbound
```

---

## Stopping the Scanner

### Graceful Stop (Saves checkpoint)

```bash
# Get PID from run_aws.sh output or:
ps aux | grep python

# Send TERM signal (scanner saves checkpoint)
kill -TERM <PID>

# Wait 30 seconds for graceful shutdown
# Check if stopped:
ps aux | grep python
```

### Force Stop (Use only if graceful fails)

```bash
# Force kill
pkill -9 python3

# Note: Checkpoint may not be saved
```

---

## Resuming from Checkpoint

```bash
# Just run the scanner again
./run_aws.sh 10000 test 2

# It will automatically detect checkpoint.json and resume
# You'll see: "✓ Checkpoint loaded: X addresses already processed"
```

---

## Stopping the EC2 Instance (Save Money)

### When you're done scanning:

```bash
# Exit SSH
exit
```

### From Windows PowerShell or AWS Console:

**Option A: Stop (preserves data, cheaper)**
```powershell
# Stop instance (data preserved, only pay for storage)
aws ec2 stop-instances --instance-ids <INSTANCE-ID>
```

**Option B: AWS Console**
1. Go to EC2 → Instances
2. Select `[REDACTED_PRIVATE_KEY]`
3. Instance state → Stop instance

**Cost while stopped**: ~$0.02/day (30 GB storage only)

### To resume later:
1. Start instance from AWS Console
2. Note: IP will change (unless you have Elastic IP)
3. SSH in with new IP
4. Run scanner again (resumes from checkpoint)

---

## Cleanup (When Completely Done)

### Delete Everything:

```bash
# On EC2, before terminating:
# Download results to your local machine

# From Windows PowerShell:
scp -i "$env:USERPROFILE\.ssh\weak-key-scanner.pem" -r ubuntu@<INSTANCE-IP>:~/bitcoin-weak-key-scanner/results/* .
```

### Terminate Instance:

**AWS Console**:
1. EC2 → Instances
2. Select instance
3. Instance state → Terminate instance
4. Confirm

**Result**: All data deleted, no more charges

---

## Quick Command Reference

```bash
# Activate environment
source venv/bin/activate

# Run scanner
./run_aws.sh 100 test 2

# Monitor
./monitor.sh
# OR
tail -f logs/aws_execution_*.log

# Check progress
cat checkpoint.json

# Stop scanner
kill -TERM <PID>

# View results
cat results/summary_report_*.txt
```

---

## Next Steps After First Successful Run

1. ✅ **Verify Results**:
   - Check `results/summary_report_*.txt`
   - Verify weak addresses found
   - Confirm testnet-only enforcement

2. ✅ **Scale Up** (if satisfied):
   - Edit `config/config.yaml` → increase `num_addresses`
   - Run larger scan (500-1,000 addresses)

3. ✅ **Optimize Costs**:
   - Stop instance when not scanning
   - Consider upgrading to c5.2xlarge for 4x speed (if budget allows)
   - Use spot instances for 70% savings

4. ✅ **Backup Results**:
   - Download results to local machine (SCP command above)
   - Optional: Upload to S3 for permanent storage

---

## Support

If you encounter issues:

1. Check **troubleshooting** sections in this file
2. Review **logs**: `tail -f logs/*.log`
3. Check **README.md** and **QUICKREF.md** for additional help
4. Verify **security group** allows HTTPS outbound
5. Ensure **API access**: `curl https://mempool.space/testnet/api/blocks/tip/height`

---

**You're ready to start! Begin with PART 1 above after SSH connection.**
