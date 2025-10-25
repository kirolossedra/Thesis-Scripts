#!/usr/bin/env python3
import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

# ==============================
# iperf3 writes its own log, Python reads it live
# ==============================

session_name = "iperf3"
target = "192.168.0.227"
test_duration = 9000
interval = 1
log_dir = "C:\\logs"

Path(log_dir).mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"{session_name}_{timestamp}.txt")

print("--------------------------------------------")
print(f"Session: {session_name}")
print(f"Target: {target}")
print(f"Log File: {log_file}")
print("--------------------------------------------\n")

# Start iperf3 with --logfile parameter to write its own log
process = subprocess.Popen(
    ['iperf3', '-c', target, '-t', str(test_duration), '-i', str(interval), 
     '--get-server-output', '--timestamps', '--logfile', log_file]
)

print(f"iperf3 started with PID {process.pid}")
print(f"Reading log file in real-time...\n")

# Wait a moment for the file to be created
time.sleep(1)

# Read the log file line by line as iperf3 writes to it
try:
    with open(log_file, 'r') as f:
        # Move to the end of file if it already has content
        f.seek(0, 2)
        
        while process.poll() is None:  # While iperf3 is still running
            line = f.readline()
            if line:
                print(line, end='', flush=True)
            else:
                time.sleep(0.1)  # Wait a bit before checking again
        
        # Read any remaining lines after process ends
        for line in f:
            print(line, end='', flush=True)
            
except KeyboardInterrupt:
    print("\n\nStopping iperf3...")
    process.terminate()
    process.wait()

print(f"\n\niperf3 finished. Log saved to: {log_file}")