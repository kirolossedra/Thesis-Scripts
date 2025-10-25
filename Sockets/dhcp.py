
import socket
import struct
import random
import time

class DHCPServer:
    def __init__(self, server_ip='192.168.0.1', subnet='192.168.0.0/24', lease_duration=86400):
        self.server_ip = server_ip
        self.subnet = subnet
        self.lease_duration = lease_duration
        self.ip_pool = self._generate_ip_pool()
        self.leased_ips = {}
        
        # Static MAC to IP mappings (reservations)
        self.static_mappings = {
            (0x42, 0x79, 0x99, 0xbb, 0x69, 0x6f): '192.168.0.33',  # 42:79:99:bb:69:6f
        }
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('', 67))

    def _generate_ip_pool(self):
        # Generate IP pool for 192.168.0.100 to 192.168.0.200
        return [f'192.168.0.{i}' for i in range(100, 201)]

    def _parse_dhcp_packet(self, data):
        # Parse DHCP packet
        op = data[0]
        htype = data[1]
        hlen = data[2]
        hops = data[3]
        xid = data[4:8]
        secs = struct.unpack('!H', data[8:10])[0]
        flags = struct.unpack('!H', data[10:12])[0]
        ciaddr = data[12:16]
        yiaddr = data[16:20]
        siaddr = data[20:24]
        giaddr = data[24:28]
        chaddr = data[28:44]  # Full 16 bytes for chaddr
        sname = data[44:108]
        file = data[108:236]
        
        # Check for DHCP magic cookie
        if len(data) > 236 and data[236:240] == bytes([99, 130, 83, 99]):
            options = data[240:]
        else:
            options = b''
        
        # Parse DHCP options
        dhcp_message_type = None
        requested_ip = None
        hostname = None
        i = 0
        while i < len(options):
            if i >= len(options):
                break
            opt_code = options[i]
            if opt_code == 255:  # End option
                break
            if opt_code == 0:  # Pad option
                i += 1
                continue
            if i + 1 >= len(options):
                break
            opt_len = options[i + 1]
            if i + 2 + opt_len > len(options):
                break
            if opt_code == 53:  # DHCP Message Type
                dhcp_message_type = options[i + 2]
            elif opt_code == 50:  # Requested IP Address
                requested_ip = socket.inet_ntoa(options[i + 2:i + 2 + opt_len])
            elif opt_code == 12:  # Host Name
                hostname = options[i + 2:i + 2 + opt_len].decode('ascii', errors='ignore')
            i += 2 + opt_len
        
        return {
            'op': op,
            'htype': htype,
            'hlen': hlen,
            'hops': hops,
            'xid': xid,
            'secs': secs,
            'flags': flags,
            'ciaddr': socket.inet_ntoa(ciaddr),
            'yiaddr': socket.inet_ntoa(yiaddr),
            'siaddr': socket.inet_ntoa(siaddr),
            'giaddr': socket.inet_ntoa(giaddr),
            'chaddr': chaddr,
            'sname': sname,
            'file': file,
            'message_type': dhcp_message_type,
            'requested_ip': requested_ip,
            'hostname': hostname
        }

    def _log_dhcp_request(self, packet, addr):
        # Log detailed debug information about DHCP request
        print("\n=== DHCP Request Received ===")
        print(f"Source Address: {addr[0]}:{addr[1]}")
        print(f"Operation: {packet['op']} ({'BOOTREQUEST' if packet['op'] == 1 else 'BOOTREPLY'})")
        print(f"Transaction ID: {packet['xid'].hex()}")
        mac_bytes = packet['chaddr'][:6]
        print(f"Client MAC: {':'.join([f'{b:02x}' for b in mac_bytes])}")
        msg_types = {1: 'Discover', 2: 'Offer', 3: 'Request', 4: 'Decline', 5: 'ACK', 6: 'NAK', 7: 'Release', 8: 'Inform'}
        print(f"Message Type: {packet['message_type']} ({msg_types.get(packet['message_type'], 'Unknown')})")
        print(f"Client IP: {packet['ciaddr']}")
        print(f"Your IP: {packet['yiaddr']}")
        print(f"Server IP: {packet['siaddr']}")
        print(f"Gateway IP: {packet['giaddr']}")
        print(f"Seconds Elapsed: {packet['secs']}")
        print(f"Flags: {packet['flags']:04x} ({'Broadcast' if packet['flags'] & 0x8000 else 'Unicast'})")
        if packet['requested_ip']:
            print(f"Requested IP: {packet['requested_ip']}")
        if packet['hostname']:
            print(f"Client Hostname: {packet['hostname']}")
        print("========================\n")

    def _create_dhcp_packet(self, packet, message_type, offered_ip):
        """Create a properly formatted DHCP response packet"""
        # Create packet with proper size (minimum 300 bytes for DHCP)
        response = bytearray(576)  # Standard DHCP packet size
        
        # BOOTP header
        response[0] = 2  # op: BOOTREPLY
        response[1] = packet['htype']  # htype: same as request
        response[2] = packet['hlen']  # hlen: same as request
        response[3] = 0  # hops
        response[4:8] = packet['xid']  # xid: must match request
        response[8:10] = struct.pack('!H', 0)  # secs
        response[10:12] = struct.pack('!H', packet['flags'])  # flags: copy from request
        response[12:16] = socket.inet_aton('0.0.0.0')  # ciaddr
        response[16:20] = socket.inet_aton(offered_ip)  # yiaddr: offered IP
        response[20:24] = socket.inet_aton(self.server_ip)  # siaddr: server IP
        response[24:28] = socket.inet_aton('0.0.0.0')  # giaddr
        response[28:44] = packet['chaddr']  # chaddr: client hardware address (16 bytes)
        response[44:108] = packet['sname']  # sname: server host name (64 bytes)
        response[108:236] = packet['file']  # file: boot file name (128 bytes)
        
        # Magic cookie
        response[236:240] = bytes([99, 130, 83, 99])
        
        # DHCP options
        idx = 240
        
        # Option 53: DHCP Message Type
        response[idx:idx+3] = bytes([53, 1, message_type])
        idx += 3
        
        # Option 54: Server Identifier (REQUIRED)
        response[idx:idx+6] = bytes([54, 4]) + socket.inet_aton(self.server_ip)
        idx += 6
        
        # Option 51: IP Address Lease Time
        response[idx:idx+6] = bytes([51, 4]) + struct.pack('!I', self.lease_duration)
        idx += 6
        
        # Option 1: Subnet Mask
        response[idx:idx+6] = bytes([1, 4]) + socket.inet_aton('255.255.255.0')
        idx += 6
        
        # Option 3: Router
        response[idx:idx+6] = bytes([3, 4]) + socket.inet_aton(self.server_ip)
        idx += 6
        
        # Option 6: Domain Name Server
        response[idx:idx+6] = bytes([6, 4]) + socket.inet_aton('8.8.8.8')
        idx += 6
        
        # Option 255: End
        response[idx] = 255
        idx += 1
        
        # Trim to actual size
        return bytes(response[:idx])

    def _create_dhcp_offer(self, packet, offered_ip):
        mac_bytes = packet['chaddr'][:6]
        print(f"Sending DHCP Offer for IP {offered_ip} to {':'.join([f'{b:02x}' for b in mac_bytes])}")
        return self._create_dhcp_packet(packet, 2, offered_ip)  # Message type 2 = OFFER

    def _create_dhcp_ack(self, packet, assigned_ip):
        mac_bytes = packet['chaddr'][:6]
        print(f"Sending DHCP ACK for IP {assigned_ip} to {':'.join([f'{b:02x}' for b in mac_bytes])}")
        return self._create_dhcp_packet(packet, 5, assigned_ip)  # Message type 5 = ACK

    def _get_broadcast_address(self, packet):
        """Determine broadcast address based on flags"""
        # If broadcast flag is set or ciaddr is 0.0.0.0, use broadcast
        if packet['flags'] & 0x8000 or packet['ciaddr'] == '0.0.0.0':
            return ('255.255.255.255', 68)
        else:
            # Could use ciaddr for unicast, but broadcast is safer
            return ('255.255.255.255', 68)

    def run(self):
        print(f"DHCP Server running on {self.server_ip}...")
        print(f"Listening on port 67")
        print(f"IP Pool: {self.ip_pool[0]} - {self.ip_pool[-1]}")
        print(f"Lease Duration: {self.lease_duration} seconds")
        
        # Display static mappings
        if self.static_mappings:
            print("\n📌 Static MAC-to-IP Reservations:")
            for mac, ip in self.static_mappings.items():
                mac_str = ':'.join([f'{b:02x}' for b in mac])
                print(f"  {mac_str} -> {ip}")
        print()
        
        while True:
            try:
                data, addr = self.server_socket.recvfrom(2048)
                packet = self._parse_dhcp_packet(data)
                
                if packet['message_type'] is None:
                    print(f"Received non-DHCP packet from {addr}")
                    continue
                
                self._log_dhcp_request(packet, addr)
                
                mac_tuple = tuple(packet['chaddr'][:6])
                
                if packet['message_type'] == 1:  # DHCP Discover
                    # Check for static mapping first
                    if mac_tuple in self.static_mappings:
                        offered_ip = self.static_mappings[mac_tuple]
                        print(f"⚡ Static mapping found: {':'.join([f'{b:02x}' for b in mac_tuple])} -> {offered_ip}")
                    else:
                        # Check if this MAC already has a lease
                        existing_ip = None
                        for ip, (mac, expiry) in list(self.leased_ips.items()):
                            if mac == mac_tuple and time.time() < expiry:
                                existing_ip = ip
                                break
                        
                        if existing_ip:
                            offered_ip = existing_ip
                            print(f"Offering existing lease: {offered_ip}")
                        else:
                            # Select an available IP
                            available_ips = [ip for ip in self.ip_pool 
                                           if ip not in self.leased_ips or 
                                           time.time() >= self.leased_ips[ip][1]]
                            
                            if available_ips:
                                offered_ip = random.choice(available_ips)
                                print(f"Offering new IP: {offered_ip}")
                            else:
                                print("No available IPs in pool")
                                continue
                    
                    response = self._create_dhcp_offer(packet, offered_ip)
                    dest = self._get_broadcast_address(packet)
                    self.server_socket.sendto(response, dest)
                
                elif packet['message_type'] == 3:  # DHCP Request
                    # Get requested IP
                    requested_ip = packet['requested_ip']
                    if not requested_ip or requested_ip == '0.0.0.0':
                        requested_ip = packet['ciaddr']
                    
                    print(f"Client requesting IP: {requested_ip}")
                    
                    # Check for static mapping
                    if mac_tuple in self.static_mappings:
                        static_ip = self.static_mappings[mac_tuple]
                        if requested_ip != static_ip:
                            print(f"⚠ Client requested {requested_ip} but static mapping requires {static_ip}")
                            requested_ip = static_ip
                    
                    # Check if IP is valid and available
                    if requested_ip in self.ip_pool or requested_ip in self.static_mappings.values():
                        # Check if already leased to another MAC
                        if requested_ip in self.leased_ips:
                            existing_mac, expiry = self.leased_ips[requested_ip]
                            if existing_mac != mac_tuple and time.time() < expiry:
                                print(f"IP {requested_ip} already leased to another client")
                                continue
                        
                        # Assign the IP
                        self.leased_ips[requested_ip] = (mac_tuple, time.time() + self.lease_duration)
                        response = self._create_dhcp_ack(packet, requested_ip)
                        dest = self._get_broadcast_address(packet)
                        self.server_socket.sendto(response, dest)
                        
                        if mac_tuple in self.static_mappings:
                            print(f"✓ Static lease granted: {requested_ip} -> {':'.join([f'{b:02x}' for b in mac_tuple])}")
                        else:
                            print(f"✓ Lease granted: {requested_ip} -> {':'.join([f'{b:02x}' for b in mac_tuple])}")
                    else:
                        print(f"Requested IP {requested_ip} not in pool or invalid")
                
                elif packet['message_type'] == 7:  # DHCP Release
                    released_ip = packet['ciaddr']
                    if released_ip in self.leased_ips:
                        del self.leased_ips[released_ip]
                        print(f"Released IP: {released_ip}")
                        
            except Exception as e:
                print(f"Error processing packet: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    server = DHCPServer()
    server.run()
