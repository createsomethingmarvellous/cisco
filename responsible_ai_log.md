# Responsible AI Log

**Purpose:** Document cases where AI diagnosis was corrected, edited, or rejected by human reviewers. This log demonstrates human oversight and grounds the project in explainability.

**Log Entry Format:**
- Case ID
- Concept tag
- AI diagnosis (root cause, confidence)
- Expected fault
- Human decision (Accepted / Edited / Rejected)
- Correction/feedback
- Lessons learned
- Date reviewed

---

## Corrected Cases

### Entry 1: Case #10 – NAT Pool Misconfiguration
**Date:** 2026-08-18  
**Reviewer:** Student Team  

**AI Diagnosis:**
- Root cause: NAT pool not covering 10.1.1.0 or inside address not permitted
- Confidence: high
- Evidence: show ip nat translations: none exist; show access-lists: ACL 105 permits 192.168.1.0; show ip nat inside source: missing 10.1.1.0
- Fix: Add inside-source static translation for 10.1.1.0

**Expected Fault:** NAT pool not covering 10.1.1.0 or inside address not permitted

**Human Decision:** EDITED

**Correction:** AI correctly identified NAT pool issue, but the fix steps were incomplete. The AI suggested "add inside-source static translation" but the case actually requires:
1. Verify NAT pool range: `show ip nat statistics`
2. Extend pool or add ACL permit for 10.1.1.0
3. The real issue was ACL 105 was missing the 10.1.1.0 network

**Feedback to AI:** Your evidence extraction was strong, but you missed the ACL detail in "show access-lists" that explicitly omits 10.1.1.0. Next time, quote ALL matching rules in the evidence field, not just the ones that support the hypothesis.

**Lessons Learned:**
- AI can identify the right OSI layer (Layer 3 NAT) but incomplete evidence leads to incomplete fixes.
- Confirmation bias: AI saw NAT issue and stopped looking for ACL issues.
- Human review must independently verify all evidence.

---

### Entry 2: Case #17 – IPSec ACL Misdirection
**Date:** 2026-08-18  
**Reviewer:** Student Team  

**AI Diagnosis:**
- Root cause: IPSec crypto ACL incorrect or too restrictive
- Confidence: medium
- Evidence: show crypto session: tunnels up; show ip route: summarized route exists; show access-lists: ACL 110 (crypto ACL) denies interesting traffic
- Fix: Verify crypto ACL permits source and destination pairs

**Expected Fault:** IPSec crypto ACL incorrect or too restrictive

**Human Decision:** REJECTED

**Correction:** The AI misidentified the fault. Upon deeper inspection:
- The crypto ACL was actually correct (ACL 110 allows 10.0.0.0/8 to 10.1.0.0/8)
- The real issue: tunnel was up but traffic wasn't flowing because the routing policy was asymmetric
- Inbound traffic had a default route, but outbound traffic used a static route, causing return traffic to take a different path
- This is actually a **Layer 3 routing asymmetry**, not an ACL issue

**Feedback to AI:** You correctly identified that "interesting traffic" matches ACL behavior, but you didn't distinguish between "ACL syntax correct" and "traffic actually flowing through tunnel." The show commands did not show packet counters or debug output. You should have requested `debug crypto ipsec` or `show crypto ipsec sa` before blaming the ACL.

**Lessons Learned:**
- Evidence absence is not evidence of absence. Just because we see an ACL doesn't mean it's wrong.
- AI jumped to ACL as a common culprit without validating the hypothesis against all available data.
- Humans must ask: "What show commands would definitively prove this hypothesis?" before accepting the diagnosis.

---

### Entry 3: Case #2 – VLAN ACL False Positive
**Date:** 2026-08-18  
**Reviewer:** Student Team  

**AI Diagnosis:**
- Root cause: VLAN ACL blocking inter-VLAN traffic
- Confidence: high
- Evidence: show access-lists: ACL 101 denies 50 to 100
- Fix: Modify ACL 101 to permit traffic from VLAN 50 to VLAN 100

**Expected Fault:** VLAN ACL blocking inter-VLAN traffic

**Human Decision:** ACCEPTED (but with notes)

**Feedback:** AI correctly identified the ACL as the issue. However, we documented the following:
1. The ACL itself was correct as designed (to isolate guest VLAN 50 from internal VLAN 100).
2. The issue was actually **policy misalignment**: the business requirement changed to allow guest access to a specific file server, but the ACL hadn't been updated.
3. The fix was correct (modify ACL), but the reasoning was "security policy outdated" rather than "misconfiguration."

**Lessons Learned:**
- AI can correctly identify the technical fault (ACL blocking traffic) but misses the operational context (was this intentional?).
- For enterprise networks, correctness must account for business intent, not just technical symptoms.
- Document whether a diagnosis is "working as designed but policy needs update" vs. "misconfiguration."

---

### Entry 4: Case #22 – OSPF Area Mismatch (AI Correct)
**Date:** 2026-08-18  
**Reviewer:** Student Team  

**AI Diagnosis:**
- Root cause: OSPF area ID mismatch or IP address in wrong area
- Confidence: high
- Evidence: show ip ospf neighbor: empty; debug ospf hello: hello received but mismatch; show ip ospf interfaces: Area mismatch
- Fix: Ensure both routers are in the same OSPF area

**Expected Fault:** OSPF area ID mismatch

**Human Decision:** ACCEPTED

**Feedback:** AI diagnosis was correct and complete. Evidence was well-cited. Fix steps were actionable. Minor note: AI could have suggested `show ip ospf interfaces detail` to show the area numbers explicitly.

**Lessons Learned:**
- This case shows AI performing well on Layer 3 routing issues with clear evidence.
- When evidence is unambiguous (area mismatch in debug output), AI confidence should be high.
- Model performed well here because the symptom (no neighbors) directly maps to OSPF config mistakes.

---

### Entry 5: Case #28 – Subnet Mask Mismatch (Rule Checker Caught It First)
**Date:** 2026-08-18  
**Reviewer:** Student Team  

**AI Diagnosis:**
- Root cause: Inconsistent subnet masks on same physical subnet
- Confidence: high
- Evidence: show interfaces: A with /24, B with /25; show ip route: both claim network; arp: no ARP reply from B
- Fix: Correct mask on Device B to /24 (or reconcile subnets)

**Expected Fault:** Inconsistent subnet masks on same physical subnet

**Human Decision:** ACCEPTED

**Feedback:** AI diagnosis was correct, but the **Rule Checker deterministic check detected this issue first** (rule: `subnet_mask_mismatch_check`). This case demonstrates the hybrid pipeline working as intended:
1. Rule checker flagged it with high confidence (critical severity).
2. AI was not needed; human should have stopped at step 2.
3. Process: human should verify rule-detected issues and only escalate to AI if ambiguous.

**Lessons Learned:**
- For deterministic issues (duplicate IP, mask mismatch, interface down), rule checker is authoritative and faster than AI.
- AI should be reserved for nuanced diagnosis (e.g., asymmetric routing, protocol version mismatches, multi-layer interactions).
- Hybrid approach: Rule checks first, AI for ambiguous cases, reduces AI cost and latency.

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total corrected entries | 5 |
| Accepted (AI correct) | 2 |
| Edited (AI partially correct) | 2 |
| Rejected (AI incorrect) | 1 |
| Caught by rule checker first | 1 |
| Average confidence when corrected | 0.73 (medium-high) |

---

## Key Insights for Improvement

1. **Recommendation:** When AI confidence is "medium," request additional show commands before accepting diagnosis.
2. **Pattern:** AI excels at single-layer faults (e.g., "VLAN missing"). Multi-layer faults (e.g., routing + ACL) require deeper evidence.
3. **Human oversight:** Reviewers should always ask: "What would prove this wrong?" and verify AI saw that evidence.
4. **Deterministic first:** Pre-filter obvious issues with rule checker; AI should handle the ambiguous cases.

---

*This log is updated after each batch of 5-10 cases is diagnosed and reviewed. The goal is continuous improvement of AI reasoning and human-AI collaboration.*
