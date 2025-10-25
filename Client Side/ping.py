#!/usr/bin/env python3
import subprocess
import sys
from datetime import datetime
import os
from pathlib import Path

# ==============================
# Auto-logging continuous ping with timestamps
# ==============================
session_name = "ping"
target = "192.168.0.227"
timeout_ms = 1000
log_dir = "C:\\logs"

# Create log directory if it doesn't exist
Path(log_dir).mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"{session_name}_{timestamp}.txt")

print("--------------------------------------------")
print(f"Session: {session_name}")
print(f"Target: {target}")
print(f"Timeout: {timeout_ms}ms")
print(f"Log File: {log_file}")
print("--------------------------------------------\n")
print("Ping started. Press Ctrl+C to stop.\n")

# Open log file
with open(log_file, 'w', buffering=1) as f:
    try:
        # Start ping process with timeout option
        if sys.platform == 'win32':
            # Windows: -w sets timeout in milliseconds
            process = subprocess.Popen(
                ['ping', '-t', '-w', str(timeout_ms), target],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                universal_newlines=False
            )
        else:
            # Linux: -W sets timeout in seconds
            timeout_sec = timeout_ms / 1000
            process = subprocess.Popen(
                ['ping', '-W', str(timeout_sec), target],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                universal_newlines=False
            )
        
        # Read and print each line with timestamp
        for line in iter(process.stdout.readline, b''):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            output = line.decode('utf-8', errors='ignore').rstrip()
            logged_line = f"{timestamp} {output}"
            print(logged_line)
            f.write(logged_line + '\n')
            sys.stdout.flush()
            
    except KeyboardInterrupt:
        print("\n\nStopping ping...")
        process.terminate()
        process.wait()
        print(f"\nLog saved to: {log_file}")