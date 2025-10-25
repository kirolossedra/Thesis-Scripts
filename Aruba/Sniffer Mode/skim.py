import os
import re
from datetime import datetime

TARGET_MAC = "4c:49:6c:d4:db:a9"

def parse_and_filter_log(filepath, output_filepath):
    """Parse a log file and extract only entries with the target MAC address."""
    filtered_entries = []
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split by the delimiter
    sections = content.split('/////')
    
    print(f"  Total sections found: {len(sections)}")
    
    # Process sections
    current_time = None
    current_time_str = None
    entries_found = 0
    
    for i, section in enumerate(sections):
        # Look for LocalBeginTime
        time_match = re.search(r'LocalBeginTime:\s*(\d+)\s*\(([^)]+)\)', section)
        
        if time_match:
            current_time_str = time_match.group(2)
            try:
                time_clean = current_time_str.split('.')[0]
                current_time = datetime.strptime(time_clean, '%Y-%m-%dT%H:%M:%S')
            except Exception as e:
                print(f"  Warning: couldn't parse timestamp '{current_time_str}': {e}")
                current_time = None
        
        # Look for lines containing the target MAC address
        lines = section.split('\n')
        for line in lines:
            if TARGET_MAC.lower() in line.lower():
                entries_found += 1
                
                # Extract all information from the line
                # The line format is space-separated with the following columns:
                # mac bssid band/chan/ch-width/ht-type essid sta-type auth dt/mt ut/it snr rssi cl-delay snr/rssi-age report-age
                parts = line.split()
                
                if len(parts) >= 11:  # Ensure we have enough columns
                    entry_data = {
                        'timestamp': current_time_str if current_time_str else 'Unknown',
                        'mac': parts[0] if len(parts) > 0 else '',
                        'bssid': parts[1] if len(parts) > 1 else '',
                        'band_channel': parts[2] if len(parts) > 2 else '',
                        'essid': parts[3] if len(parts) > 3 else '',
                        'sta_type': parts[4] if len(parts) > 4 else '',
                        'auth': parts[5] if len(parts) > 5 else '',
                        'dt_mt': parts[6] if len(parts) > 6 else '',
                        'ut_it': parts[7] if len(parts) > 7 else '',
                        'snr': parts[8] if len(parts) > 8 else '',
                        'rssi': parts[9] if len(parts) > 9 else '',
                        'cl_delay': parts[10] if len(parts) > 10 else '',
                        'snr_rssi_age': parts[11] if len(parts) > 11 else '',
                        'report_age': parts[12] if len(parts) > 12 else '',
                        'full_line': line.strip()
                    }
                    filtered_entries.append(entry_data)
                    print(f"  Found entry at {current_time_str}")
    
    print(f"  Total entries found for MAC {TARGET_MAC}: {entries_found}")
    
    # Write filtered data to output file
    if filtered_entries:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            # Write header
            f.write("="*100 + "\n")
            f.write(f"FILTERED LOG DATA FOR MAC ADDRESS: {TARGET_MAC}\n")
            f.write(f"Total entries found: {len(filtered_entries)}\n")
            f.write(f"Source file: {filepath}\n")
            f.write("="*100 + "\n\n")
            
            # Write column headers
            f.write(f"{'Timestamp':<30} {'MAC':<20} {'BSSID':<20} {'Channel':<15} {'ESSID':<20} "
                   f"{'Type':<12} {'Auth':<6} {'SNR':<5} {'RSSI':<5}\n")
            f.write("-"*150 + "\n")
            
            # Write each entry
            for entry in filtered_entries:
                # Extract channel from band_channel (e.g., "5GHz/36E/80MHz/HE" -> "36E")
                channel = ''
                if '/' in entry['band_channel']:
                    parts = entry['band_channel'].split('/')
                    if len(parts) > 1:
                        channel = parts[1]
                
                f.write(f"{entry['timestamp']:<30} {entry['mac']:<20} {entry['bssid']:<20} "
                       f"{channel:<15} {entry['essid']:<20} {entry['sta_type']:<12} "
                       f"{entry['auth']:<6} {entry['snr']:<5} {entry['rssi']:<5}\n")
            
            # Write detailed section
            f.write("\n" + "="*100 + "\n")
            f.write("DETAILED INFORMATION\n")
            f.write("="*100 + "\n\n")
            
            for i, entry in enumerate(filtered_entries, 1):
                f.write(f"Entry #{i}\n")
                f.write(f"  Timestamp:        {entry['timestamp']}\n")
                f.write(f"  MAC Address:      {entry['mac']}\n")
                f.write(f"  BSSID:            {entry['bssid']}\n")
                f.write(f"  Band/Channel:     {entry['band_channel']}\n")
                f.write(f"  ESSID:            {entry['essid']}\n")
                f.write(f"  Station Type:     {entry['sta_type']}\n")
                f.write(f"  Auth:             {entry['auth']}\n")
                f.write(f"  DT/MT:            {entry['dt_mt']}\n")
                f.write(f"  UT/IT:            {entry['ut_it']}\n")
                f.write(f"  SNR:              {entry['snr']} dB\n")
                f.write(f"  RSSI:             {entry['rssi']} dBm\n")
                f.write(f"  CL Delay:         {entry['cl_delay']}\n")
                f.write(f"  SNR/RSSI Age:     {entry['snr_rssi_age']}\n")
                f.write(f"  Report Age:       {entry['report_age']}\n")
                f.write(f"  Full Line:        {entry['full_line']}\n")
                f.write("-"*100 + "\n\n")
            
            # Write statistics
            f.write("="*100 + "\n")
            f.write("STATISTICS\n")
            f.write("="*100 + "\n\n")
            
            # Count unique values
            unique_bssids = set(e['bssid'] for e in filtered_entries if e['bssid'])
            unique_channels = set(e['band_channel'].split('/')[1] if '/' in e['band_channel'] else '' 
                                 for e in filtered_entries if e['band_channel'])
            unique_essids = set(e['essid'] for e in filtered_entries if e['essid'])
            
            f.write(f"Unique BSSIDs: {len(unique_bssids)}\n")
            for bssid in sorted(unique_bssids):
                count = sum(1 for e in filtered_entries if e['bssid'] == bssid)
                f.write(f"  {bssid}: {count} occurrences\n")
            
            f.write(f"\nUnique Channels: {len(unique_channels)}\n")
            for channel in sorted(unique_channels):
                count = sum(1 for e in filtered_entries if '/' in e['band_channel'] 
                           and e['band_channel'].split('/')[1] == channel)
                f.write(f"  {channel}: {count} occurrences\n")
            
            f.write(f"\nUnique ESSIDs: {len(unique_essids)}\n")
            for essid in sorted(unique_essids):
                count = sum(1 for e in filtered_entries if e['essid'] == essid)
                f.write(f"  {essid}: {count} occurrences\n")
            
            # RSSI/SNR statistics
            rssi_values = [int(e['rssi']) for e in filtered_entries if e['rssi'].isdigit()]
            snr_values = [int(e['snr']) for e in filtered_entries if e['snr'].isdigit()]
            
            if rssi_values:
                f.write(f"\nRSSI Statistics:\n")
                f.write(f"  Min: {min(rssi_values)} dBm\n")
                f.write(f"  Max: {max(rssi_values)} dBm\n")
                f.write(f"  Average: {sum(rssi_values)/len(rssi_values):.1f} dBm\n")
            
            if snr_values:
                f.write(f"\nSNR Statistics:\n")
                f.write(f"  Min: {min(snr_values)} dB\n")
                f.write(f"  Max: {max(snr_values)} dB\n")
                f.write(f"  Average: {sum(snr_values)/len(snr_values):.1f} dB\n")
    
    return len(filtered_entries)

def scan_and_filter():
    """Scan current directory for text files and filter data."""
    files_checked = []
    total_entries = 0
    
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
        
        # Create output filename
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_filtered_{TARGET_MAC.replace(':', '')}.txt"
        
        try:
            entries_count = parse_and_filter_log(filename, output_filename)
            if entries_count > 0:
                total_entries += entries_count
                print(f"  ✓ Filtered data saved to: {output_filename}")
                print(f"  ✓ Found {entries_count} entries")
                break  # Stop after finding first file with data
            else:
                print(f"  ✗ No entries for MAC {TARGET_MAC} found")
                # Remove empty output file
                if os.path.exists(output_filename):
                    os.remove(output_filename)
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    if total_entries == 0:
        print("\n" + "="*50)
        print("NO DATA FOUND!")
        print(f"Checked {len(files_checked)} files, none had data for MAC {TARGET_MAC}")
        print("="*50)
    else:
        print("\n" + "="*50)
        print(f"FILTERING COMPLETE!")
        print(f"Total entries extracted: {total_entries}")
        print("="*50)

if __name__ == "__main__":
    scan_and_filter()