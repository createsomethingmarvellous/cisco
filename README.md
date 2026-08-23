# NetSage AI: Cisco Troubleshooting Assistant with Human Review

## Project Overview

NetSage AI is an AI-assisted network troubleshooting system designed for Cisco-style lab networks. It combines:
- **Deterministic rule checking** for obvious faults
- **Structured AI diagnosis** with confidence levels
- **Human review workflows** to ensure correctness and explainability
- **Feedback logging** to track AI accuracy and improve over time

**Key Principle:** *Explainability over complexity. Every diagnosis must be understandable and reviewable by a junior network engineer.*

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   DIAGNOSIS PIPELINE                         │
└─────────────────────────────────────────────────────────────┘

1. INPUT: Symptom + Topology + Show-Command Outputs
   ↓
2. FILTER: Validate syntax, IP ranges, interface names
   ↓
3. PARSE: Extract structured data from show outputs (config_parser.py)
   ↓
4. RULE CHECK: Deterministic checks for common misconfigurations (rule_checker.py)
   ├─ Duplicate IPs (critical)
   ├─ Interface down (high)
   ├─ Subnet mask mismatch (critical)
   ├─ Gateway unreachable (high)
   ├─ Missing VLAN assignment (high)
   ├─ Missing routes (high)
   ├─ PortFast on trunk (medium)
   └─ ACL syntax errors (medium)
   ↓
5. IF rule check detects issue → Return with confidence=high, skip AI
   ELSE → Generate AI prompt
   ↓
6. AI DIAGNOSIS: Call LLM with structured prompt → JSON response (diagnose_prompt.md)
   Response includes: root_cause, confidence, evidence, what, where, fix_steps, reasoning
   ↓
7. VALIDATE: Check JSON structure and evidence quality
   ↓
8. HUMAN REVIEW: Reviewer accepts, edits, or rejects diagnosis (responsible_ai_log.md)
   ↓
9. LOG: Record decision and any corrections for learning
   ↓
OUTPUT: Approved diagnosis with confidence level and fix steps
```

---

## File Structure

```
d:\cisco\
├── README.md                    # This file
├── cases.csv                    # 30 troubleshooting cases (dataset)
├── diagnose_prompt.md           # Structured AI prompts + 3 worked examples
├── config_parser.py             # Parse show-command outputs → structured data
├── rule_checker.py              # Deterministic checks for common faults
├── ai_diagnosis_runner.py       # Orchestrates full pipeline
├── responsible_ai_log.md        # Human review log (5+ corrected cases)
├── dashboard.py                 # (To be created) Reporting and visualization
├── ai_responses/                # (To be created) AI responses for each case (JSON)
│   └── case_001_response.json
│   └── case_002_response.json
│   └── ...
└── review_log.csv              # (Generated) Human review tracking
```

---

## Component Descriptions

### 1. `cases.csv`
**30 troubleshooting cases** covering Cisco network fault types:
- **Columns:** case_id, symptom, topology_note, show_outputs, expected_fault, osi_layer, concept_tag, severity, case_type
- **Concepts covered:**
  - Inter-VLAN routing (2 cases)
  - VLAN ACL (2 cases)
  - DHCP config (2 cases)
  - DNS routing (1 case)
  - Spanning Tree / Layer 2 (5 cases)
  - SSH/Telnet config (2 cases)
  - NAT (1 case)
  - Frame Relay (1 case)
  - EIGRP/OSPF/RIP (3 cases)
  - BGP (1 case)
  - SNMP/Syslog (2 cases)
  - IPSec/VPN (1 case)
  - Port security (1 case)
  - Multicast (1 case)
  - QoS (1 case)
  - PPP (1 case)
  - RADIUS (1 case)

**Usage:**
```python
import csv
with open('cases.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        case_id = row['case_id']
        symptom = row['symptom']
        # Load into DiagnosisCase objects
```

---

### 2. `diagnose_prompt.md`
**Structured prompts for AI diagnosis** with:
- Primary prompt template (forces JSON output with 9 required fields)
- **3 worked examples:**
  1. Inter-VLAN routing issue (subinterface down)
  2. ACL blocking SSH (port 22)
  3. DHCP gateway mismatch (missing default-gateway)
- Secondary prompts for refinement (evidence verification, confidence justification, fix validation)
- Integration notes with rule checker
- Output validation checklist

**How to use:**
1. Load prompt template from this file
2. Substitute {symptom}, {topology_note}, {show_outputs}, {expected_fault}
3. Send to LLM (Claude, GPT-4, etc.)
4. Parse JSON response (must have 9 fields)
5. Validate evidence contains show-command quotes

---

### 3. `config_parser.py`
**Parses Cisco show-command outputs into Python dictionaries.**

**Classes:**
- `CiscoConfigParser`: Static methods to parse individual show commands
  - `parse_show_vlan(output)` → Dict[vlan_id: {name, status}]
  - `parse_show_ip_route(output)` → Dict[subnet: {next_hop, raw}]
  - `parse_show_interfaces(output)` → Dict[iface_name: {status, ip, vlan, encapsulation, errors}]
  - `parse_show_access_lists(output)` → Dict[acl_id: List[{rule}]]
  - `parse_show_ip_dhcp_binding(output)` → Dict[ip: {mac, state}]
- `ConfigAnalyzer`: Methods to check parsed configs for issues
  - `check_subnet_mask_consistency()`
  - `check_interface_errors()`
  - `check_missing_routes()`

**Usage:**
```python
from config_parser import CiscoConfigParser

parser = CiscoConfigParser()
vlans = parser.parse_show_vlan(show_output)
routes = parser.parse_show_ip_route(show_output)
interfaces = parser.parse_show_interfaces(show_output)
```

---

### 4. `rule_checker.py`
**Deterministic checks for common Cisco misconfigurations.**

**8 Rule Checks:**
1. `check_duplicate_ips()` — DHCP bindings + static IPs for duplicates (CRITICAL)
2. `check_interface_down()` — Flags interfaces with status=down (HIGH)
3. `check_subnet_mask_mismatch()` — Overlapping subnets with different masks (CRITICAL)
4. `check_gateway_unreachable()` — DHCP gateway not in any route (HIGH)
5. `check_missing_vlan_assignment()` — Interface assigned to non-existent VLAN (HIGH)
6. `check_missing_routes()` — Expected routes missing from routing table (HIGH)
7. `check_portfast_on_trunk()` — PortFast enabled on trunk port (MEDIUM)
8. `check_acl_syntax()` — Invalid ACL rule syntax (MEDIUM)

**Output:** `DiagnosisResult` objects with (detected, issue, osi_layer, severity, evidence)

**Usage:**
```python
from rule_checker import RuleChecker

checker = RuleChecker()
config_data = {
    'dhcp_bindings': {...},
    'interfaces': {...},
    'vlans': {...},
    'routes': {...},
    'acls': {...},
    'gateway': '192.168.1.1',
    'expected_destinations': ['10.0.0.0/8']
}

results = checker.run_all_checks(config_data)
detected_issues = checker.get_detected_issues()
report = checker.report()  # Summary statistics
```

---

### 5. `ai_diagnosis_runner.py`
**Orchestrates the full pipeline: parse → rule check → AI prompt → human review.**

**Classes:**
- `DiagnosisCase`: Holds a single case through the pipeline
  - Attributes: symptom, topology, show_outputs, expected_fault, parsed_config, rule_check_results, ai_diagnosis, review_status, human_feedback
- `DiagnosisPipeline`: Runs steps 1-3
  - `step_1_parse_config()` — Extract structured data
  - `step_2_rule_checks()` — Run deterministic checks
  - `step_3_ai_diagnosis_prompt()` — Generate prompt for AI
  - `set_ai_response()` — Validate and store AI JSON response
  - `compare_with_expected()` — Check if AI matched expected fault
  - `run_full_pipeline()` — Execute all steps
- `DiagnosisReporter`: Generate reports and logs
  - `export_cases_for_ai()` — Batch export prompts to file
  - `create_review_log()` — CSV for human review tracking
  - `generate_summary_report()` — Statistics by concept, acceptance rate

**Workflow:**
```python
from ai_diagnosis_runner import DiagnosisCase, DiagnosisPipeline, DiagnosisReporter

# Load case
case = DiagnosisCase(case_id=1, symptom="...", ...)

# Run pipeline
pipeline = DiagnosisPipeline()
result = pipeline.run_full_pipeline(case)  # steps 1-3

# Get AI response from LLM
ai_json = """{"root_cause": "...", ...}"""
pipeline.set_ai_response(case, ai_json)

# Human review
case.review_status = ReviewStatus.ACCEPTED
case.human_feedback = "Correct diagnosis, good confidence."

# Generate reports
reporter = DiagnosisReporter()
reporter.create_review_log([case], 'review_log.csv')
summary = reporter.generate_summary_report([case])
```

---

### 6. `responsible_ai_log.md`
**Documents 5+ cases where AI diagnosis was corrected, edited, or rejected.**

**For each entry:**
- Case ID and concept tag
- AI diagnosis (root cause, confidence, evidence)
- Expected fault
- Human decision (Accepted / Edited / Rejected)
- Correction and feedback
- Lessons learned

**Current entries showcase:**
- Entry 1: NAT pool case — AI correct but fix steps incomplete (EDITED)
- Entry 2: IPSec case — AI blamed ACL but real issue was asymmetric routing (REJECTED)
- Entry 3: VLAN ACL case — AI technically correct but missed policy context (ACCEPTED with notes)
- Entry 4: OSPF case — AI diagnosis correct and complete (ACCEPTED)
- Entry 5: Subnet mask case — Rule checker caught it first, AI also correct (ACCEPTED)

**Summary statistics:**
- 2 Accepted (AI correct)
- 2 Edited (AI partially correct)
- 1 Rejected (AI incorrect)
- 1 Caught by rule checker first

---

## Usage Workflow

### For Instructors / Setup

1. **Prepare environment:**
   ```bash
   python -m pip install -r requirements.txt  # (future: add if using external libs)
   ```

2. **Load cases:**
   ```python
   import csv
   from ai_diagnosis_runner import DiagnosisCase, DiagnosisPipeline
   
   cases = []
   with open('cases.csv') as f:
       reader = csv.DictReader(f)
       for row in reader:
           case = DiagnosisCase(
               case_id=int(row['case_id']),
               symptom=row['symptom'],
               topology_note=row['topology_note'],
               show_outputs=row['show_outputs'],
               expected_fault=row['expected_fault'],
               osi_layer=row['osi_layer'],
               concept_tag=row['concept_tag'],
               severity=row['severity']
           )
           cases.append(case)
   ```

3. **Generate AI prompts:**
   ```python
   from ai_diagnosis_runner import DiagnosisReporter
   
   reporter = DiagnosisReporter()
   reporter.export_cases_for_ai(cases, 'ai_prompts.txt')
   ```
   This creates a file with all 30 prompts ready to send to an LLM.

4. **Send to AI (Claude, GPT-4, etc.) and collect responses** into `ai_responses/` directory

5. **Human review:** Open `review_log.csv`, evaluate each AI response:
   - Does it match the expected fault?
   - Is the confidence appropriate?
   - Are fix steps actionable?
   - Mark: Accepted / Edited / Rejected

6. **Log corrections:** Update `responsible_ai_log.md` with 5+ corrected cases

### For Students / Demonstration

1. **Load a single case:**
   ```python
   case = DiagnosisCase(case_id=2, symptom="Guest Wi-Fi can reach internal server", ...)
   ```

2. **Run the pipeline:**
   ```python
   pipeline = DiagnosisPipeline()
   result = pipeline.run_full_pipeline(case)
   print("AI Prompt:")
   print(result['ai_prompt'])
   ```

3. **Get AI diagnosis:**
   - Copy the prompt to Claude or GPT-4
   - Receive JSON response
   - Paste into code: `pipeline.set_ai_response(case, ai_json_text)`

4. **Review and test the fix:**
   - Compare AI diagnosis with expected fault
   - Decide: Accepted / Edited / Rejected
   - Record human feedback
   - Log lessons learned

---

## Design Principles

### 1. **Explainability First**
- Every AI recommendation must cite evidence (quoted show-command lines)
- Reasoning field explains why alternatives were ruled out
- Confidence level indicates how definitive the diagnosis is
- Junior engineers should understand the logic without a PhD

### 2. **Human Oversight**
- No fix is applied without human review
- Reviewer log (responsible_ai_log.md) documents corrections
- If AI confidence < 0.7, escalate to senior engineer
- Goal: build trust in AI over time

### 3. **Deterministic-First Hybrid**
- Rule checker catches obvious issues instantly (duplicate IP, interface down)
- AI only for nuanced diagnosis (multi-layer faults, protocol mismatches)
- Reduces cost, latency, and false positives

### 4. **Cisco-Grounded, Original**
- Learned from Cisco's diagnostic approach but built original methodology
- Not just pattern matching; AI explains *why* a fault would cause the symptom
- Covers Cisco-specific protocols (OSPF, EIGRP, Spanning Tree, NAT, IPSec)

### 5. **Organized and Documented**
- Code is modular and well-commented
- Cases dataset is comprehensive and tagged
- Prompts are templated and reusable
- Feedback loop is systematic (not ad-hoc notes)

---

## Key Metrics for Success

| Metric | Target |
|--------|--------|
| Case coverage | ≥30 cases across ≥8 fault types |
| Evidence quality | ≥80% of AI responses cite show-command lines |
| Human acceptance rate | ≥70% of AI diagnoses accepted on first review |
| Rule checker catch rate | Detects ≥80% of obvious issues (duplicate IP, interface down) |
| Confidence calibration | High confidence diagnoses have ≥85% acceptance rate |
| Responsible AI entries | ≥5 documented corrections per 30 cases |

---

## Future Enhancements

1. **Dashboard visualization** — Plot acceptance rate by concept, severity heatmap
2. **Feedback loop** — Use corrected cases to fine-tune prompts
3. **Multi-model comparison** — Test Claude vs. GPT-4 vs. Llama accuracy
4. **Network simulation** — Auto-verify fixes in Cisco Packet Tracer
5. **Confidence scoring** — ML model to predict diagnostic quality
6. **Knowledge base** — Extract patterns from all diagnosed cases

---

## Contact / Questions

For questions about the project or troubleshooting:
1. Refer to `diagnose_prompt.md` for prompt examples
2. Check `responsible_ai_log.md` for common pitfalls
3. Review `rule_checker.py` for what's deterministically checkable
4. Trace through `ai_diagnosis_runner.py` to understand the pipeline

---

**Last Updated:** 2026-08-18  
**Status:** Complete baseline, ready for AI testing and human review
