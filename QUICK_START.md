# QUICK START GUIDE

## Project Overview

**NetSage AI** is a network troubleshooting assistant that:
1. Takes a symptom + network show-command outputs
2. Checks for obvious faults with deterministic rules
3. Uses AI (Claude/GPT-4) to diagnose root cause
4. Requires human review before accepting the fix
5. Logs all decisions for continuous learning

**Key Features:**
- 30 real-world Cisco lab cases
- Structured prompts that force JSON output
- 8 deterministic rule checks
- Human review workflow
- Responsible AI logging (5+ corrected cases)

---

## Getting Started (5 minutes)

### 1. Verify Files Are Created

```bash
cd d:\cisco
ls -la  # On Windows: dir
```

You should see:
- `cases.csv` — 30 troubleshooting cases
- `diagnose_prompt.md` — AI prompt templates + 3 examples
- `config_parser.py` — Show-command parser
- `rule_checker.py` — Deterministic checks
- `ai_diagnosis_runner.py` — Orchestrator
- `dashboard.py` — Reporting
- `example_workflow.py` — Demo script
- `responsible_ai_log.md` — Human feedback log
- `README.md` — Full documentation

### 2. Run the Example Workflow

```bash
python example_workflow.py
```

**Output:** Demonstrates one case (#2 VLAN ACL) going through the entire pipeline:
- Case loading
- Config parsing
- Rule checks
- AI prompt generation
- AI response (simulated)
- Validation
- Human review
- Report generation
- Logging

**Files created:**
- `example_review_log.csv` — Human review decisions
- `example_ai_log.md` — Documented feedback

### 3. View the Dashboard

```bash
python dashboard.py
```

This generates `dashboard.html` with statistics on:
- Cases by concept tag
- Severity distribution
- AI vs human agreement rates
- Acceptance rates by confidence level

Open in browser: `dashboard.html`

---

## Full Workflow (Step-by-Step)

### Phase 1: Setup

```bash
# Already done, but this is the pattern:
# 1. Load cases from cases.csv
# 2. Create DiagnosisCase objects for each
# 3. Run pipeline to generate AI prompts
```

### Phase 2: AI Diagnosis

```python
from ai_diagnosis_runner import DiagnosisCase, DiagnosisPipeline

# Load case
case = DiagnosisCase(case_id=1, symptom="...", ...)

# Generate prompt
pipeline = DiagnosisPipeline()
result = pipeline.run_full_pipeline(case)

# Prompt is ready to send to Claude or GPT-4
print(result['ai_prompt'])
```

**Next:** Copy prompt to Claude or GPT-4 API

### Phase 3: Collect AI Responses

Save each response as JSON:

```
ai_responses/
├── case_001_response.json
├── case_002_response.json
└── ...
```

### Phase 4: Human Review

```python
from ai_diagnosis_runner import DiagnosisReporter, ReviewStatus

# Load case with AI response
case.ai_diagnosis = json.loads(response_json)

# Human makes decision
case.review_status = ReviewStatus.ACCEPTED  # or EDITED or REJECTED
case.human_feedback = "Correct diagnosis. Fix is safe."
case.notes = "This is a policy mismatch, not a misconfiguration."

# Generate review log
reporter = DiagnosisReporter()
reporter.create_review_log([case], 'review_log.csv')

# Log corrections
# Update responsible_ai_log.md with entry 6, 7, 8...
```

### Phase 5: Analyze Results

```python
summary = reporter.generate_summary_report(all_cases)
print(f"Acceptance rate: {summary['acceptance_rate']}%")
print(f"By concept: {summary['by_concept']}")
```

---

## Quick Reference: Key Functions

### Load Cases
```python
import csv
from ai_diagnosis_runner import DiagnosisCase

cases = []
with open('cases.csv') as f:
    for row in csv.DictReader(f):
        case = DiagnosisCase(
            case_id=int(row['case_id']),
            symptom=row['symptom'],
            # ...
        )
        cases.append(case)
```

### Run Deterministic Checks
```python
from rule_checker import RuleChecker

checker = RuleChecker()
config_data = {
    'dhcp_bindings': {...},
    'interfaces': {...},
    # ...
}
results = checker.run_all_checks(config_data)
detected_issues = checker.get_detected_issues()
```

### Generate AI Prompts
```python
from ai_diagnosis_runner import DiagnosisPipeline

pipeline = DiagnosisPipeline()
result = pipeline.run_full_pipeline(case)
print(result['ai_prompt'])  # Send to LLM
```

### Validate AI Response
```python
# Get JSON from LLM
ai_json = '{"root_cause": "...", ...}'

# Store in case
success = pipeline.set_ai_response(case, ai_json)
if success:
    print(case.ai_diagnosis['confidence'])
else:
    print("Response validation failed")
```

### Record Human Review
```python
from ai_diagnosis_runner import ReviewStatus

case.review_status = ReviewStatus.ACCEPTED
case.human_feedback = "Correct."
case.notes = ""

# Or
case.review_status = ReviewStatus.EDITED
case.human_feedback = "AI identified the right layer but missed ACL detail."

# Or
case.review_status = ReviewStatus.REJECTED
case.human_feedback = "This is actually a routing asymmetry issue, not ACL."
```

### Generate Reports
```python
from ai_diagnosis_runner import DiagnosisReporter

reporter = DiagnosisReporter()
reporter.export_cases_for_ai(cases, 'all_prompts.txt')
reporter.create_review_log(cases, 'review_log.csv')
summary = reporter.generate_summary_report(cases)
```

### Generate Dashboard
```python
from dashboard import Dashboard

dashboard = Dashboard()
dashboard.load_cases_from_csv('cases.csv')
dashboard.generate_html_report('dashboard.html', review_log)
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'ai_diagnosis_runner'`
**Solution:** Make sure you're running Python from `d:\cisco` directory
```bash
cd d:\cisco
python example_workflow.py
```

### Issue: CSV file not found
**Solution:** Verify `cases.csv` exists in `d:\cisco`
```bash
ls cases.csv  # On Windows: dir cases.csv
```

### Issue: JSON parsing error from AI response
**Solution:** Ensure AI returned valid JSON
- Check response doesn't have extra text before/after JSON
- Verify all required fields are present
- Use Python JSON validator: `json.loads(response_text)`

### Issue: Prompt too long for API
**Solution:** The full prompt with 30 cases might exceed token limits
- Process cases one at a time (recommended)
- Or batch 5-10 per request
- Use `example_workflow.py` as a template for single-case processing

---

## Example: Process One Case End-to-End

```python
# case_id 10: NAT pool issue
# symptom: PC gets IP but cannot reach server behind NAT
# expected_fault: NAT pool not covering subnet

from ai_diagnosis_runner import DiagnosisCase, DiagnosisPipeline, ReviewStatus
import json

# 1. Create case
case = DiagnosisCase(
    case_id=10,
    symptom="ping 10.1.1.1 times out; ping 192.168.1.1 works",
    topology_note="Device in 192.168.1.0/24. Trying to reach 10.1.1.1 behind NAT.",
    show_outputs="show ip nat translations: none exist; ...",
    expected_fault="NAT pool not covering 10.1.1.0 or inside address not permitted",
    osi_layer="3",
    concept_tag="nat-pool",
    severity="high"
)

# 2. Run pipeline
pipeline = DiagnosisPipeline()
result = pipeline.run_full_pipeline(case)

# 3. Send to Claude/GPT-4 and get response
# (In real use, call API here; for demo, use simulated response)
ai_response_json = '''
{
  "root_cause": "NAT pool missing 10.1.1.0 or ACL blocks it",
  "osi_layer": "3",
  "confidence": "high",
  "evidence": ["show ip nat translations: none exist", "show access-lists: ACL 105 permits 192.168.1.0"],
  "what_is_wrong": "NAT ACL or pool doesn't cover 10.1.1.0 network",
  "where_is_fault": "Router NAT config (pool or ACL)",
  "next_diagnostic_command": "show ip nat statistics",
  "fix_steps": [
    "Step 1: Check NAT pool range: 'show ip nat statistics'",
    "Step 2: Verify ACL 105 includes 10.1.1.0: 'show access-list 105'",
    "Step 3: If missing, add: 'access-list 105 permit ip 192.168.1.0 0.0.0.255 10.1.1.0 0.0.0.255'",
    "Step 4: Retest: ping 10.1.1.1 should succeed"
  ],
  "reasoning": "Show outputs clearly show NAT translations table is empty (no translations), and ACL 105 only has 192.168.1.0 in source. The destination 10.1.1.0 is missing from the ACL, preventing NAT translation."
}
'''

# 4. Validate
pipeline.set_ai_response(case, ai_response_json)

# 5. Human review
case.review_status = ReviewStatus.EDITED
case.human_feedback = "AI correctly identified ACL as the issue, but fix steps missed checking current NAT pool config first. Good diagnosis, incomplete fix."

# 6. Log
print(f"Case #{case.case_id}: {case.review_status.value}")
print(f"AI root cause: {case.ai_diagnosis['root_cause']}")
print(f"Confidence: {case.ai_diagnosis['confidence']}")
print(f"Human feedback: {case.human_feedback}")
```

---

## Expected Metrics

After running all 30 cases and collecting human reviews:

| Metric | Expected | Actual |
|--------|----------|--------|
| Total cases | 30 | ✓ |
| Cases by concept | ≥8 concepts | ✓ |
| Rule checker issues | ≥10 cases | ? |
| AI acceptance rate | ≥70% | ? |
| High confidence acceptance | ≥85% | ? |
| Responsible AI entries | ≥5 corrected | 5 (documented) |

---

## Next Steps

1. **Run example workflow** to see the full pipeline in action
2. **Modify case data** to add your own lab scenarios
3. **Connect to Claude/GPT-4 API** for real AI inference (update step 3 above)
4. **Collect human reviews** for all 30 cases
5. **Analyze results** with dashboard.py
6. **Document lessons learned** in responsible_ai_log.md
7. **Iterate prompts** based on feedback

---

## Support & Questions

Refer to:
- `README.md` — Full architecture and component descriptions
- `diagnose_prompt.md` — Prompt templates and worked examples
- `responsible_ai_log.md` — Real cases where AI was corrected
- `example_workflow.py` — Runnable demo code

---

**Last Updated:** 2026-08-18  
**Status:** Ready to use. All core components functional.
