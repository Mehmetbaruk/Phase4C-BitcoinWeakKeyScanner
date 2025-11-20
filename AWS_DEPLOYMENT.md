# AWS Deployment Quick Start Guide

## Prerequisites

### AWS Account Setup
1. AWS Account with EC2 access
2. SSH key pair created (`.pem` file)
3. Basic understanding of EC2 console

### Recommended Instance Types

| Instance Type | vCPU | RAM   | Price/Hour | Best For |
|---------------|------|-------|------------|----------|
| c5.2xlarge    | 8    | 16 GB | $0.34      | Balanced |
| c5.4xlarge    | 16   | 32 GB | $0.68      | Fast     |
| c5.xlarge     | 4    | 8 GB  | $0.17      | Budget   |

**Spot Instance Discount**: ~70% savings (recommended with checkpoint/resume)

---

## Step-by-Step AWS Deployment

### Step 1: Launch EC2 Instance

```bash
# Via AWS CLI (or use Console)
aws ec2 run-instances \
    --image-id ami-0c7217cdde317cfec \  # Ubuntu 22.04 LTS (update for your region)
    --instance-type c5.2xlarge \
    --key-name your-key-name \
    --security-group-ids sg-xxxxxxxx \
    --subnet-id subnet-xxxxxxxx \
    --block-device-mappings DeviceName=/dev/sda1,Ebs={VolumeSize=30} \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=WeakKeyScanner}]'
```

**Via Console**:
1. EC2 Dashboard → Launch Instance
2. **AMI**: Ubuntu Server 22.04 LTS
3. **Instance Type**: c5.2xlarge
4. **Storage**: 30 GB gp3
5. **Security Group**: Allow outbound HTTPS (443)
6. **Key Pair**: Select your `.pem` file

### Step 2: Connect to Instance

```bash
# Get public IP from console
export INSTANCE_IP=54.123.456.789

# Connect
ssh -i ~/.ssh/your-key.pem ubuntu@$INSTANCE_IP
```

### Step 3: Install Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install git
sudo apt-get install -y git

# Clone repository (replace with your repo URL)
git clone https://github.com/your-org/weak-key-scanner.git
cd weak-key-scanner

# Run installer
chmod +x install.sh
./install.sh

# Should see: "✓ All required packages installed successfully"
```

### Step 4: Configure for Your Needs

```bash
# Edit configuration
nano config/config.yaml

# Key settings to review:
# - scanning.num_addresses: 10000 (adjust as needed)
# - prng_attack.mode: "test" or "production"
# - prng_attack.parallel_workers: 8 (match your vCPU count)
```

### Step 5: Run Scan

#### Option A: Quick Test Run

```bash
# Test with small dataset first
cd src
python3 main.py --addresses 10

# Should complete in ~10 minutes
# Verify results in ../results/
```

#### Option B: Long-Running Production Scan

```bash
# Return to root directory
cd ..

# Start background execution
./run_aws.sh 10000 test 8
#            ↑      ↑    ↑
#            |      |    └─ Workers (match vCPU)
#            |      └────── Mode (test/production)
#            └─────────── Addresses to scan

# Output:
# Scanner started with PID: 12345
# Log file: logs/aws_execution_20251103_143000.log
```

### Step 6: Monitor Execution

```bash
# From same instance
./monitor.sh

# Or continuously tail log
tail -f logs/aws_execution_*.log

# Check process is running
ps aux | grep python
```

### Step 7: Disconnect Safely

```bash
# Option A: Use screen (recommended)
screen -S scanner
./run_aws.sh 10000 test 8
# Press Ctrl+A, then D to detach
# To reattach: screen -r scanner

# Option B: Use tmux
tmux new -s scanner
./run_aws.sh 10000 test 8
# Press Ctrl+B, then D to detach
# To reattach: tmux attach -t scanner

# Option C: nohup (already done by run_aws.sh)
# Just exit SSH - process continues
```

---

## Monitoring from Local Machine

### Option 1: SSH Log Streaming

```bash
# Stream logs to your local terminal
ssh -i ~/.ssh/your-key.pem ubuntu@$INSTANCE_IP \
    "tail -f weak-key-scanner/logs/*.log"
```

### Option 2: Periodic Status Checks

```bash
# Check status every 5 minutes
watch -n 300 ssh -i ~/.ssh/your-key.pem ubuntu@$INSTANCE_IP \
    "cd weak-key-scanner && ./monitor.sh"
```

### Option 3: Copy Results Periodically

```bash
# Download results as they're generated
scp -i ~/.ssh/your-key.pem \
    ubuntu@$INSTANCE_IP:weak-key-scanner/results/*.json \
    ./local-results/
```

---

## Using Spot Instances (70% Savings)

### Why Spot Instances Work Well

This tool's checkpoint/resume system is **designed for spot interruptions**:

1. **Automatic Checkpointing**: Saves every 100 addresses
2. **Signal Handling**: Catches AWS's 2-minute warning
3. **Resume on Restart**: Picks up where it left off

### Launch Spot Instance

```bash
# Via AWS CLI
aws ec2 request-spot-instances \
    --instance-count 1 \
    --type "one-time" \
    --launch-specification file://spot-specification.json

# spot-specification.json:
{
  "ImageId": "ami-0c7217cdde317cfec",
  "InstanceType": "c5.2xlarge",
  "KeyName": "your-key-name",
  "SecurityGroupIds": ["sg-xxxxxxxx"],
  "SubnetId": "subnet-xxxxxxxx"
}
```

**Via Console**:
1. EC2 → Spot Requests → Request Spot Instances
2. Same configuration as on-demand
3. Maximum price: Leave as default (current spot price)

### Handling Spot Interruption

When AWS reclaims your spot instance:

1. **Automatic**: Signal handler saves checkpoint
2. **Launch new spot instance** (or use same one when available)
3. **Run scanner again**: Automatically resumes from checkpoint

```bash
# On new instance, after installation
cd weak-key-scanner
./run_aws.sh 10000 test 8

# Output will show:
# "Checkpoint loaded: 3,456 addresses already processed"
# "Resuming from checkpoint"
```

---

## Cost Optimization Strategies

### 1. Use Spot Instances

**Savings**: ~70%

```
c5.2xlarge On-Demand: $0.34/hour
c5.2xlarge Spot:      $0.10/hour (typical)
```

For 100-hour scan:
- On-Demand: $34
- Spot: $10
- **Savings: $24**

### 2. Right-Size Your Instance

| Addresses | Mode       | Recommended Instance | Est. Cost (Spot) |
|-----------|------------|----------------------|------------------|
| 100       | Test       | c5.xlarge (4 vCPU)   | $0.50            |
| 1,000     | Test       | c5.2xlarge (8 vCPU)  | $1.50            |
| 10,000    | Test       | c5.2xlarge (8 vCPU)  | $15              |
| 100       | Production | c5.4xlarge (16 vCPU) | $20              |

### 3. Stop Instance When Not Scanning

```bash
# Stop instance (keeps EBS volume)
aws ec2 stop-instances --instance-ids i-xxxxxxxxx

# Costs while stopped: Only EBS ($0.10/GB-month)
# For 30 GB: ~$3/month

# Restart when needed
aws ec2 start-instances --instance-ids i-xxxxxxxxx
```

### 4. Use Checkpointing Strategically

- **Long runs**: Set `checkpoint_interval: 50` for more frequent saves
- **Spot instances**: Reduces lost work on interruption
- **Development**: Use `--no-checkpoint` to avoid resume confusion

---

## Troubleshooting AWS-Specific Issues

### Issue: Can't Connect via SSH

**Check**:
```bash
# Security group allows SSH
aws ec2 describe-security-groups --group-ids sg-xxxxxxxx

# Instance is running
aws ec2 describe-instances --instance-ids i-xxxxxxxx
```

**Solution**:
- Add inbound rule: SSH (port 22) from your IP
- Verify `.pem` file permissions: `chmod 400 your-key.pem`

### Issue: Out of Disk Space

```bash
# Check disk usage
df -h

# Clean logs if needed
cd weak-key-scanner
rm logs/aws_execution_*.log  # Keep only latest
```

**Solution**: Increase EBS volume in AWS console

### Issue: Process Killed (OOM)

```bash
# Check system logs
dmesg | tail
```

**Solution**:
- Reduce `batch_size` in config.yaml
- Use instance with more RAM
- Reduce `parallel_workers`

### Issue: Spot Instance Terminated Too Quickly

**Symptoms**: Spot instance terminates before checkpoint saves

**Solution**:
- Reduce `checkpoint_interval` to 50 or 25
- Use on-demand for critical final hours
- Monitor spot pricing: `aws ec2 describe-spot-price-history`

---

## AWS CloudWatch Integration

### Enable CloudWatch Logs (Optional)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure to ship logs
sudo nano /opt/aws/amazon-cloudwatch-agent/bin/config.json
```

**Config snippet**:
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/home/ubuntu/weak-key-scanner/logs/*.log",
            "log_group_name": "/aws/ec2/weak-key-scanner",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

### Benefits

- **Remote Monitoring**: Check logs from AWS Console
- **Alerting**: Set alarms on error patterns
- **Retention**: Keep logs after instance termination
- **Analysis**: Use CloudWatch Insights for pattern detection

---

## Production Checklist

Before running production scans:

- [ ] Instance type sized appropriately
- [ ] EBS volume has sufficient space (30+ GB)
- [ ] Security group allows outbound HTTPS
- [ ] Config file reviewed and customized
- [ ] Test run completed successfully
- [ ] Screen or tmux session started
- [ ] Monitor script working
- [ ] Backup plan for checkpoint file
- [ ] Cost alerts configured in AWS
- [ ] Spot instance interruption handling tested

---

## Example: Complete 10,000 Address Scan

```bash
# 1. Launch c5.2xlarge spot instance
aws ec2 request-spot-instances --instance-count 1 ...

# 2. Connect
ssh -i key.pem ubuntu@<ip>

# 3. Install
git clone <repo> && cd weak-key-scanner
./install.sh

# 4. Configure
nano config/config.yaml
# Set: num_addresses: 10000, mode: test, workers: 8

# 5. Start scan in screen
screen -S scanner
./run_aws.sh 10000 test 8
# Ctrl+A, D to detach

# 6. Monitor from local machine
ssh -i key.pem ubuntu@<ip> "tail -f weak-key-scanner/logs/*.log"

# 7. Wait ~150 hours (spot price ~$15 total)

# 8. Retrieve results
scp -i key.pem ubuntu@<ip>:weak-key-scanner/results/*.json ./

# 9. Terminate instance
aws ec2 terminate-instances --instance-ids i-xxxxxxxx
```

**Total Cost**: ~$15 (spot) or ~$50 (on-demand)

---

## Advanced: Multi-Region Parallel Scanning

For very large scans, distribute across regions:

```bash
# Region 1: us-east-1
./run_aws.sh 5000 test 8 --start-block 700000

# Region 2: eu-west-1
./run_aws.sh 5000 test 8 --start-block 750000

# Merge results locally
cat results_us/*.json results_eu/*.json > combined_results.json
```

---

## Questions?

Common AWS scenarios:
- **Budget concern**: Use c5.xlarge spot (~$0.05/hr)
- **Time concern**: Use c5.4xlarge on-demand (~$0.68/hr)
- **Learning**: Start with 100 addresses on smallest instance

For more help, see main README.md
