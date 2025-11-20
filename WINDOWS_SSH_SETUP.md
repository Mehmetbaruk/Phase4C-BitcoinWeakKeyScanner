# Windows SSH Setup Guide

## Step 1: Fix Key Pair Filename

Your key file is named `weak-key-scanner.pem.pem` (double extension). We need to rename it.

### Option A: Using File Explorer (Easy)

1. Open File Explorer → Downloads folder
2. Find `weak-key-scanner.pem.pem`
3. Right-click → Rename
4. Change to: `weak-key-scanner.pem` (remove the extra `.pem`)
5. Press Enter

### Option B: Using PowerShell

```powershell
# Navigate to Downloads
cd $env:USERPROFILE\Downloads

# Check if file exists
dir weak-key-scanner.pem.pem

# Rename it
Rename-Item "weak-key-scanner.pem.pem" "weak-key-scanner.pem"

# Verify
dir weak-key-scanner.pem
```

---

## Step 2: Move Key to Safe Location

### Create .ssh directory (if it doesn't exist)

```powershell
# Create .ssh directory
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ssh"

# Move the key file
Move-Item "$env:USERPROFILE\Downloads\weak-key-scanner.pem" "$env:USERPROFILE\.ssh\weak-key-scanner.pem"

# Verify
dir "$env:USERPROFILE\.ssh\weak-key-scanner.pem"
```

---

## Step 3: Set Correct Permissions

Windows doesn't use `chmod` like Linux. Use these commands instead:

```powershell
# Remove inheritance and other users
$keyFile = "$env:USERPROFILE\.ssh\weak-key-scanner.pem"

# Remove all permissions except for current user
icacls $keyFile /inheritance:r
icacls $keyFile /grant:r "$env:USERNAME:(R)"

# Verify (should show only your username with Read access)
icacls $keyFile
```

**Expected output**:
```
C:\Users\YourName\.ssh\weak-key-scanner.pem YourName:(R)
Successfully processed 1 files
```

---

## Step 4: Test SSH Connection

### Get your EC2 instance public IP:

1. Go to AWS Console → EC2 → Instances
2. Click on `[REDACTED_PRIVATE_KEY]`
3. Copy the "Public IPv4 address" (e.g., `54.123.45.67`)

### Connect via SSH:

```powershell
# Replace <YOUR-INSTANCE-IP> with actual IP
ssh -i "$env:USERPROFILE\.ssh\weak-key-scanner.pem" ubuntu@<YOUR-INSTANCE-IP>
```

**Example**:
```powershell
ssh -i "$env:USERPROFILE\.ssh\weak-key-scanner.pem" ubuntu@54.123.45.67
```

### First Connection (First time only):

You'll see:
```
The authenticity of host '54.123.45.67' can't be established.
ECDSA key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no)?
```

Type: `yes` and press Enter

---

## Troubleshooting

### Error: "WARNING: UNPROTECTED PRIVATE KEY FILE!"

**Solution**: Repeat Step 3 (permissions)

### Error: "Permission denied (publickey)"

**Check**:
1. Using correct username? Must be `ubuntu` for Ubuntu AMI
2. Key file path correct? Use `dir "$env:USERPROFILE\.ssh\weak-key-scanner.pem"` to verify
3. Instance running? Check AWS Console

### Error: "Connection timed out"

**Check**:
1. Security group allows SSH from your IP?
2. Instance status is "Running"?
3. Firewall blocking SSH? Try disabling Windows Firewall temporarily

### Can't find SSH command

**Solution**: Install OpenSSH Client:
```powershell
# Check if installed
Get-Command ssh

# If not found, install:
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

---

## Alternative: Use PuTTY (If SSH command doesn't work)

### Step 1: Download PuTTY
- Download: https://www.putty.org/
- Install PuTTY and PuTTYgen

### Step 2: Convert .pem to .ppk
1. Open **PuTTYgen**
2. Click "Load"
3. Change file type to "All Files (*.*)"
4. Select `weak-key-scanner.pem`
5. Click "Save private key"
6. Save as: `weak-key-scanner.ppk`

### Step 3: Connect with PuTTY
1. Open **PuTTY**
2. Host Name: `ubuntu@<YOUR-INSTANCE-IP>`
3. Port: `22`
4. Connection → SSH → Auth → Credentials
5. Browse and select `weak-key-scanner.ppk`
6. Click "Open"

---

## Quick Reference

### Connect to EC2:
```powershell
ssh -i "$env:USERPROFILE\.ssh\weak-key-scanner.pem" ubuntu@<INSTANCE-IP>
```

### Check key permissions:
```powershell
icacls "$env:USERPROFILE\.ssh\weak-key-scanner.pem"
```

### Get instance IP from AWS:
```
AWS Console → EC2 → Instances → bitcoin-weak-key-scanner → Public IPv4 address
```

---

## Next Steps After Connection

Once connected, you'll see:
```
ubuntu@ip-172-31-XX-XX:~$
```

Now proceed to installation (I'll provide commands in the next message).
