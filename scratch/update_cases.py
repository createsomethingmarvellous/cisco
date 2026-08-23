import csv

# Create authentic multi-device Packet Tracer cases
cases = [
    {
        'case_id': 1,
        'symptom': 'PC1 (VLAN 10) gets IP but cannot ping PC2 in VLAN 20',
        'topology_note': 'Packet Tracer Lab: Router R1 (2911) connected via Gi0/0 trunk to Switch SW1 (2960). PC1 on SW1 Fa0/1 (VLAN 10), PC2 on SW1 Fa0/2 (VLAN 20).',
        'show_outputs': """Device: R1
hostname R1
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

Device: SW1
hostname SW1
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
    {
        'case_id': 2,
        'symptom': 'Guest Wi-Fi (VLAN 50) clients get IP but cannot reach file server on VLAN 100',
        'topology_note': 'Packet Tracer Lab: Router R1 handling inter-VLAN routing with ACL 101 applied. SW1 hosting VLAN 50 (Guest) and VLAN 100 (Server).',
        'show_outputs': """Device: R1
hostname R1
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

Device: SW1
hostname SW1
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
    {
        'case_id': 3,
        'symptom': 'Workstation PC1 reports IP address conflict warning 192.168.1.50',
        'topology_note': 'Packet Tracer Lab: Router R1 configured as DHCP server. Static printer assigned same IP address.',
        'show_outputs': """Device: R1
hostname R1
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
    {
        'case_id': 4,
        'symptom': 'OSPF neighbors R1 and R2 stuck in INIT state; no routes exchanged',
        'topology_note': 'Packet Tracer Lab: R1 and R2 connected via serial link S0/0/0. Both running OSPF Process 1.',
        'show_outputs': """Device: R1
hostname R1
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

Device: R2
hostname R2
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
        'expected_fault': 'OSPF Area ID mismatch: R1 interface in Area 0 while R2 interface in Area 1',
        'osi_layer': '3',
        'concept_tag': 'ospf-area-mismatch',
        'severity': 'high',
        'case_type': 'routing'
    },
    {
        'case_id': 5,
        'symptom': 'Switch SW1 and SW2 trunk link port flapping with native VLAN mismatch error in Syslog',
        'topology_note': 'Packet Tracer Lab: SW1 connected to SW2 on GigabitEthernet0/1 configured as 802.1Q trunk.',
        'show_outputs': """Device: SW1
hostname SW1
!
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk native vlan 10
!
%CDP-4-NATIVE_VLAN_MISMATCH: Native VLAN mismatch detected on GigabitEthernet0/1 (10), with SW2 GigabitEthernet0/1 (20).

Device: SW2
hostname SW2
!
interface GigabitEthernet0/1
 switchport mode trunk
 switchport trunk native vlan 20
""",
        'expected_fault': 'Native VLAN mismatch on trunk link: SW1 uses Native VLAN 10, SW2 uses Native VLAN 20',
        'osi_layer': '2',
        'concept_tag': 'trunk-native-vlan-mismatch',
        'severity': 'high',
        'case_type': 'layer2'
    }
]

with open('cases.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['case_id', 'symptom', 'topology_note', 'show_outputs', 'expected_fault', 'osi_layer', 'concept_tag', 'severity', 'case_type'])
    writer.writeheader()
    for c in cases:
        writer.writerow(c)

print("Created multi-device authentic Packet Tracer cases in cases.csv")
