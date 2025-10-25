import os
import re
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

TARGET_MAC = "4c:49:6c:d4:db:a9"

def parse_log_file(filepath):
    """Parse a log file and extract timestamp and channel for target MAC address."""
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
        
        # Look for the target MAC address and extract channel info
        # Pattern: MAC address followed by BSSID, then band/chan/ch-width/ht-type
        mac_pattern = rf'{TARGET_MAC}\s+\S+\s+5GHz/(\d+E?)'
        mac_match = re.search(mac_pattern, section, re.IGNORECASE)
        
        if mac_match and current_time:
            channel = mac_match.group(1)
            data.append((current_time, channel))
            print(f"  Found {TARGET_MAC} at {current_time} on channel {channel}")
    
    print(f"  Successfully parsed {len(data)} data points for MAC {TARGET_MAC}")
    return data

def scan_and_plot():
    """Scan current directory for text files and plot channel changes."""
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
    
    # Get unique channels and assign numeric values
    unique_channels = sorted(set(ch for _, ch in all_data), key=lambda x: (int(re.search(r'\d+', x).group()), x))
    channel_to_num = {ch: i for i, ch in enumerate(unique_channels)}
    
    # Convert data to numeric values
    timestamps = [d[0] for d in all_data]
    channel_nums = [channel_to_num[d[1]] for d in all_data]
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Plot as step function
    ax.step(timestamps, channel_nums, where='post', linewidth=2.5, 
            color='steelblue', alpha=0.8, zorder=3)
    
    # Add markers at each data point
    colors = plt.cm.Set3(range(len(unique_channels)))
    for i, ch in enumerate(unique_channels):
        ch_data = [(ts, num) for ts, num in zip(timestamps, channel_nums) if num == i]
        if ch_data:
            ch_timestamps = [d[0] for d in ch_data]
            ch_nums = [d[1] for d in ch_data]
            ax.scatter(ch_timestamps, ch_nums, color=colors[i], s=80, 
                      label=f'Channel {ch}', alpha=0.9, edgecolors='black', 
                      linewidth=0.5, zorder=5)
    
    # Formatting
    ax.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax.set_ylabel('Channel', fontsize=12, fontweight='bold')
    ax.set_title(f'Channel Timeline for MAC {TARGET_MAC}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--', axis='both')
    ax.legend(loc='upper left', fontsize=9, ncol=2)
    
    # Set y-axis to show channel labels
    ax.set_yticks(range(len(unique_channels)))
    ax.set_yticklabels(unique_channels)
    ax.set_ylim(-0.5, len(unique_channels) - 0.5)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45, ha='right')
    
    # Add start and end time annotations
    start_time = min(timestamps).strftime('%Y-%m-%d %H:%M:%S')
    end_time = max(timestamps).strftime('%Y-%m-%d %H:%M:%S')
    
    plt.tight_layout()
    
    # Save the plot
    output_file = f'mac_{TARGET_MAC.replace(":", "")}_channel_timeline.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved as: {output_file}")
    
    # Show summary
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Target MAC: {TARGET_MAC}")
    print(f"  Files checked: {len(files_checked)}")
    print(f"  Total data points: {len(all_data)}")
    print(f"  Time range: {start_time} to {end_time}")
    
    # Channel distribution
    channel_counts = {}
    for _, ch in all_data:
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
    print(f"  Channel distribution:")
    for ch in unique_channels:
        count = channel_counts.get(ch, 0)
        percentage = (count / len(all_data)) * 100
        print(f"    {ch}: {count} occurrences ({percentage:.1f}%)")
    
    # Detect channel transitions
    transitions = []
    for i in range(1, len(all_data)):
        if all_data[i][1] != all_data[i-1][1]:
            transitions.append((all_data[i-1][0], all_data[i-1][1], all_data[i][0], all_data[i][1]))
    
    if transitions:
        print(f"  Channel transitions detected: {len(transitions)}")
        print(f"  First few transitions:")
        for i, (t1, ch1, t2, ch2) in enumerate(transitions[:5]):
            print(f"    {t1.strftime('%H:%M:%S')} ({ch1}) → {t2.strftime('%H:%M:%S')} ({ch2})")
        if len(transitions) > 5:
            print(f"    ... and {len(transitions) - 5} more")
    
    print(f"{'='*50}")
    
    plt.show()

if __name__ == "__main__":
    scan_and_plot()