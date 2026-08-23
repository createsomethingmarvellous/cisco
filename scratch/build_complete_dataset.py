import csv
import json

# Production-grade authentic multi-device Packet Tracer dataset
cases = [
    # Case 1: Inter-VLAN Routing Subinterface Down
    {
        'case_id': 1,
        'symptom': 'PC1 (VLAN 10) gets IP 192.168.10.50 but cannot ping PC2 (VLAN 20: 192.168.20.50)',
        'topology_note': 'Packet Tracer Lab: Router R1-EDGE (Cisco 2911) connected via Gi0/0 trunk to Switch SW-CORE (2960). PC1 on SW-CORE Fa0/1 (VLAN 10), PC2 on SW-CORE Fa0/2 (VLAN 20).',
        'show_outputs': """Device: R1-EDGE
hostname R1-EDGE
!
interface GigabitEthernet0/0
 no ip address
 duplex auto
 speed auto
!
interface GigabitEthernet0/0.10
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0
!
interface GigabitEthernet0/0.20
 encapsulation dot1Q 20
 shutdown
 ip address 192.168.20.1 255.255.255.0
!
show ip route
C    192.168.10.0/24 is directly connected, GigabitEthernet0/0.10

Device: SW-CORE
hostname SW-CORE
!
vlan 10
 name Sales
vlan 20
 name Engineering
!
interface FastEthernet0/1
 switchport access vlan 10
 switchport mode access
!
interface FastEthernet0/2
 switchport access vlan 20
 switchport mode access
!
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk allowed vlan 10,20
""",
        'expected_fault': 'Router subinterface GigabitEthernet0/0.20 is administratively down',
        'osi_layer': '3',
        'concept_tag': 'inter-vlan-routing',
        'severity': 'high',
        'case_type': 'routing'
    },

    # Case 2: VLAN ACL Ingress Deny Rule
    {
        'case_id': 2,
        'symptom': 'Guest Wi-Fi clients (VLAN 50: 10.0.50.0/24) get IP but cannot reach File Server (VLAN 100: 10.0.100.50)',
        'topology_note': 'Packet Tracer Lab: Router R1-GW handling inter-VLAN routing with ACL 101 applied. SW-ACCESS hosting VLAN 50 (Guest) and VLAN 100 (Server).',
        'show_outputs': """Device: R1-GW
hostname R1-GW
!
interface GigabitEthernet0/0.50
 encapsulation dot1Q 50
 ip address 10.0.50.1 255.255.255.0
 ip access-group 101 in
!
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 ip address 10.0.100.1 255.255.255.0
!
access-list 101 deny ip 10.0.50.0 0.0.0.255 10.0.100.0 0.0.0.255
access-list 101 permit ip any any

Device: SW-ACCESS
hostname SW-ACCESS
!
vlan 50
 name Guest
vlan 100
 name Server
!
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk allowed vlan 50,100
""",
        'expected_fault': 'VLAN ACL 101 explicitly denies traffic from VLAN 50 (10.0.50.0/24) to VLAN 100 (10.0.100.0/24)',
        'osi_layer': '3-4',
        'concept_tag': 'vlan-acl',
        'severity': 'high',
        'case_type': 'acl'
    },

    # Case 3: DHCP Pool Missing Excluded-Address
    {
        'case_id': 3,
        'symptom': 'Workstation PC-01 reports IP address conflict warning for 192.168.1.50',
        'topology_note': 'Packet Tracer Lab: Router R1-DHCP configured as DHCP server. Network printer static IP 192.168.1.50 in same subnet.',
        'show_outputs': """Device: R1-DHCP
hostname R1-DHCP
!
ip dhcp pool LAN_POOL
 network 192.168.1.0 255.255.255.0
 default-router 192.168.1.1
!
show ip dhcp binding
IP address       Client-ID/Hardware address     Lease expiration        Type
192.168.1.50     0060.2F3A.1122                 Aug 19 2026 05:00 PM    Automatic
!
show ip dhcp conflict
IP address       Detection method   Detection time
192.168.1.50     Ping               Aug 19 2026 04:30 PM
""",
        'expected_fault': 'DHCP pool 192.168.1.0/24 missing ip dhcp excluded-address range for static IP 192.168.1.50',
        'osi_layer': '3',
        'concept_tag': 'ip-conflict',
        'severity': 'critical',
        'case_type': 'dhcp'
    },

    # Case 4: OSPF Area ID Mismatch
    {
        'case_id': 4,
        'symptom': 'OSPF neighbors R1-CORE and R2-BRANCH stuck in INIT state; no dynamic routes in routing table',
        'topology_note': 'Packet Tracer Lab: R1-CORE and R2-BRANCH connected via Serial link S0/0/0. Both running OSPF Process 1.',
        'show_outputs': """Device: R1-CORE
hostname R1-CORE
!
interface Serial0/0/0
 ip address 10.1.1.1 255.255.255.252
!
router ospf 1
 router-id 1.1.1.1
 network 10.1.1.0 0.0.0.3 area 0
!
show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
2.2.2.2           0   INIT/  -        00:00:33    10.1.1.2        Serial0/0/0

Device: R2-BRANCH
hostname R2-BRANCH
!
interface Serial0/0/0
 ip address 10.1.1.2 255.255.255.252
!
router ospf 1
 router-id 2.2.2.2
 network 10.1.1.0 0.0.0.3 area 1
!
show ip ospf neighbor
Neighbor ID     Pri   State           Dead Time   Address         Interface
1.1.1.1           0   INIT/  -        00:00:31    10.1.1.1        Serial0/0/0
""",
        'expected_fault': 'OSPF Area ID mismatch: R1-CORE interface in Area 0 while R2-BRANCH interface in Area 1',
        'osi_layer': '3',
        'concept_tag': 'ospf-area-mismatch',
        'severity': 'high',
        'case_type': 'routing'
    },

    # Case 5: Switch Trunk Native VLAN Mismatch
    {
        'case_id': 5,
        'symptom': 'Switches SW-FLOOR1 and SW-FLOOR2 trunk link port flapping with native VLAN mismatch error in Syslog',
        'topology_note': 'Packet Tracer Lab: SW-FLOOR1 connected to SW-FLOOR2 on GigabitEthernet0/1 configured as 802.1Q trunk.',
        'show_outputs': """Device: SW-FLOOR1
hostname SW-FLOOR1
!
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk native vlan 10
!
%CDP-4-NATIVE_VLAN_MISMATCH: Native VLAN mismatch detected on GigabitEthernet0/1 (10), with SW-FLOOR2 GigabitEthernet0/1 (20).

Device: SW-FLOOR2
hostname SW-FLOOR2
!
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk native vlan 20
""",
        'expected_fault': 'Native VLAN mismatch on trunk link: SW-FLOOR1 uses Native VLAN 10, SW-FLOOR2 uses Native VLAN 20',
        'osi_layer': '2',
        'concept_tag': 'trunk-native-vlan-mismatch',
        'severity': 'high',
        'case_type': 'layer2'
    },

    # Case 6: Missing DHCP Relay Helper Address
    {
        'case_id': 6,
        'symptom': 'PC1 in VLAN 30 fails to get IP address from central DHCP server (10.100.1.50)',
        'topology_note': 'Packet Tracer Lab: Router R1-HQ acts as default gateway for VLAN 30 (192.168.30.0/24). Central DHCP server located on VLAN 100.',
        'show_outputs': """Device: R1-HQ
hostname R1-HQ
!
interface GigabitEthernet0/0.30
 encapsulation dot1Q 30
 ip address 192.168.30.1 255.255.255.0
!
interface GigabitEthernet0/0.100
 encapsulation dot1Q 100
 ip address 10.100.1.1 255.255.255.0
!
Device: SW1
hostname SW1
!
interface FastEthernet0/10
 switchport access vlan 30
 switchport mode access
""",
        'expected_fault': 'Missing ip helper-address 10.100.1.50 command on router subinterface GigabitEthernet0/0.30',
        'osi_layer': '3',
        'concept_tag': 'dhcp-relay-missing',
        'severity': 'high',
        'case_type': 'dhcp'
    },

    # Case 7: Static Route Next-Hop Unreachable
    {
        'case_id': 7,
        'symptom': 'R1-HQ cannot reach Branch LAN (172.16.10.0/24); ping to 172.16.10.1 times out',
        'topology_note': 'Packet Tracer Lab: R1-HQ connected to R2-BR via point-to-point link 10.0.0.0/30 (R1: 10.0.0.1, R2: 10.0.0.2).',
        'show_outputs': """Device: R1-HQ
hostname R1-HQ
!
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
!
ip route 172.16.10.0 255.255.255.0 10.0.0.5
!
show ip route
S    172.16.10.0/24 [1/0] via 10.0.0.5 (unreachable)

Device: R2-BR
hostname R2-BR
!
interface GigabitEthernet0/0
 ip address 10.0.0.2 255.255.255.252
""",
        'expected_fault': 'Static route on R1-HQ points to invalid next-hop IP 10.0.0.5 instead of 10.0.0.2',
        'osi_layer': '3',
        'concept_tag': 'static-route-invalid-nexthop',
        'severity': 'high',
        'case_type': 'routing'
    },

    # Case 8: Port Security Shutdown Violation
    {
        'case_id': 8,
        'symptom': 'Switchport Fa0/5 becomes disabled immediately when employee connects new laptop',
        'topology_note': 'Packet Tracer Lab: Switch SW-SEC configured with Port Security on Fa0/5 (max 1 MAC, violation shutdown).',
        'show_outputs': """Device: SW-SEC
hostname SW-SEC
!
interface FastEthernet0/5
 switchport mode access
 switchport port-security
 switchport port-security maximum 1
 switchport port-security mac-address 0010.1122.3344
 switchport port-security violation shutdown
!
show interfaces FastEthernet0/5
FastEthernet0/5 is down, line protocol is down (err-disabled)
!
show port-security interface FastEthernet0/5
Port Security              : Enabled
Port Status                : Secure-shutdown
Violation Mode             : Shutdown
Security Violation Count   : 1
Last Source Address:Vlan   : 0090.AABB.CCDD:1
""",
        'expected_fault': 'Port Security violation triggered by unauthorized MAC address 0090.AABB.CCDD on Fa0/5',
        'osi_layer': '2',
        'concept_tag': 'port-security-errdisable',
        'severity': 'high',
        'case_type': 'layer2'
    },

    # Case 9: NAT Missing Inside Interface Designation
    {
        'case_id': 9,
        'symptom': 'Internal LAN (192.168.1.0/24) hosts cannot access Internet web server (8.8.8.8)',
        'topology_note': 'Packet Tracer Lab: Router R1-NAT running Dynamic NAT overload (PAT) towards ISP router.',
        'show_outputs': """Device: R1-NAT
hostname R1-NAT
!
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
!
interface GigabitEthernet0/1
 ip address 203.0.113.2 255.255.255.252
 ip nat outside
!
ip nat inside source list 1 interface GigabitEthernet0/1 overload
access-list 1 permit 192.168.1.0 0.0.0.255
!
show ip nat translations
(empty)
""",
        'expected_fault': 'Internal interface GigabitEthernet0/0 is missing the ip nat inside command',
        'osi_layer': '3',
        'concept_tag': 'nat-inside-missing',
        'severity': 'high',
        'case_type': 'nat'
    },

    # Case 10: EIGRP Autonomous System Mismatch
    {
        'case_id': 10,
        'symptom': 'EIGRP neighbors R1 and R2 do not form adjacency; routing tables missing remote subnets',
        'topology_note': 'Packet Tracer Lab: R1 and R2 connected via serial link S0/0/0. R1 in EIGRP AS 100, R2 in EIGRP AS 200.',
        'show_outputs': """Device: R1
hostname R1
!
interface Serial0/0/0
 ip address 10.2.2.1 255.255.255.252
!
router eigrp 100
 network 10.2.2.0 0.0.0.3
!
show ip eigrp neighbors
IP-EIGRP neighbors for process 100
(empty)

Device: R2
hostname R2
!
interface Serial0/0/0
 ip address 10.2.2.2 255.255.255.252
!
router eigrp 200
 network 10.2.2.0 0.0.0.3
!
show ip eigrp neighbors
IP-EIGRP neighbors for process 200
(empty)
""",
        'expected_fault': 'EIGRP Autonomous System (AS) number mismatch: R1 uses AS 100 while R2 uses AS 200',
        'osi_layer': '3',
        'concept_tag': 'eigrp-as-mismatch',
        'severity': 'high',
        'case_type': 'routing'
    },

    # Case 11: HSRP Dual-Active Split Brain
    {
        'case_id': 11,
        'symptom': 'Duplicate IP address warnings for 192.168.1.254 on default gateway; network instability',
        'topology_note': 'Packet Tracer Lab: R1 (Priority 110) and R2 (Priority 100) configured for HSRP Group 1 on Gi0/0.',
        'show_outputs': """Device: R1
hostname R1
!
interface GigabitEthernet0/0
 ip address 192.168.1.2 255.255.255.0
 standby 1 ip 192.168.1.254
 standby 1 priority 110
!
show standby brief
Group  State   Active          Standby         Virtual IP
1      Active  local           192.168.1.3     192.168.1.254

Device: R2
hostname R2
!
interface GigabitEthernet0/0
 ip address 192.168.1.3 255.255.255.0
 standby 1 ip 192.168.1.254
 standby 1 priority 100
 ip access-group 105 in
!
access-list 105 deny udp any any eq 1985
access-list 105 permit ip any any
!
show standby brief
Group  State   Active          Standby         Virtual IP
1      Active  local           unknown         192.168.1.254
""",
        'expected_fault': 'HSRP dual-active split brain caused by ACL 105 on R2 blocking HSRP UDP 1985 hello packets',
        'osi_layer': '3',
        'concept_tag': 'hsrp-split-brain',
        'severity': 'critical',
        'case_type': 'redundancy'
    },

    # Case 12: LACP EtherChannel Passive/Passive Mismatch
    {
        'case_id': 12,
        'symptom': 'EtherChannel Port-channel 1 down; member interfaces Gi0/1 and Gi0/2 remain in suspended mode',
        'topology_note': 'Packet Tracer Lab: SW1 and SW2 interconnected via two links configured for LACP EtherChannel.',
        'show_outputs': """Device: SW1
hostname SW1
!
interface GigabitEthernet0/1
 channel-group 1 mode passive
!
interface GigabitEthernet0/2
 channel-group 1 mode passive
!
show etherchannel summary
Group  Port-channel  Protocol    Ports
1      Po1(SD)         LACP      Gi0/1(I) Gi0/2(I)

Device: SW2
hostname SW2
!
interface GigabitEthernet0/1
 channel-group 1 mode passive
!
interface GigabitEthernet0/2
 channel-group 1 mode passive
!
show etherchannel summary
Group  Port-channel  Protocol    Ports
1      Po1(SD)         LACP      Gi0/1(I) Gi0/2(I)
""",
        'expected_fault': 'LACP EtherChannel mode passive on both switches prevents channel negotiation (at least one must be active)',
        'osi_layer': '2',
        'concept_tag': 'lacp-etherchannel-passive',
        'severity': 'high',
        'case_type': 'layer2'
    },

    # Case 13: Wireless WLC CAPWAP Option 43 Missing
    {
        'case_id': 13,
        'symptom': 'Lightweight APs in VLAN 20 fail to discover Wireless LAN Controller (10.100.1.10) in VLAN 100',
        'topology_note': 'Packet Tracer Lab: Cisco 3702 AP in VLAN 20 receiving DHCP from Router R1-DHCP.',
        'show_outputs': """Device: R1-DHCP
hostname R1-DHCP
!
ip dhcp pool AP_POOL
 network 192.168.20.0 255.255.255.0
 default-router 192.168.20.1
!
Device: WLC-3504
hostname WLC-3504
!
Management Interface IP: 10.100.1.10
AP Summary: 0 APs connected
""",
        'expected_fault': 'DHCP pool AP_POOL missing Option 43 (ip dhcp pool AP_POOL -> option 43 ip 10.100.1.10) for CAPWAP WLC discovery',
        'osi_layer': '3',
        'concept_tag': 'wlc-capwap-dhcp-option43',
        'severity': 'high',
        'case_type': 'wireless'
    },

    # Case 14: BGP Remote AS Number Mismatch
    {
        'case_id': 14,
        'symptom': 'eBGP session between Router R1-ENT and ISP-RTR fails to establish; state remains Idle',
        'topology_note': 'Packet Tracer Lab: Enterprise Router R1-ENT (AS 65001) peering with ISP Router (AS 64512) over 203.0.113.0/30.',
        'show_outputs': """Device: R1-ENT
hostname R1-ENT
!
interface GigabitEthernet0/0
 ip address 203.0.113.1 255.255.255.252
!
router bgp 65001
 neighbor 203.0.113.2 remote-as 64599
!
show ip bgp summary
BGP neighbor is 203.0.113.2, remote AS 64599, external link
BGP state = Idle

Device: ISP-RTR
hostname ISP-RTR
!
interface GigabitEthernet0/0
 ip address 203.0.113.2 255.255.255.252
!
router bgp 64512
 neighbor 203.0.113.1 remote-as 65001
""",
        'expected_fault': 'BGP neighbor remote-as mismatch on R1-ENT: configured remote-as 64599 instead of ISP AS 64512',
        'osi_layer': '3',
        'concept_tag': 'bgp-remote-as-mismatch',
        'severity': 'high',
        'case_type': 'routing'
    },

    # Case 15: Spanning Tree PortFast Enabled on Trunk Link
    {
        'case_id': 15,
        'symptom': 'Broadcast storm and MAC address table instability occurring across Switch SW1 and SW2',
        'topology_note': 'Packet Tracer Lab: Inter-switch trunk link Gi0/1 configured with PortFast by mistake.',
        'show_outputs': """Device: SW1
hostname SW1
!
interface GigabitEthernet0/1
 switchport mode trunk
 spanning-tree portfast
!
show spanning-tree interface GigabitEthernet0/1
PortFast enabled on trunk port GigabitEthernet0/1!
Topology change counter: 452
""",
        'expected_fault': 'Spanning Tree PortFast enabled on trunk interface GigabitEthernet0/1 bypassing listening/learning states',
        'osi_layer': '2',
        'concept_tag': 'stp-portfast-trunk-loop',
        'severity': 'critical',
        'case_type': 'layer2'
    }
]

with open('cases.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['case_id', 'symptom', 'topology_note', 'show_outputs', 'expected_fault', 'osi_layer', 'concept_tag', 'severity', 'case_type'])
    writer.writeheader()
    for c in cases:
        writer.writerow(c)

print(f"Successfully generated {len(cases)} comprehensive multi-device Packet Tracer cases in cases.csv!")
