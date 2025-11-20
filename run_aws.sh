#!/bin/bash
# AWS Execution Script for Bitcoin Weak Key Scanner
# Optimized for long-running AWS EC2 execution with automatic recovery

set -e

echo "======================================================================"
echo "Bitcoin Weak Key Scanner - AWS Execution"
echo "======================================================================"
echo "Starting at: $(date)"
echo ""

# Configuration
ADDRESSES="${1:-10000}"        # Number of addresses to scan (default: 10000)
MODE="${2:-test}"              # Mode: test or production (default: test)
WORKERS="${3:-8}"              # Parallel workers (default: 8)

echo "Configuration:"
echo "  Target Addresses: $ADDRESSES"
echo "  Mode: $MODE"
echo "  Workers: $WORKERS"
echo ""

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "Virtual environment not found. Run install.sh first."
        exit 1
    fi
fi

# Create necessary directories
mkdir -p logs
mkdir -p results

# Update config with runtime parameters
echo "Updating configuration..."
python3 << EOF
import yaml

config_path = 'config/config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

config['scanning']['num_addresses'] = $ADDRESSES
config['prng_attack']['mode'] = '$MODE'
config['prng_attack']['parallel_workers'] = $WORKERS

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print(f"Configuration updated: {$ADDRESSES} addresses, {$MODE} mode, {$WORKERS} workers")
EOF

# Run the scanner with nohup for background execution
echo ""
echo "======================================================================"
echo "Starting scan in background..."
echo "======================================================================"

cd src

nohup python3 main.py \
    --config ../config/config.yaml \
    --addresses $ADDRESSES \
    > ../logs/aws_execution_$(date +%Y%m%d_%H%M%S).log 2>&1 &

PID=$!

echo "Scanner started with PID: $PID"
echo "Log file: logs/aws_execution_*.log"
echo ""
echo "To monitor progress:"
echo "  tail -f logs/aws_execution_*.log"
echo ""
echo "To check process status:"
echo "  ps aux | grep $PID"
echo ""
echo "To stop the scanner:"
echo "  kill -TERM $PID"
echo ""
echo "Results will be saved to: results/"
echo ""
echo "======================================================================"

# Create monitoring script
cat > ../monitor.sh << 'MONITOR_EOF'
#!/bin/bash
# Monitor script for AWS execution

echo "Bitcoin Weak Key Scanner - Monitor"
echo "=================================="
echo ""

# Find the latest log file
LATEST_LOG=$(ls -t logs/aws_execution_*.log 2>/dev/null | head -n1)

if [ -z "$LATEST_LOG" ]; then
    echo "No execution logs found."
    exit 1
fi

echo "Monitoring log: $LATEST_LOG"
echo ""

# Extract key progress indicators
echo "Recent Progress:"
echo "----------------"
tail -n 20 "$LATEST_LOG" | grep -E "(progress|analyzed|found|recovered|complete)" || echo "No progress updates yet"

echo ""
echo "Statistics:"
echo "-----------"
grep -E "(Addresses analyzed|Weak addresses|Keys recovered)" "$LATEST_LOG" | tail -n 5 || echo "No statistics available yet"

echo ""
echo "Last 5 log entries:"
echo "-------------------"
tail -n 5 "$LATEST_LOG"
MONITOR_EOF

chmod +x ../monitor.sh

echo "Monitor script created: monitor.sh"
echo "Run './monitor.sh' to check progress"
echo ""
