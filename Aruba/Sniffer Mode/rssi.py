import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

TARGET_MAC = "4c:49:6c:d4:db:a9"

def parse_log_file(filepath):
    """Parse a log file and extract timestamp and RSSI for target MAC address."""
    data = []
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split by the delimiter
    sections = content.split('/////')
    
    print(f"  Total sections found: {len(sections)}")
    
    # Process sections
    current_time = None
    
    for i, section in enumerate(sections):
        # Look for LocalBeginTime
        time_match = re.search(r'LocalBeginTime:\s*(\d+)\s*\(([^)]+)\)', section)
        
        if time_match:
            time_str = time_match.group(2)
            try:
                # Parse the timestamp - Format: 2025-10-24T11:32:14.662-0400
                time_clean = time_str.split('.')[0]
                current_time = datetime.strptime(time_clean, '%Y-%m-%dT%H:%M:%S')
            except Exception as e:
                print(f"  Warning: couldn't parse timestamp '{time_str}': {e}")
                current_time = None
        
        # Look for the target MAC address and extract RSSI
        # The line format has multiple columns, RSSI is after SNR
        # Pattern: MAC address ... snr rssi cl-delay ...
        # We need to match the entire line to get proper column alignment
        mac_pattern = rf'{TARGET_MAC}\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)\s+(\d+)'
        mac_match = re.search(mac_pattern, section, re.IGNORECASE)
        
        if mac_match and current_time:
            snr = int(mac_match.group(1))
            rssi = int(mac_match.group(2))
            data.append((current_time, rssi, snr))
            print(f"  Found {TARGET_MAC} at {current_time} with RSSI={rssi}, SNR={snr}")
    
    print(f"  Successfully parsed {len(data)} data points for MAC {TARGET_MAC}")
    return data

def scan_and_plot():
    """Scan current directory for text files and plot RSSI changes."""
    all_data = []
    files_checked = []
    found_data = False
    
    # Find all text files in current directory
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt') or f.endswith('.log')]
    
    print(f"Found {len(txt_files)} log/txt files in current directory:")
    for filename in txt_files:
        print(f"  - {filename}")
    print()
    
    # Check files until we find one with data
    for filename in txt_files:
        files_checked.append(filename)
        print(f"Checking: {filename}")
        try:
            data = parse_log_file(filename)
            if data:
                all_data.extend(data)
                found_data = True
                print(f"  ✓ Found data in {filename}")
                break  # Stop after finding first file with data
            else:
                print(f"  ✗ No data for MAC {TARGET_MAC} found")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    if not found_data:
        print("\n" + "="*50)
        print("NO DATA FOUND!")
        print(f"Checked {len(files_checked)} files, none had data for MAC {TARGET_MAC}")
        print("="*50)
        return
    
    # Sort by timestamp
    all_data.sort(key=lambda x: x[0])
    
    # Extract data
    timestamps = [d[0] for d in all_data]
    rssi_values = [d[1] for d in all_data]
    snr_values = [d[2] for d in all_data]
    
    # Create the plot with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Plot RSSI
    ax1.plot(timestamps, rssi_values, linewidth=2, color='crimson', 
             alpha=0.7, marker='o', markersize=5, label='RSSI')
    ax1.fill_between(timestamps, rssi_values, alpha=0.2, color='crimson')
    
    # RSSI formatting
    ax1.set_ylabel('RSSI (dBm)', fontsize=12, fontweight='bold')
    ax1.set_title(f'RSSI and SNR Timeline for MAC {TARGET_MAC}', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(loc='upper right', fontsize=10)
    
    # Add reference lines for RSSI quality
    ax1.axhline(y=80, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax1.axhline(y=70, color='orange', linestyle='--', alpha=0.5, linewidth=1)
    ax1.axhline(y=60, color='green', linestyle='--', alpha=0.5, linewidth=1)
    ax1.text(timestamps[-1], 80, ' Poor', va='center', ha='left', fontsize=8, color='red')
    ax1.text(timestamps[-1], 70, ' Fair', va='center', ha='left', fontsize=8, color='orange')
    ax1.text(timestamps[-1], 60, ' Good', va='center', ha='left', fontsize=8, color='green')
    
    # Invert y-axis for RSSI (lower values = better signal in dBm)
    ax1.invert_yaxis()
    
    # Plot SNR
    ax2.plot(timestamps, snr_values, linewidth=2, color='steelblue', 
             alpha=0.7, marker='s', markersize=5, label='SNR')
    ax2.fill_between(timestamps, snr_values, alpha=0.2, color='steelblue')
    
    # SNR formatting
    ax2.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax2.set_ylabel('SNR (dB)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(loc='upper right', fontsize=10)
    
    # Add reference lines for SNR quality
    ax2.axhline(y=25, color='green', linestyle='--', alpha=0.5, linewidth=1)
    ax2.axhline(y=15, color='orange', linestyle='--', alpha=0.5, linewidth=1)
    ax2.axhline(y=10, color='red', linestyle='--', alpha=0.5, linewidth=1)
    ax2.text(timestamps[-1], 25, ' Excellent', va='center', ha='left', fontsize=8, color='green')
    ax2.text(timestamps[-1], 15, ' Good', va='center', ha='left', fontsize=8, color='orange')
    ax2.text(timestamps[-1], 10, ' Fair', va='center', ha='left', fontsize=8, color='red')
    
    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save the plot
    output_file = f'mac_{TARGET_MAC.replace(":", "")}_rssi_timeline.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved as: {output_file}")
    
    # Show summary
    start_time = min(timestamps).strftime('%Y-%m-%d %H:%M:%S')
    end_time = max(timestamps).strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Target MAC: {TARGET_MAC}")
    print(f"  Files checked: {len(files_checked)}")
    print(f"  Total data points: {len(all_data)}")
    print(f"  Time range: {start_time} to {end_time}")
    print(f"\n  RSSI Statistics:")
    print(f"    Min: {min(rssi_values)} dBm")
    print(f"    Max: {max(rssi_values)} dBm")
    print(f"    Average: {sum(rssi_values)/len(rssi_values):.1f} dBm")
    print(f"    Median: {sorted(rssi_values)[len(rssi_values)//2]} dBm")
    print(f"\n  SNR Statistics:")
    print(f"    Min: {min(snr_values)} dB")
    print(f"    Max: {max(snr_values)} dB")
    print(f"    Average: {sum(snr_values)/len(snr_values):.1f} dB")
    print(f"    Median: {sorted(snr_values)[len(snr_values)//2]} dB")
    
    # Signal quality assessment
    excellent_rssi = sum(1 for r in rssi_values if r <= 60)
    good_rssi = sum(1 for r in rssi_values if 60 < r <= 70)
    fair_rssi = sum(1 for r in rssi_values if 70 < r <= 80)
    poor_rssi = sum(1 for r in rssi_values if r > 80)
    
    print(f"\n  Signal Quality Distribution (RSSI):")
    print(f"    Excellent (≤60 dBm): {excellent_rssi} ({excellent_rssi/len(rssi_values)*100:.1f}%)")
    print(f"    Good (60-70 dBm): {good_rssi} ({good_rssi/len(rssi_values)*100:.1f}%)")
    print(f"    Fair (70-80 dBm): {fair_rssi} ({fair_rssi/len(rssi_values)*100:.1f}%)")
    print(f"    Poor (>80 dBm): {poor_rssi} ({poor_rssi/len(rssi_values)*100:.1f}%)")
    
    print(f"{'='*50}")
    
    plt.show()

if __name__ == "__main__":
    scan_and_plot()