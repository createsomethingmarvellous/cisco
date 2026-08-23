# NetSage AI Diagnosis Prompt Library

## Architecture

The diagnosis flow is: **Filter → Deterministic Checks → AI Prompt → Human Review**

- **Filter**: Remove malformed input, validate IP/VLAN ranges, check syntax
- **Deterministic Checks** (rule_checker.py): Catch obvious issues (duplicate IPs, down interfaces, missing routes)
- **AI Prompt**: Structured request for root cause analysis with confidence
- **Output JSON**: Explainable fields (what, where, confidence, why, next command, fix)

---

## Primary Diagnosis Prompt Template

**Purpose:** Force the AI model to return structured JSON with clear reasoning, evidence citations, and confidence levels.

```
You are a Cisco network troubleshooting expert. Analyze the network issue below using the given symptom, topology, and show-command outputs. Return a JSON object with these exact fields:

{
  "root_cause": "<concise description of the fault>",
  "osi_layer": "<layer number, e.g., '2', '3', '3-4', etc.>",
  "confidence": "<low|medium|high or 0.0-1.0>",
  "evidence": ["<quoted show-command line 1>", "<quoted show-command line 2>"],
  "what_is_wrong": "<what component or config is broken>",
  "where_is_fault": "<interface, VLAN, router, protocol, etc.>",
  "next_diagnostic_command": "<one show command to verify hypothesis>",
  "fix_steps": [
    "Step 1: <action and expected result>",
    "Step 2: <action and expected result>",
    "Step 3: <verify with show command>"
  ],
  "reasoning": "<explain why you selected this root cause, considering alternative hypotheses>"
}

**Case Details:**

Symptom: {symptom}

Topology Note: {topology_note}

Show-Command Outputs:
{show_outputs}

Expected Fault (for reference, do NOT use directly): {expected_fault}

**Instructions:**
1. Extract key facts from show-command output (IP addresses, VLAN IDs, interface status, route entries, ACL rules).
2. Identify which OSI layer(s) are involved (Layer 2 = switching/VLANs; Layer 3 = routing/IP).
3. Consider common Cisco misconfigurations: duplicate IPs, missing VLAN assignments, ACL blocking, gateway mismatch, interface down.
4. Return exactly one most likely root cause. If multiple equally likely, pick the simplest.
5. Quote actual evidence from show outputs. Do NOT invent logs.
6. Confidence: low if many unknowns, medium if some evidence points to root cause, high if evidence is definitive.
7. Next command should directly test your hypothesis.
8. Fix steps should be exact configuration commands or verification actions.
9. Reasoning field must explain why this is more likely than alternatives (e.g., "ruling out routing because show ip route contains the destination subnet").

Return ONLY valid JSON. No extra text.
```

---

## Worked Example 1: Inter-VLAN Routing Issue

**Input:**
```
Symptom: PC1 gets IP from DHCP but cannot ping PC2 in VLAN 20.

Topology Note: Two PCs in separate VLANs (10, 20). Router configured with subinterfaces.

Show-Command Outputs:
- show vlan brief: VLAN 10 active, VLAN 20 active
- show ip route: no route to VLAN 20 subnet (10.0.20.0/24 missing)
- show interfaces: Fa0/0.20 is down, line protocol is down
- show interfaces Fa0/0.20: encapsulation dot1Q 20, no IP address

Expected Fault: Inter-VLAN routing not configured
```

**Expected AI Output:**
```json
{
  "root_cause": "Subinterface Fa0/0.20 is administratively down; no inter-VLAN routing",
  "osi_layer": "3",
  "confidence": "high",
  "evidence": [
    "show interfaces Fa0/0.20 is down, line protocol is down",
    "show ip route missing 10.0.20.0/24",
    "show interfaces Fa0/0.20: no IP address configured"
  ],
  "what_is_wrong": "Router subinterface down and IP not assigned",
  "where_is_fault": "Router interface Fa0/0.20 (VLAN 20 trunk)",
  "next_diagnostic_command": "show run | include interface Fa0/0.20",
  "fix_steps": [
    "Step 1: Enter interface Fa0/0.20 configuration mode",
    "Step 2: Assign IP: 'ip address 10.0.20.1 255.255.255.0'",
    "Step 3: Enable interface: 'no shutdown'",
    "Step 4: Verify: 'show interfaces Fa0/0.20' should show up/up",
    "Step 5: Test: PC1 pings PC2 should succeed"
  ],
  "reasoning": "Subinterface down is root cause because (1) show vlan lists VLAN 20 as active, ruling out VLAN config; (2) no route in routing table indicates layer 3 path is broken; (3) subinterface is down and has no IP, blocking routing. Alternative: ACL blocking—ruled out because we see no ACL output. Alternative: DHCP—ruled out because PC1 already has IP."
}
```

---

## Worked Example 2: ACL Blocking SSH

**Input:**
```
Symptom: SSH to router times out; telnet works.

Topology Note: SSH service configured. Telnet enabled for comparison.

Show-Command Outputs:
- show ip ssh: version 1.99
- show run | include ssh: only 'ip ssh version 1.99'
- show access-lists: ACL 23 has 'permit tcp any any eq 23' but NO rule for port 22
- show interfaces: all up

Expected Fault: ACL blocking SSH port 22
```

**Expected AI Output:**
```json
{
  "root_cause": "Access Control List 23 missing rule for SSH port 22",
  "osi_layer": "4",
  "confidence": "high",
  "evidence": [
    "show access-lists: ACL 23 permits port 23 (telnet) but no rule for port 22",
    "show ip ssh: SSH version is 1.99, service enabled",
    "Telnet works (port 23 allowed by ACL) but SSH fails (port 22 not allowed)"
  ],
  "what_is_wrong": "Inbound ACL missing permit rule for TCP port 22",
  "where_is_fault": "Router ACL 23 (likely applied to vty lines or inbound interface)",
  "next_diagnostic_command": "show run | include access-list 23",
  "fix_steps": [
    "Step 1: Enter global configuration mode",
    "Step 2: Edit ACL 23: 'access-list 23 permit tcp any any eq 22'",
    "Step 3: Verify: 'show access-lists 23' should now show SSH rule",
    "Step 4: Test SSH: 'ssh -v -l admin 192.168.1.1' should connect",
    "Step 5: Confirm: 'show ip ssh' and 'show sessions'"
  ],
  "reasoning": "ACL missing port 22 rule is root cause because (1) Telnet (port 23) works, proving SSH daemon is listening and router is reachable, so layer 1-3 are OK; (2) SSH is enabled in run config but port 22 not in ACL, indicating access list filtering; (3) port mismatch (23 allowed, 22 blocked) is classic ACL oversight. Alternative: SSH daemon crash—ruled out because show ip ssh shows service is up. Alternative: firewall—would affect both telnet and SSH, but only SSH fails."
}
```

---

## Worked Example 3: DHCP Gateway Mismatch

**Input:**
```
Symptom: DHCP clients get IP but gateway unreachable; static IP works.

Topology Note: DHCP pool 10.0.0.0/24, gateway 10.0.0.1. Static device 10.0.0.50.

Show-Command Outputs:
- show ip dhcp pool: subnet 10.0.0.0 255.255.255.0, but NO 'default-gateway 10.0.0.1' line
- show run | include ip helper: no helper configured on relay
- show interfaces Fa0/0: up/up, IP 10.0.0.1 255.255.255.0
- show ip dhcp binding: 10.0.0.10 leased (MAC aabbccddee11)

Expected Fault: DHCP gateway not set or DHCP relay misconfigured
```

**Expected AI Output:**
```json
{
  "root_cause": "DHCP pool missing 'default-gateway' command; clients receive no gateway",
  "osi_layer": "3",
  "confidence": "high",
  "evidence": [
    "show ip dhcp pool: subnet configured but no 'default-gateway' line",
    "show interfaces Fa0/0: up/up, gateway IP 10.0.0.1 exists on router",
    "Static device 10.0.0.50 can reach gateway; dynamic client with no gateway cannot"
  ],
  "what_is_wrong": "DHCP pool configuration incomplete: missing default gateway option",
  "where_is_fault": "DHCP server pool configuration on router",
  "next_diagnostic_command": "show ip dhcp pool | include gateway",
  "fix_steps": [
    "Step 1: Enter DHCP pool config: 'ip dhcp pool MyPool'",
    "Step 2: Add gateway: 'default-gateway 10.0.0.1'",
    "Step 3: Save and verify: 'show ip dhcp pool'",
    "Step 4: Release and renew on client: 'ipconfig /release && ipconfig /renew' (Windows) or 'dhclient -r && dhclient' (Linux)",
    "Step 5: Verify client has gateway: 'ipconfig' or 'ip route show'"
  ],
  "reasoning": "Missing default-gateway is root cause because (1) static IP on same subnet works, proving router is reachable; (2) DHCP pool is defined but no gateway option, so DHCP clients have no route to router; (3) common DHCP misconfiguration. Alternative: gateway down—ruled out because static device can ping gateway. Alternative: DHCP relay issue—ruled out because no relay is configured and router is DHCP server directly."
}
```

---

## Secondary Prompts for Refinement

### Prompt: Evidence Verification
Use if AI response lacks specific show-command evidence:

```
Review your diagnosis. For each claim in the root cause, cite a specific line from show-command output. 
Format: (show command: <line>). 
If you cannot find evidence for a claim, mark it [NO EVIDENCE] and lower confidence to low.
Return the same JSON with updated evidence field and adjusted confidence.
```

### Prompt: Confidence Justification
Use if confidence is unclear:

```
Justify your confidence level:
- HIGH: This fault is uniquely identified by the show-command output, no alternatives fit the evidence.
- MEDIUM: Multiple faults could explain the symptom; this is the most likely based on evidence.
- LOW: Insufficient information; further diagnostic commands needed.

Explain which alternative hypotheses you ruled out and why.
```

### Prompt: Fix Validation
Use if fix steps seem risky or incomplete:

```
Before the fix is applied:
1. State the expected state of the network after each fix step.
2. Identify any side effects or risks (e.g., traffic loss, cascading failures).
3. Propose a rollback plan if the fix fails.
4. Recommend a minimal test to verify the fix worked before declaring success.
```

---

## Integration with Rule Checker

Before invoking the AI prompt, the **deterministic rule checker** (rule_checker.py) runs:

1. **Validate syntax** — IP addresses, VLAN IDs, interface names
2. **Check common hard failures** — duplicate IPs, gateway mismatch, interface down, missing VLAN
3. **If rule checker finds definitive issue**, return it immediately with confidence=high
4. **If no clear issue**, pass to AI prompt with note of what was already ruled out

This hybrid approach ensures:
- **Explainability**: rules catch obvious issues, AI refines ambiguous ones
- **Speed**: no AI call for trivial cases (duplicate IP)
- **Safety**: human must review all recommendations

---

## Output Validation Checklist

AI response must include:
- [ ] Valid JSON (parseable)
- [ ] All 10 fields present
- [ ] Confidence is one of: low, medium, high, or 0.0–1.0
- [ ] Evidence array has 2+ items quoted from show outputs
- [ ] next_diagnostic_command is a single 'show' command
- [ ] fix_steps array has 3+ actionable steps
- [ ] reasoning references why alternatives were ruled out
- [ ] where_is_fault identifies a specific interface/VLAN/device
- [ ] OSI layer matches the fault domain (2 for VLAN/trunk, 3 for routing, 4 for ACL/port)

If any field fails validation, prompt human reviewer to request clarification from AI.
