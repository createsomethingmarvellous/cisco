"""
rule_checker.py
Deterministic rule-based checks for common Cisco network misconfigurations.
Purpose: Catch obvious issues before AI diagnosis (faster, more deterministic).
Output: List of identified issues with confidence=high for human review.
"""

import re
import ipaddress
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum


class OSILayer(Enum):
    LAYER_2 = "2"
    LAYER_3 = "3"
    LAYER_4 = "4"


class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DiagnosisResult:
    """Structured result of a rule check."""
    
    def __init__(self, rule_name: str, detected: bool, issue: Optional[str], 
                 osi_layer: OSILayer, severity: SeverityLevel, evidence: List[str]):
        self.rule_name = rule_name
        self.detected = detected
        self.issue = issue
        self.osi_layer = osi_layer
        self.severity = severity
        self.evidence = evidence  # quoted lines from show outputs
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule': self.rule_name,
            'detected': self.detected,
            'issue': self.issue,
            'osi_layer': self.osi_layer.value,
            'severity': self.severity.value,
            'evidence': self.evidence
        }


class MultiDeviceCrossChecker:
    """Performs deterministic cross-device validation across multi-device Packet Tracer topologies."""

    @classmethod
    def check_topology(cls, parsed_topology: Dict[str, Dict[str, Any]]) -> List[DiagnosisResult]:
        results = []

        # Rule 1: Check Interface Shutdown State across all devices
        for dev_name, data in parsed_topology.items():
            raw_block = data.get('cleaned_block', '')
            # Parse interfaces with explicit shutdown in config block
            shutdown_ifaces = re.findall(r'interface\s+([A-Za-z0-9/\.]+)(?:(?!interface)[\s\S])*?\n\s+shutdown', raw_block, re.IGNORECASE)
            for iface_name in shutdown_ifaces:
                results.append(DiagnosisResult(
                    rule_name=f"interface_down_{dev_name}",
                    detected=True,
                    issue=f"Device {dev_name} interface {iface_name} is administratively SHUTDOWN",
                    osi_layer=OSILayer.LAYER_2,
                    severity=SeverityLevel.HIGH,
                    evidence=[f"{dev_name} interface {iface_name} configuration has 'shutdown' enabled"]
                ))
            
            for iface_name, iface_data in data.get('interfaces', {}).items():
                if iface_data.get('status') == 'down' and iface_name not in shutdown_ifaces:
                    results.append(DiagnosisResult(
                        rule_name=f"interface_down_{dev_name}",
                        detected=True,
                        issue=f"Device {dev_name} interface {iface_name} is DOWN",
                        osi_layer=OSILayer.LAYER_2,
                        severity=SeverityLevel.HIGH,
                        evidence=[f"{dev_name} {iface_name} is down, line protocol is down"]
                    ))

        # Rule 2: Check for Native VLAN Mismatches across switches
        native_vlans = {}
        for dev_name, data in parsed_topology.items():
            raw = data.get('cleaned_block', '')
            match = re.search(r'switchport trunk native vlan (\d+)', raw, re.IGNORECASE)
            if match:
                native_vlans[dev_name] = match.group(1)

        if len(set(native_vlans.values())) > 1:
            mismatches = [f"{dev}: VLAN {v}" for dev, v in native_vlans.items()]
            results.append(DiagnosisResult(
                rule_name="native_vlan_mismatch",
                detected=True,
                issue=f"Native VLAN mismatch detected across trunk peers: {', '.join(mismatches)}",
                osi_layer=OSILayer.LAYER_2,
                severity=SeverityLevel.HIGH,
                evidence=[f"Trunk native VLAN mismatch: {', '.join(mismatches)}"]
            ))

        # Rule 3: Check for ACL Deny Rules
        for dev_name, data in parsed_topology.items():
            for acl_id, rules in data.get('acls', {}).items():
                for rule_dict in rules:
                    r_text = rule_dict.get('rule', '')
                    if 'deny' in r_text.lower():
                        results.append(DiagnosisResult(
                            rule_name=f"acl_deny_rule_{dev_name}",
                            detected=True,
                            issue=f"Device {dev_name} ACL {acl_id} contains active DENY rule: '{r_text}'",
                            osi_layer=OSILayer.LAYER_4,
                            severity=SeverityLevel.MEDIUM,
                            evidence=[f"{dev_name} ACL {acl_id}: {r_text}"]
                        ))

        return results


class RuleChecker:
    """Deterministic checks for common network faults."""
    
    def __init__(self):
        self.results: List[DiagnosisResult] = []
    
    def check_duplicate_ips(self, dhcp_bindings: Dict[str, Dict], static_ips: List[str]) -> DiagnosisResult:
        """Rule 1: Check for duplicate IP addresses."""
        rule_name = "duplicate_ip_check"
        all_ips = list(dhcp_bindings.keys()) + static_ips
        seen = {}
        duplicates = []
        evidence = []
        
        for ip in all_ips:
            if ip in seen:
                duplicates.append(ip)
                evidence.append(f"IP {ip} assigned to multiple devices")
            seen[ip] = True
        
        if duplicates:
            issue = f"Duplicate IPs found: {', '.join(duplicates)}"
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=True,
                issue=issue,
                osi_layer=OSILayer.LAYER_3,
                severity=SeverityLevel.CRITICAL,
                evidence=evidence
            )
        else:
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=False,
                issue=None,
                osi_layer=OSILayer.LAYER_3,
                severity=SeverityLevel.LOW,
                evidence=[]
            )
        
        self.results.append(result)
        return result
    
    def check_interface_down(self, interfaces: Dict[str, Dict]) -> DiagnosisResult:
        """Rule 2: Check for interfaces that are down."""
        rule_name = "interface_down_check"
        down_interfaces = []
        evidence = []
        
        for iface_name, config in interfaces.items():
            status = config.get('status', 'unknown')
            if status.lower() == 'down':
                down_interfaces.append(iface_name)
                evidence.append(f"{iface_name} is down (status: {status})")
        
        if down_interfaces:
            issue = f"Interfaces down: {', '.join(down_interfaces)}"
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=True,
                issue=issue,
                osi_layer=OSILayer.LAYER_2,
                severity=SeverityLevel.HIGH,
                evidence=evidence
            )
        else:
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=False,
                issue=None,
                osi_layer=OSILayer.LAYER_2,
                severity=SeverityLevel.LOW,
                evidence=[]
            )
        
        self.results.append(result)
        return result
    
    def check_subnet_mask_mismatch(self, interfaces: Dict[str, Dict]) -> DiagnosisResult:
        """Rule 3: Check for inconsistent subnet masks on overlapping subnets."""
        rule_name = "subnet_mask_mismatch_check"
        subnets = {}
        mismatches = []
        evidence = []
        
        for iface_name, config in interfaces.items():
            ip = config.get('ip')
            mask = config.get('mask')
            
            if ip and mask:
                try:
                    network = ipaddress.ip_network(f"{ip}/{mask}", strict=False)
                    network_key = str(network)
                    
                    if network_key not in subnets:
                        subnets[network_key] = []
                    subnets[network_key].append((iface_name, mask))
                except ValueError:
                    pass
        
        # Check for same network with different masks
        for network, iface_list in subnets.items():
            masks = set(m for _, m in iface_list)
            if len(masks) > 1:
                ifaces = ', '.join(i for i, _ in iface_list)
                mismatches.append(f"Network {network} on {ifaces} with different masks")
                evidence.append(f"Subnet mask mismatch on {network}: {masks}")
        
        if mismatches:
            issue = '; '.join(mismatches)
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=True,
                issue=issue,
                osi_layer=OSILayer.LAYER_3,
                severity=SeverityLevel.CRITICAL,
                evidence=evidence
            )
        else:
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=False,
                issue=None,
                osi_layer=OSILayer.LAYER_3,
                severity=SeverityLevel.LOW,
                evidence=[]
            )
        
        self.results.append(result)
        return result
    
    def check_gateway_unreachable(self, dhcp_config: Dict, gateway: str, 
                                   routes: Dict[str, Any]) -> DiagnosisResult:
        """Rule 4: Check if DHCP gateway is reachable via routing."""
        rule_name = "gateway_unreachable_check"
        evidence = []
        
        if not gateway or gateway == '0.0.0.0':
            issue = "DHCP gateway not set or invalid"
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=True,
                issue=issue,
                osi_layer=OSILayer.LAYER_3,
                severity=SeverityLevel.HIGH,
                evidence=["DHCP pool missing default-gateway command"]
            )
        else:
            # Check if gateway is in a known route
            gateway_reachable = False
            try:
                gw_addr = ipaddress.ip_address(gateway)
                for route in routes.keys():
                    route_obj = ipaddress.ip_network(route, strict=False)
                    if gw_addr in route_obj:
                        gateway_reachable = True
                        evidence.append(f"Gateway {gateway} reachable via route {route}")
                        break
            except ValueError:
                pass
            
            if not gateway_reachable:
                issue = f"DHCP gateway {gateway} not found in routing table"
                evidence.append(f"Gateway {gateway} not in any known route")
                result = DiagnosisResult(
                    rule_name=rule_name,
                    detected=True,
                    issue=issue,
                    osi_layer=OSILayer.LAYER_3,
                    severity=SeverityLevel.HIGH,
                    evidence=evidence
                )
            else:
                result = DiagnosisResult(
                    rule_name=rule_name,
                    detected=False,
                    issue=None,
                    osi_layer=OSILayer.LAYER_3,
                    severity=SeverityLevel.LOW,
                    evidence=evidence
                )
        
        self.results.append(result)
        return result
    
    def check_missing_vlan_assignment(self, vlans: Dict[int, Dict], 
                                       interfaces: Dict[str, Dict]) -> DiagnosisResult:
        """Rule 5: Check if interface is assigned to a non-existent VLAN."""
        rule_name = "missing_vlan_check"
        missing_vlans = []
        evidence = []
        
        for iface_name, config in interfaces.items():
            vlan_id = config.get('vlan')
            if vlan_id and vlan_id not in vlans:
                missing_vlans.append((iface_name, vlan_id))
                evidence.append(f"Interface {iface_name} assigned to VLAN {vlan_id} (does not exist)")
        
        if missing_vlans:
            issue = f"Interfaces assigned to non-existent VLANs: {missing_vlans}"
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=True,
                issue=issue,
                osi_layer=OSILayer.LAYER_2,
                severity=SeverityLevel.HIGH,
                evidence=evidence
            )
        else:
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=False,
                issue=None,
                osi_layer=OSILayer.LAYER_2,
                severity=SeverityLevel.LOW,
                evidence=[]
            )
        
        self.results.append(result)
        return result
    
    def check_missing_routes(self, routes: Dict[str, Any], expected_destinations: List[str]) -> DiagnosisResult:
        """Rule 6: Check for missing critical routes."""
        rule_name = "missing_route_check"
        missing_routes = []
        evidence = []
        
        existing_routes = set(routes.keys())
        for dest in expected_destinations:
            if dest not in existing_routes:
                missing_routes.append(dest)
                evidence.append(f"Expected route {dest} not found in routing table")
        
        if missing_routes:
            issue = f"Missing routes: {', '.join(missing_routes)}"
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=True,
                issue=issue,
                osi_layer=OSILayer.LAYER_3,
                severity=SeverityLevel.HIGH,
                evidence=evidence
            )
        else:
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=False,
                issue=None,
                osi_layer=OSILayer.LAYER_3,
                severity=SeverityLevel.LOW,
                evidence=[]
            )
        
        self.results.append(result)
        return result
    
    def check_portfast_on_trunk(self, interfaces: Dict[str, Dict]) -> DiagnosisResult:
        """Rule 7: Check if PortFast is incorrectly enabled on trunk ports."""
        rule_name = "portfast_on_trunk_check"
        problematic_ports = []
        evidence = []
        
        for iface_name, config in interfaces.items():
            is_trunk = config.get('encapsulation') == 'dot1Q'
            has_portfast = config.get('portfast', False)
            
            if is_trunk and has_portfast:
                problematic_ports.append(iface_name)
                evidence.append(f"Interface {iface_name} has PortFast enabled on trunk")
        
        if problematic_ports:
            issue = f"PortFast incorrectly enabled on trunk ports: {', '.join(problematic_ports)}"
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=True,
                issue=issue,
                osi_layer=OSILayer.LAYER_2,
                severity=SeverityLevel.MEDIUM,
                evidence=evidence
            )
        else:
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=False,
                issue=None,
                osi_layer=OSILayer.LAYER_2,
                severity=SeverityLevel.LOW,
                evidence=[]
            )
        
        self.results.append(result)
        return result
    
    def check_acl_syntax(self, acls: Dict[str, List[Dict]]) -> DiagnosisResult:
        """Rule 8: Check for syntactically invalid ACL rules."""
        rule_name = "acl_syntax_check"
        invalid_rules = []
        evidence = []
        
        for acl_id, rules in acls.items():
            for rule_dict in rules:
                rule_text = rule_dict.get('rule', '')
                # Simple check: valid rules should start with permit/deny
                if not (rule_text.strip().startswith('permit') or rule_text.strip().startswith('deny')):
                    invalid_rules.append((acl_id, rule_text))
                    evidence.append(f"ACL {acl_id}: Invalid syntax in '{rule_text}'")
        
        if invalid_rules:
            issue = f"Invalid ACL syntax found in {len(invalid_rules)} rule(s)"
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=True,
                issue=issue,
                osi_layer=OSILayer.LAYER_4,
                severity=SeverityLevel.MEDIUM,
                evidence=evidence
            )
        else:
            result = DiagnosisResult(
                rule_name=rule_name,
                detected=False,
                issue=None,
                osi_layer=OSILayer.LAYER_4,
                severity=SeverityLevel.LOW,
                evidence=[]
            )
        
        self.results.append(result)
        return result
    
    def run_all_checks(self, config_data: Dict[str, Any]) -> List[DiagnosisResult]:
        """Run all deterministic checks on provided config data."""
        self.results = []
        
        dhcp_bindings = config_data.get('dhcp_bindings', {})
        static_ips = config_data.get('static_ips', [])
        interfaces = config_data.get('interfaces', {})
        vlans = config_data.get('vlans', {})
        routes = config_data.get('routes', {})
        acls = config_data.get('acls', {})
        gateway = config_data.get('gateway', None)
        expected_destinations = config_data.get('expected_destinations', [])
        
        # Run all checks
        self.check_duplicate_ips(dhcp_bindings, static_ips)
        self.check_interface_down(interfaces)
        self.check_subnet_mask_mismatch(interfaces)
        self.check_gateway_unreachable(config_data, gateway, routes)
        self.check_missing_vlan_assignment(vlans, interfaces)
        self.check_missing_routes(routes, expected_destinations)
        self.check_portfast_on_trunk(interfaces)
        self.check_acl_syntax(acls)
        
        return self.results
    
    def get_detected_issues(self) -> List[DiagnosisResult]:
        """Return only results where issues were detected."""
        return [r for r in self.results if r.detected]
    
    def get_highest_severity(self) -> Optional[SeverityLevel]:
        """Return the highest severity level found."""
        detected = self.get_detected_issues()
        if not detected:
            return None
        
        severity_order = [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW]
        for severity in severity_order:
            if any(r.severity == severity for r in detected):
                return severity
        
        return None
    
    def report(self) -> Dict[str, Any]:
        """Generate a summary report of all checks."""
        detected = self.get_detected_issues()
        
        return {
            'total_checks': len(self.results),
            'issues_found': len(detected),
            'highest_severity': self.get_highest_severity().value if self.get_highest_severity() else None,
            'results': [r.to_dict() for r in self.results],
            'detected_issues': [r.to_dict() for r in detected]
        }


if __name__ == '__main__':
    # Example usage
    checker = RuleChecker()
    
    sample_config = {
        'dhcp_bindings': {
            '192.168.1.10': {'mac': 'AA:BB:CC:DD:EE:11', 'state': 'Active'},
            '192.168.1.10': {'mac': 'AA:BB:CC:DD:EE:22', 'state': 'Active'},  # Duplicate
        },
        'static_ips': ['192.168.1.50'],
        'interfaces': {
            'Fa0/0': {'status': 'up', 'ip': '192.168.1.1', 'mask': '24'},
            'Fa0/1': {'status': 'down', 'ip': '10.0.0.1', 'mask': '24'},
        },
        'vlans': {1: {'name': 'default'}, 10: {'name': 'vlan10'}},
        'routes': {'192.168.1.0/24': {'next_hop': 'connected'}},
        'acls': {
            '101': [
                {'rule': 'permit tcp any any eq 80'},
                {'rule': 'invalid_rule_here'},
            ]
        },
        'gateway': '192.168.1.1',
        'expected_destinations': ['192.168.1.0/24', '10.0.0.0/24']
    }
    
    results = checker.run_all_checks(sample_config)
    report = checker.report()
    
    print("Rule Checker Report:")
    print(f"Total checks: {report['total_checks']}")
    print(f"Issues found: {report['issues_found']}")
    print(f"Highest severity: {report['highest_severity']}")
    print("\nDetected issues:")
    for issue in report['detected_issues']:
        print(f"  - {issue['rule']}: {issue['issue']}")
