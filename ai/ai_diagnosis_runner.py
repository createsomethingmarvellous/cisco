"""
ai_diagnosis_runner.py
Orchestrates the full diagnosis flow: filter → rule check → AI prompt → human review.
Purpose: Coordinate all components and track case-by-case results.
"""

import json
import csv
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_parser import CiscoConfigParser, ConfigAnalyzer
from checker.rule_checker import RuleChecker, DiagnosisResult


class ReviewStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class DiagnosisCase:
    """Represents a single troubleshooting case through the entire pipeline."""
    
    def __init__(self, case_id: int, symptom: str, topology_note: str, 
                 show_outputs: str, expected_fault: str, osi_layer: str, 
                 concept_tag: str, severity: str):
        self.case_id = case_id
        self.symptom = symptom
        self.topology_note = topology_note
        self.show_outputs = show_outputs
        self.expected_fault = expected_fault
        self.osi_layer = osi_layer
        self.concept_tag = concept_tag
        self.severity = severity
        
        # Results filled during pipeline
        self.parsed_config: Dict[str, Any] = {}
        self.rule_check_results: List[DiagnosisResult] = []
        self.ai_diagnosis: Optional[Dict[str, Any]] = None
        self.review_status = ReviewStatus.PENDING
        self.human_feedback: Optional[str] = None
        self.notes: str = ""
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'case_id': self.case_id,
            'symptom': self.symptom,
            'topology_note': self.topology_note,
            'expected_fault': self.expected_fault,
            'osi_layer': self.osi_layer,
            'concept_tag': self.concept_tag,
            'severity': self.severity,
            'parsed_config': self.parsed_config,
            'rule_check_results': [r.to_dict() for r in self.rule_check_results],
            'ai_diagnosis': self.ai_diagnosis,
            'review_status': self.review_status.value,
            'human_feedback': self.human_feedback,
            'notes': self.notes,
            'timestamp': self.timestamp
        }


class DiagnosisPipeline:
    """Runs the full diagnosis pipeline for a case."""
    
    def __init__(self):
        self.parser = CiscoConfigParser()
        self.analyzer = ConfigAnalyzer(self.parser)
        self.rule_checker = RuleChecker()
    
    def step_1_parse_config(self, case: DiagnosisCase) -> Dict[str, Any]:
        """Step 1: Parse show-command outputs into structured data."""
        parsed = {
            'raw_output': case.show_outputs,
            'parse_timestamp': datetime.now().isoformat()
        }
        
        # Try to extract common show-command sections
        sections = case.show_outputs.split('---')
        
        for section in sections:
            if 'show vlan' in section.lower():
                try:
                    parsed['vlans'] = self.parser.parse_show_vlan(section)
                except Exception as e:
                    parsed['vlan_parse_error'] = str(e)
            
            if 'show ip route' in section.lower():
                try:
                    parsed['routes'] = self.parser.parse_show_ip_route(section)
                except Exception as e:
                    parsed['route_parse_error'] = str(e)
            
            if 'show interfaces' in section.lower():
                try:
                    parsed['interfaces'] = self.parser.parse_show_interfaces(section)
                except Exception as e:
                    parsed['interface_parse_error'] = str(e)
            
            if 'show access' in section.lower():
                try:
                    parsed['acls'] = self.parser.parse_show_access_lists(section)
                except Exception as e:
                    parsed['acl_parse_error'] = str(e)
            
            if 'show ip dhcp' in section.lower():
                try:
                    parsed['dhcp_bindings'] = self.parser.parse_show_ip_dhcp_binding(section)
                except Exception as e:
                    parsed['dhcp_parse_error'] = str(e)
        
        case.parsed_config = parsed
        return parsed
    
    def step_2_rule_checks(self, case: DiagnosisCase) -> List[DiagnosisResult]:
        """Step 2: Run deterministic rule checks."""
        config_data = {
            'dhcp_bindings': case.parsed_config.get('dhcp_bindings', {}),
            'static_ips': [],
            'interfaces': case.parsed_config.get('interfaces', {}),
            'vlans': case.parsed_config.get('vlans', {}),
            'routes': case.parsed_config.get('routes', {}),
            'acls': case.parsed_config.get('acls', {}),
            'gateway': None,  # Would be extracted from DHCP config
            'expected_destinations': []
        }
        
        results = self.rule_checker.run_all_checks(config_data)
        case.rule_check_results = results
        
        return results
    
    def step_3_ai_diagnosis_prompt(self, case: DiagnosisCase) -> str:
        """Step 3: Generate the AI prompt (returns prompt text, not the AI response)."""
        detected_issues = [r for r in case.rule_check_results if r.detected]
        
        rule_context = ""
        if detected_issues:
            rule_context = "\n\n**Pre-diagnosis (Rule Checker):**\n"
            for issue in detected_issues:
                rule_context += f"- {issue.rule_name}: {issue.issue} (Severity: {issue.severity.value})\n"
        
        prompt = f"""You are a Cisco network troubleshooting expert. Analyze the network issue below using the given symptom, topology, and show-command outputs. Return a JSON object with these exact fields:

{{
  "faults": [
    {{
      "root_cause": "<concise description of the fault>",
      "confidence": "<low|medium|high or 0.0-1.0>",
      "evidence": ["<quoted show-command line 1>", "<quoted show-command line 2>"],
      "osi_layer": "<layer number, e.g., '2', '3', '3-4', etc.>",
      "next_command": "<one show command to verify hypothesis>",
      "fix_steps": [
        "Step 1: <action and expected result>",
        "Step 2: <action and expected result>",
        "Step 3: <verify with show command>"
      ],
      "reasoning": "<explain why you selected this root cause, considering alternative hypotheses>"
    }}
  ],
  "confidence_matrix": {{
    "layer_2": "high/medium/low assessment",
    "layer_3": "high/medium/low assessment",
    "layer_4_to_7": "high/medium/low assessment"
  }}
}}

**Case #{case.case_id}:**

Symptom: {case.symptom}

Topology Note: {case.topology_note}

Show-Command Outputs:
{case.show_outputs}

Expected Fault (for reference, do NOT use directly): {case.expected_fault}

{rule_context}

**Instructions:**
1. Extract key facts from show-command output (IP addresses, VLAN IDs, interface status, route entries, ACL rules).
2. Identify which OSI layer(s) are involved (Layer 2 = switching/VLANs; Layer 3 = routing/IP).
3. Consider common Cisco misconfigurations: duplicate IPs, missing VLAN assignments, ACL blocking, gateway mismatch, interface down.
4. List all misconfigurations found across all OSI layers.
5. Quote actual evidence from show outputs. Do NOT invent logs.
6. Confidence: low if many unknowns, medium if some evidence points to root cause, high if evidence is definitive.
7. Next command should directly test your hypothesis.
8. Fix steps should be exact configuration commands or verification actions.
9. Reasoning field must explain why this is more likely than alternatives.
10. Provide an exact, complete, and copy-pasteable Cisco IOS configuration script to fix the issue in `fix_steps` (if applicable), including 'enable' and 'configure terminal'.

Return ONLY valid JSON. No extra text.
"""
        
        return prompt
    
    def set_ai_response(self, case: DiagnosisCase, ai_response_json: str) -> bool:
        """Step 4: Parse and validate AI response."""
        try:
            ai_diagnosis = json.loads(ai_response_json)
            
            # Validate required fields
            required_fields = [
                'faults', 'confidence_matrix'
            ]
            
            for field in required_fields:
                if field not in ai_diagnosis:
                    return False
            
            case.ai_diagnosis = ai_diagnosis
            return True
        except json.JSONDecodeError:
            return False
    
    def compare_with_expected(self, case: DiagnosisCase) -> Dict[str, Any]:
        """Compare AI diagnosis with expected fault."""
        if not case.ai_diagnosis or not case.ai_diagnosis.get('faults'):
            return {'match': False, 'notes': 'No AI diagnosis available'}
        
        faults = case.ai_diagnosis.get('faults', [])
        ai_root_cause = " | ".join([f.get('root_cause', '') for f in faults]).lower()
        expected = case.expected_fault.lower()
        
        match = expected in ai_root_cause or any(expected in f.get('root_cause', '').lower() for f in faults) or any(f.get('root_cause', '').lower() in expected for f in faults)
        
        first_fault = faults[0] if faults else {}
        return {
            'match': match,
            'ai_root_cause': ai_root_cause,
            'expected_fault': case.expected_fault,
            'ai_confidence': first_fault.get('confidence'),
            'ai_osi_layer': first_fault.get('osi_layer'),
            'expected_osi_layer': case.osi_layer
        }
    
    def run_full_pipeline(self, case: DiagnosisCase) -> Dict[str, Any]:
        """Execute all diagnostic steps (except AI inference which must be done externally)."""
        self.step_1_parse_config(case)
        self.step_2_rule_checks(case)
        
        prompt = self.step_3_ai_diagnosis_prompt(case)
        
        return {
            'case_id': case.case_id,
            'parsed_config': case.parsed_config,
            'rule_check_results': [r.to_dict() for r in case.rule_check_results],
            'ai_prompt': prompt,
            'case_object': case
        }


class DiagnosisReporter:
    """Generates reports and logs for human review."""
    
    @staticmethod
    def export_cases_for_ai(cases: List[DiagnosisCase], output_file: str) -> None:
        """Export cases and prompts to a file for batch AI processing."""
        with open(output_file, 'w') as f:
            for case in cases:
                pipeline = DiagnosisPipeline()
                result = pipeline.run_full_pipeline(case)
                
                f.write(f"\n{'='*80}\n")
                f.write(f"CASE #{case.case_id}: {case.symptom[:60]}\n")
                f.write(f"{'='*80}\n")
                f.write(result['ai_prompt'])
                f.write(f"\n\n")
    
    @staticmethod
    def create_review_log(cases: List[DiagnosisCase], output_file: str) -> None:
        """Create a CSV for human review tracking."""
        with open(output_file, 'w', newline='') as f:
            fieldnames = [
                'case_id', 'concept_tag', 'symptom', 'expected_fault', 
                'ai_root_cause', 'ai_confidence', 'match', 'review_status', 
                'human_feedback', 'notes'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for case in cases:
                comparison = DiagnosisPipeline().compare_with_expected(case)
                
                writer.writerow({
                    'case_id': case.case_id,
                    'concept_tag': case.concept_tag,
                    'symptom': case.symptom,
                    'expected_fault': case.expected_fault,
                    'ai_root_cause': comparison.get('ai_root_cause', 'N/A'),
                    'ai_confidence': comparison.get('ai_confidence', 'N/A'),
                    'match': comparison.get('match', False),
                    'review_status': case.review_status.value,
                    'human_feedback': case.human_feedback or '',
                    'notes': case.notes
                })
    
    @staticmethod
    def generate_summary_report(cases: List[DiagnosisCase]) -> Dict[str, Any]:
        """Generate high-level statistics."""
        total_cases = len(cases)
        accepted = sum(1 for c in cases if c.review_status == ReviewStatus.ACCEPTED)
        edited = sum(1 for c in cases if c.review_status == ReviewStatus.EDITED)
        rejected = sum(1 for c in cases if c.review_status == ReviewStatus.REJECTED)
        pending = sum(1 for c in cases if c.review_status == ReviewStatus.PENDING)
        
        # Group by concept
        concepts = {}
        for case in cases:
            if case.concept_tag not in concepts:
                concepts[case.concept_tag] = {'total': 0, 'accepted': 0, 'edited': 0, 'rejected': 0}
            concepts[case.concept_tag]['total'] += 1
            if case.review_status == ReviewStatus.ACCEPTED:
                concepts[case.concept_tag]['accepted'] += 1
            elif case.review_status == ReviewStatus.EDITED:
                concepts[case.concept_tag]['edited'] += 1
            elif case.review_status == ReviewStatus.REJECTED:
                concepts[case.concept_tag]['rejected'] += 1
        
        return {
            'total_cases': total_cases,
            'accepted': accepted,
            'edited': edited,
            'rejected': rejected,
            'pending': pending,
            'acceptance_rate': round(accepted / total_cases * 100, 1) if total_cases > 0 else 0,
            'by_concept': concepts
        }


if __name__ == '__main__':
    # Example: load cases and run pipeline
    cases = []
    
    # Placeholder: would load from cases.csv
    test_case = DiagnosisCase(
        case_id=1,
        symptom="PC1 gets IP but cannot ping PC2",
        topology_note="Two VLANs",
        show_outputs="show vlan brief: VLAN 10, 20 active\n--- show ip route: missing route",
        expected_fault="Inter-VLAN routing not configured",
        osi_layer="3",
        concept_tag="inter-vlan-routing",
        severity="high"
    )
    cases.append(test_case)
    
    pipeline = DiagnosisPipeline()
    result = pipeline.run_full_pipeline(test_case)
    
    print("Prompt generated for case:")
    print(result['ai_prompt'][:200] + "...")
    
    reporter = DiagnosisReporter()
    summary = reporter.generate_summary_report(cases)
    print(f"\nSummary: {summary}")
