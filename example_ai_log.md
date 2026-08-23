
### Entry: Case #2 – vlan-acl
**Date:** 2026-08-18  
**Reviewer:** Example Workflow  

**AI Diagnosis:**
- Root cause: VLAN ACL blocking inter-VLAN traffic
- Confidence: high

**Expected Fault:** VLAN ACL blocking inter-VLAN traffic

**Human Decision:** ACCEPTED

**Feedback:** Correct diagnosis. The ACL is clearly the issue. Fix steps are clear and safe to apply. Confidence 'high' is justified by the evidence.

**Notes:** This is a policy mismatch case—the ACL was correctly configured to isolate guest traffic, but business requirements changed. Senior engineer should review whether the security exception is warranted.

**Lessons Learned:**
- Rule checker did not flag this (no deterministic violation).
- AI reasoning was sound and correctly identified the ACL as the barrier.
- Human value-add: contextualizing whether this is misconfiguration or policy update.
