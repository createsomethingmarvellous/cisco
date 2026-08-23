"""
config_parser.py
Cleans and parses Cisco show-command outputs into structured dictionaries.
Purpose: Pre-filter raw text, extract key fields, validate data integrity.
"""

import re
from typing import Dict, List, Any, Optional


class PacketTracerCleaner:
    """Advanced preprocessor for raw Packet Tracer CLI outputs and logs."""
    
    INTERFACE_MAP = {
        r'\bGi(\d+/\d+(?:/\d+)?)\b': r'GigabitEthernet\1',
        r'\bFa(\d+/\d+)\b': r'FastEthernet\1',
        r'\bSe(\d+/\d+/\d+)\b': r'Serial\1',
        r'\bTe(\d+/\d+)\b': r'TenGigabitEthernet\1',
        r'\bPo(\d+)\b': r'Port-channel\1'
    }

    @classmethod
    def clean_raw_config(cls, raw_text: str) -> str:
        """Strip boilerplate headers, empty comment lines, and cryptographic keys."""
        if not raw_text:
            return ""
        lines = raw_text.split('\n')
        cleaned_lines = []
        skip_block = False
        
        for line in lines:
            stripped = line.strip()
            # Skip boilerplate headers
            if stripped.startswith('Building configuration...') or stripped.startswith('Current configuration :'):
                continue
            if stripped.startswith('crypto pki') or stripped.startswith('certificate self-signed'):
                skip_block = True
                continue
            if skip_block and stripped == 'quit':
                skip_block = False
                continue
            if skip_block or stripped == '!':
                continue
            cleaned_lines.append(line)
            
        return '\n'.join(cleaned_lines)

    @classmethod
    def normalize_interface_names(cls, text: str) -> str:
        """Standardize abbreviated interface names (e.g. Fa0/1 -> FastEthernet0/1)."""
        normalized = text
        for pattern, replacement in cls.INTERFACE_MAP.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        return normalized

    @classmethod
    def extract_syslog_anomalies(cls, log_text: str) -> List[str]:
        """Extract high-severity Cisco syslog events (%LINK, %LINEPROTO, %OSPF, %STP)."""
        anomalies = []
        if not log_text:
            return anomalies
        
        patterns = [
            r'%\w+-\d+-\w+:[^\n]+',  # Standard Cisco Syslog format %FACILITY-SEVERITY-MNEMONIC: message
            r'duplicate ip[^\n]+',
            r'native vlan mismatch[^\n]+',
            r'bpdu guard[^\n]+'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, log_text, flags=re.IGNORECASE)
            for m in matches:
                if m.strip() not in anomalies:
                    anomalies.append(m.strip())
        return anomalies

    @classmethod
    def preprocess_for_prompt(cls, raw_output: str) -> Dict[str, Any]:
        """Clean noise, normalize interface names, and extract anomalies for prompt injection."""
        cleaned = cls.clean_raw_config(raw_output)
        normalized = cls.normalize_interface_names(cleaned)
        anomalies = cls.extract_syslog_anomalies(raw_output)
        
        return {
            'cleaned_output': normalized,
            'anomalies': anomalies,
            'original_length': len(raw_output),
            'cleaned_length': len(normalized)
        }


class MultiDeviceIOSParser:
    """Parses multi-device Packet Tracer configuration text blocks."""

    @classmethod
    def split_devices(cls, raw_text: str) -> Dict[str, str]:
        """Split a multi-device config dump into per-device raw blocks."""
        devices = {}
        current_device = "DEFAULT"
        current_lines = []

        lines = raw_text.split('\n')
        for line in lines:
            # Detect device header tag e.g. "Device: R1", "hostname SW1", "=== R1 ==="
            device_match = re.search(r'(?:Device:\s*|hostname\s+|===\s*)([A-Za-z0-9_\-]+)', line, re.IGNORECASE)
            if device_match and not line.strip().startswith('!'):
                dev_name = device_match.group(1).upper()
                if dev_name not in ['BUILDING', 'CURRENT', 'IOS', 'CISCO']:
                    if current_lines and current_device != "DEFAULT":
                        devices[current_device] = '\n'.join(current_lines)
                        current_lines = []
                    current_device = dev_name

            current_lines.append(line)

        if current_lines:
            devices[current_device] = '\n'.join(current_lines)

        return devices if len(devices) > 1 or "DEFAULT" not in devices else {"R1": raw_text}

    @classmethod
    def parse_all_devices(cls, raw_text: str) -> Dict[str, Dict[str, Any]]:
        """Parse structured config dicts for every device in the topology."""
        device_blocks = cls.split_devices(raw_text)
        parsed_topology = {}

        parser = CiscoConfigParser()
        for dev_name, block in device_blocks.items():
            cleaned = PacketTracerCleaner.clean_raw_config(block)
            normalized = PacketTracerCleaner.normalize_interface_names(cleaned)

            parsed_topology[dev_name] = {
                'raw_block': block,
                'cleaned_block': normalized,
                'vlans': parser.parse_show_vlan(normalized),
                'routes': parser.parse_show_ip_route(normalized),
                'interfaces': parser.parse_show_interfaces(normalized),
                'acls': parser.parse_show_access_lists(normalized),
                'dhcp_bindings': parser.parse_show_ip_dhcp_binding(normalized),
                'anomalies': PacketTracerCleaner.extract_syslog_anomalies(block)
            }

        return parsed_topology


class CiscoConfigParser:
    """Parse Cisco show-command outputs into structured data."""
    
    @staticmethod
    def parse_show_vlan(output: str) -> Dict[str, Any]:
        """Parse 'show vlan brief' output."""
        vlans = {}
        lines = output.strip().split('\n')
        for line in lines[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 2:
                try:
                    vlan_id = int(parts[0])
                    name = parts[1]
                    status = parts[2] if len(parts) > 2 else 'unknown'
                    vlans[vlan_id] = {'name': name, 'status': status}
                except ValueError:
                    continue
        return vlans
    
    @staticmethod
    def parse_show_ip_route(output: str) -> Dict[str, Any]:
        """Parse 'show ip route' output."""
        routes = {}
        lines = output.strip().split('\n')
        for line in lines:
            # Look for destination/mask patterns
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)/(\d+).*via\s+(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                dest, mask, next_hop = match.groups()
                routes[f"{dest}/{mask}"] = {'next_hop': next_hop, 'raw': line}
        return routes
    
    @staticmethod
    def parse_show_interfaces(output: str) -> Dict[str, Any]:
        """Parse 'show interfaces' output."""
        interfaces = {}
        current_iface = None
        lines = output.strip().split('\n')
        
        for line in lines:
            # Detect interface line (e.g., "FastEthernet0/0 is up, line protocol is up")
            iface_match = re.match(r'^(\S+)\s+is\s+(\w+)', line)
            if iface_match:
                current_iface = iface_match.group(1)
                status = iface_match.group(2)
                interfaces[current_iface] = {
                    'status': status,
                    'ip': None,
                    'vlan': None,
                    'encapsulation': None,
                    'errors': 0
                }
            elif current_iface and 'Internet address is' in line:
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)/(\d+)', line)
                if ip_match:
                    interfaces[current_iface]['ip'] = ip_match.group(1)
                    interfaces[current_iface]['mask'] = ip_match.group(2)
            elif current_iface and 'Encapsulation' in line:
                enc_match = re.search(r'Encapsulation (\S+)', line)
                if enc_match:
                    interfaces[current_iface]['encapsulation'] = enc_match.group(1)
            elif current_iface and ('errors' in line or 'dropped' in line):
                # Extract error counts
                error_match = re.search(r'(\d+)\s+errors', line)
                if error_match:
                    interfaces[current_iface]['errors'] = int(error_match.group(1))
        
        return interfaces
    
    @staticmethod
    def parse_show_access_lists(output: str) -> Dict[str, List[Dict[str, str]]]:
        """Parse 'show access-lists' output."""
        acls = {}
        current_acl = None
        lines = output.strip().split('\n')
        
        for line in lines:
            # Detect ACL line (e.g., "Standard IP access list 101")
            acl_match = re.match(r'(Standard|Extended|Named) IP access list (\d+|\w+)', line)
            if acl_match:
                current_acl = acl_match.group(2)
                acls[current_acl] = []
            elif current_acl and (line.strip().startswith('permit') or line.strip().startswith('deny')):
                acls[current_acl].append({'rule': line.strip()})
        
        return acls
    
    @staticmethod
    def parse_show_ip_dhcp_binding(output: str) -> Dict[str, Any]:
        """Parse 'show ip dhcp binding' output."""
        bindings = {}
        lines = output.strip().split('\n')
        for line in lines[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 3:
                ip = parts[0]
                mac = parts[1]
                state = parts[2]
                bindings[ip] = {'mac': mac, 'state': state}
        return bindings
    
    @staticmethod
    def validate_ip_format(ip: str) -> bool:
        """Check if IP is valid format."""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        return all(0 <= int(p) <= 255 for p in parts if p.isdigit())
    
    @staticmethod
    def validate_no_duplicate_ips(bindings: Dict[str, Any]) -> List[str]:
        """Check for duplicate IP addresses in DHCP bindings."""
        duplicates = []
        ip_counts = {}
        for ip in bindings.keys():
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        duplicates = [ip for ip, count in ip_counts.items() if count > 1]
        return duplicates
    
    @staticmethod
    def extract_vlan_from_interface(iface_config: str) -> Optional[int]:
        """Extract VLAN ID from interface config output."""
        match = re.search(r'switchport access vlan (\d+)', iface_config)
        if match:
            return int(match.group(1))
        return None
    
    @staticmethod
    def extract_gateway_from_dhcp_config(dhcp_config: str) -> Optional[str]:
        """Extract default gateway from DHCP pool config."""
        match = re.search(r'default-gateway\s+(\d+\.\d+\.\d+\.\d+)', dhcp_config)
        if match:
            return match.group(1)
        return None


class ConfigAnalyzer:
    """Analyze parsed configs for common issues."""
    
    def __init__(self, parser: CiscoConfigParser):
        self.parser = parser
    
    def check_subnet_mask_consistency(self, interfaces: Dict[str, Any]) -> List[str]:
        """Find devices claiming same subnet with different masks."""
        subnets = {}
        issues = []
        for iface, config in interfaces.items():
            if config.get('ip') and config.get('mask'):
                subnet = f"{config['ip']}/{config['mask']}"
                if subnet not in subnets:
                    subnets[subnet] = []
                subnets[subnet].append(iface)
        
        # Check for overlaps (simplified; real implementation would compute CIDR)
        for subnet, ifaces in subnets.items():
            if len(ifaces) > 1:
                issues.append(f"Subnet {subnet} on multiple interfaces: {ifaces}")
        
        return issues
    
    def check_interface_errors(self, interfaces: Dict[str, Any]) -> List[str]:
        """Flag interfaces with errors or down status."""
        issues = []
        for iface, config in interfaces.items():
            if config.get('status') == 'down':
                issues.append(f"Interface {iface} is DOWN")
            if config.get('errors', 0) > 10:
                issues.append(f"Interface {iface} has {config['errors']} errors")
        return issues
    
    def check_missing_routes(self, routes: Dict[str, Any], expected_subnets: List[str]) -> List[str]:
        """Check if expected routes exist."""
        issues = []
        existing_routes = set(routes.keys())
        for expected in expected_subnets:
            if expected not in existing_routes:
                issues.append(f"Missing route: {expected}")
        return issues


if __name__ == '__main__':
    # Example usage
    parser = CiscoConfigParser()
    
    # Test IP format validation
    assert parser.validate_ip_format('192.168.1.1') == True
    assert parser.validate_ip_format('256.1.1.1') == False
    
    print("Config parser initialized and validated.")
