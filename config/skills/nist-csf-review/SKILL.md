---
name: nist-csf-review
description: Map current changes to NIST CSF categories and SP 800-218 SSDF phases
compatibility: opencode
---
## NIST Cybersecurity Framework (CSF) Mapping

Review code changes and map them to NIST CSF functions:

### IDENTIFY
- [ ] Asset management: Is new code tracking information assets?
- [ ] Risk assessment: Has the change introduced new risks?
- [ ] Governance: Does the change align with security policies?

### PROTECT
- [ ] Access control: Are permissions properly scoped?
- [ ] Awareness: Is security-adjacent code documented?
- [ ] Data security: Is sensitive data encrypted at rest and in transit?
- [ ] Maintenance: Are dependencies updated and secure?
- [ ] Protective technology: Are security headers/configurations applied?

### DETECT
- [ ] Anomalies: Is error/exception logging in place?
- [ ] Continuous monitoring: Are health checks/metrics exposed?
- [ ] Detection processes: Can security events be identified?

### RESPOND
- [ ] Response planning: Are error conditions handled gracefully?
- [ ] Mitigation: Do failures degrade safely?
- [ ] Improvements: Are learnings applied from past incidents?

### RECOVER
- [ ] Recovery planning: Can state be restored after failure?
- [ ] Communication: Are recovery procedures documented?

## NIST SP 800-218 SSDF Phase Mapping

### Prepare (PO)
- [ ] PO.1: Security requirements defined for this feature?
- [ ] PO.2: Security roles assigned?
- [ ] PO.3: Tooling available (linters, scanners, test frameworks)?
- [ ] PO.4: Security check criteria defined?

### Protect (PS)
- [ ] PS.1: Code protected from unauthorized access?
- [ ] PS.2: Release integrity mechanism (signatures/checksums)?
- [ ] PS.3: Release artifacts archived?

### Produce (PW)
- [ ] PW.1: Security requirements in design?
- [ ] PW.2: Design reviewed for security compliance?
- [ ] PW.4: Secure coding practices followed?
- [ ] PW.5: Build process secure?
- [ ] PW.6: Code reviewed for vulnerabilities?
- [ ] PW.7: Code tested for vulnerabilities?
- [ ] PW.8: Secure defaults configured?

### Respond (RV)
- [ ] RV.1: Vulnerability identification ongoing?
- [ ] RV.2: Vulnerability assessment and remediation planned?
- [ ] RV.3: Root cause analysis process in place?

## Output Format
For each change, report:
- CSF Function(s) impacted
- SSDF Phase(s) applicable
- Any gaps identified
- Recommended actions
