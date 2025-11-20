# AWS Setup Requirements for Bitcoin Weak Key Scanner

## What You Need to Create in AWS

### 1. EC2 Instance

**Purpose**: Run the weak key scanner application

**Specifications**:
```
AMI: Ubuntu Server 22.04 LTS (ami-0c7217cdde317cfec or equivalent for your region)
Instance Type: c5.2xlarge (8 vCPU, 16 GB RAM)
Storage: 30 GB EBS gp3
Network: VPC with internet access
```

**Step-by-Step in AWS Console**:
1. Go to EC2 Dashboard
2. Click "Launch Instance"
3. Choose:
   - Name: `[REDACTED_PRIVATE_KEY]`
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: `c5.2xlarge`
   - Key pair: Create new or use existing (you'll need the `.pem` file)
   - Network: Default VPC is fine
   - Storage: 30 GB gp3
   - Advanced: Leave defaults

**Cost Estimate**:
- On-Demand: $0.34/hour (~$8/day)
- Spot Instance: $0.10/hour (~$2.40/day) ← **RECOMMENDED**

---

### 2. Security Group

**Purpose**: Control network access to your instance

**Configuration**:
```
Inbound Rules:
- SSH (port 22) from YOUR IP only
  Example: SSH, TCP, 22, 123.45.67.89/32

Outbound Rules:
- HTTPS (port 443) to anywhere (0.0.0.0/0)
  Required for: Mempool.space API calls
- HTTP (port 80) to anywhere (0.0.0.0/0)
  Optional: Package downloads
```

**Step-by-Step in AWS Console**:
1. EC2 Dashboard → Security Groups
2. Create Security Group
3. Name: `weak-key-scanner-sg`
4. VPC: Select your VPC (default is fine)
5. Add Inbound Rule:
   - Type: SSH
   - Port: 22
   - Source: My IP (automatically fills your current IP)
6. Outbound rules are usually open by default (allow all)
7. Click "Create"

**Important**: Your IP will change if you're on residential internet. You may need to update the SSH rule periodically.

---

### 3. SSH Key Pair

**Purpose**: Secure access to your EC2 instance

**Creation**:
```
Either:
A) Create in AWS Console during EC2 launch
B) Create separately: EC2 Dashboard → Key Pairs → Create Key Pair
```

**What You Get**:
- A `.pem` file (e.g., `weak-key-scanner.pem`)
- **IMPORTANT**: Save this file securely - you cannot download it again

**Setup on Your Local Machine**:
```bash
# Move to .ssh directory
mv ~/Downloads/weak-key-scanner.pem ~/.ssh/

# Set correct permissions (required for SSH)
chmod 400 ~/.ssh/weak-key-scanner.pem

# Test connection
ssh -i ~/.ssh/weak-key-scanner.pem ubuntu@<instance-public-ip>
```

---

### 4. Elastic IP (Optional but Recommended)

**Purpose**: Keep the same IP address even if you stop/start the instance

**Why Recommended**:
- Without it: IP changes every time you stop/start
- With it: IP stays constant (easier for SSH access)

**Cost**: FREE while instance is running, $0.005/hour when instance is stopped

**Step-by-Step**:
1. EC2 Dashboard → Elastic IPs
2. Click "Allocate Elastic IP address"
3. Click "Allocate"
4. Select the new IP → Actions → Associate Elastic IP address
5. Choose your instance
6. Click "Associate"

**Result**: Your instance now has a permanent IP address

---

### 5. IAM Role (Optional - for CloudWatch Logs)

**Purpose**: Allow EC2 to send logs to CloudWatch (advanced monitoring)

**Only needed if**: You want logs in AWS Console instead of just on the instance

**Setup**:
1. IAM Dashboard → Roles → Create Role
2. Type: AWS service → EC2
3. Permissions: `[REDACTED_PRIVATE_KEY]`
4. Name: `[REDACTED_PRIVATE_KEY]`
5. Attach to EC2: Instance → Actions → Security → Modify IAM Role

**Cost**: CloudWatch Logs pricing applies (first 5 GB/month free)

---

## Quick Setup Checklist

### Minimum Setup (Required)

- [ ] **EC2 Instance**: c5.2xlarge, Ubuntu 22.04, 30 GB storage
- [ ] **Security Group**: SSH from your IP, HTTPS outbound
- [ ] **SSH Key Pair**: Downloaded `.pem` file, permissions set to 400

**Time to Setup**: 10 minutes  
**Cost**: ~$2.40/day (spot) or ~$8/day (on-demand)

### Recommended Setup

- [ ] All items from Minimum Setup
- [ ] **Elastic IP**: Associated with instance
- [ ] **Spot Instance**: Instead of on-demand (70% savings)

**Time to Setup**: 15 minutes  
**Cost**: ~$2.40/day + $0.12/day (Elastic IP when stopped)

### Advanced Setup (Optional)

- [ ] All items from Recommended Setup
- [ ] **IAM Role**: For CloudWatch Logs
- [ ] **CloudWatch Alarms**: For monitoring/alerts
- [ ] **S3 Bucket**: For result backup

**Time to Setup**: 30 minutes  
**Cost**: +$1-2/month for CloudWatch/S3

---

## Step-by-Step: Complete AWS Setup

### Phase 1: Launch Instance (5 minutes)

```
1. Go to AWS Console → EC2 → Launch Instance
2. Name: bitcoin-weak-key-scanner
3. AMI: Ubuntu Server 22.04 LTS
4. Instance type: c5.2xlarge
5. Key pair: Create new "weak-key-scanner" (download .pem)
6. Network: Default VPC, auto-assign public IP
7. Configure storage: 30 GB gp3
8. Advanced details → Request Spot instances (check box)
9. Launch instance
```

**What happens**: AWS creates your server (~2 minutes to boot)

### Phase 2: Configure Security (3 minutes)

```
1. Wait for instance status: "Running"
2. Select your instance
3. Click "Security" tab
4. Click security group link
5. Edit inbound rules
6. Add: SSH, port 22, My IP
7. Save rules
```

**What happens**: SSH access is now allowed from your computer

### Phase 3: Connect and Install (10 minutes)

```bash
# 1. Get the public IP from EC2 Console
# 2. Connect via SSH
ssh -i ~/.ssh/weak-key-scanner.pem ubuntu@<public-ip>

# 3. Clone the repository
git clone <your-repo-url>
cd weak-key-scanner

# 4. Run the installer
chmod +x install.sh
./install.sh

# 5. Verify installation
source venv/bin/activate
python3 -c "import bitcoinlib; print('✓ Ready to scan')"
```

**What happens**: All dependencies installed, scanner ready to run

### Phase 4: Start Scanning (2 minutes)

```bash
# Start a test scan
./run_aws.sh 100 test 8

# Monitor progress
./monitor.sh

# Or tail the log
tail -f logs/aws_execution_*.log
```

**What happens**: Scanner runs in background, saving progress every 100 addresses

---

## Cost Breakdown

### Example: 10,000 Address Scan in Test Mode

| Resource | Type | Duration | Cost |
|----------|------|----------|------|
| EC2 c5.2xlarge | Spot | 150 hours | $15 |
| EBS Storage | 30 GB gp3 | 6 days | $0.18 |
| Data Transfer | API calls | Negligible | $0 |
| **Total** | | **~6 days** | **~$15.20** |

### Cost Optimization

**Use Spot Instances**:
- On-demand: $51 for 150 hours
- Spot: $15 for 150 hours
- **Savings: $36 (71%)**

**Stop When Not Scanning**:
- Running: $0.10/hour
- Stopped: $0.02/hour (EBS only)
- **Savings: $1.92/day when stopped**

---

## Common Questions

### Q: Can I use a smaller instance?

**A**: Yes, but it will be slower
- `t3.medium` (2 vCPU): 4x slower, $0.02/hour spot
- `c5.xlarge` (4 vCPU): 2x slower, $0.05/hour spot
- `c5.2xlarge` (8 vCPU): Recommended, $0.10/hour spot
- `c5.4xlarge` (16 vCPU): 1.5x faster, $0.20/hour spot

### Q: What if my spot instance gets terminated?

**A**: The scanner handles this automatically:
1. AWS sends SIGTERM (2-minute warning)
2. Scanner saves checkpoint
3. Launch new spot instance
4. Run scanner again - it resumes from checkpoint
5. No work lost!

### Q: Can I run this from my laptop?

**A**: Yes, but not recommended because:
- Long-running (hours to days)
- Need to keep laptop on and connected
- AWS EC2 is designed for this use case
- Cheaper than your electricity + wear on laptop

### Q: How do I know it's working?

**A**: Multiple ways:
```bash
# Check process is running
ps aux | grep python

# View progress
./monitor.sh

# Tail logs
tail -f logs/*.log

# Check checkpoint file
cat checkpoint.json
```

### Q: What if I want to stop and resume later?

**A**: Easy:
```bash
# Stop the scanner
kill -TERM <pid>  # Gets PID from run_aws.sh output

# Or just stop the EC2 instance
# The checkpoint file is preserved

# To resume: Start instance, SSH in, run scanner again
./run_aws.sh 10000 test 8
# Output: "Checkpoint loaded: 3,456 addresses already processed"
```

---

## Troubleshooting AWS Setup

### Can't SSH to instance

**Check**:
```bash
# 1. Instance is running?
# EC2 Console → Instances → Status should be "running"

# 2. Security group allows your IP?
# Instance → Security → Inbound rules → SSH from your IP

# 3. Key file permissions?
chmod 400 ~/.ssh/weak-key-scanner.pem

# 4. Using correct username?
ssh -i ~/.ssh/weak-key-scanner.pem ubuntu@<ip>
#                                  ^^^^^^ Ubuntu AMI uses "ubuntu"
```

### Out of disk space

**Solution**:
```bash
# Check usage
df -h

# If full, increase EBS volume:
# 1. EC2 Console → Instances → Storage → Volume ID
# 2. Actions → Modify Volume → New size: 50 GB
# 3. SSH to instance and resize filesystem:
sudo growpart /dev/xvda 1
sudo resize2fs /dev/xvda1
```

### Spot instance keeps getting terminated

**Solution**:
1. Check spot price history: Is demand high in your region?
2. Try different instance type: c5.large instead of c5.2xlarge
3. Use on-demand for final hours of scan
4. Switch region if spot prices are high

---

## AWS Console URLs

**Quick Links**:
- EC2 Dashboard: https://console.aws.amazon.com/ec2
- Security Groups: https://console.aws.amazon.com/ec2/home#SecurityGroups
- Elastic IPs: https://console.aws.amazon.com/ec2/home#Addresses
- Key Pairs: https://console.aws.amazon.com/ec2/home#KeyPairs
- Spot Instances: https://console.aws.amazon.com/ec2sp/home#/spot

---

## Summary: What to Create

**Absolute Minimum** (10 minutes):
1. ✅ EC2 Instance (c5.2xlarge spot, Ubuntu 22.04, 30 GB)
2. ✅ Security Group (SSH from your IP)
3. ✅ SSH Key Pair (download .pem file)

**That's it!** These 3 things are all you need to run the scanner.

**Total Cost**: ~$15 for 10,000 address scan (~6 days)

---

## Ready to Start?

Once you have your EC2 instance running:

```bash
# Connect
ssh -i ~/.ssh/weak-key-scanner.pem ubuntu@<instance-ip>

# Install
git clone <repo-url> && cd weak-key-scanner
./install.sh

# Run
./run_aws.sh 10000 test 8

# Monitor
./monitor.sh
```

**Questions?** Refer to AWS_DEPLOYMENT.md for detailed instructions.
