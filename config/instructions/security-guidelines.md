# Security Guidelines (ISO 27001 + NIST SP 800-218)

## NIST SP 800-218 — Secure Software Development Framework (SSDF)

### Prepare the Organization (PO)
- PO.1: Define security requirements for software development.
- PO.2: Implement roles and responsibilities for security.
- PO.3: Implement supporting tooling (SAST, DAST, SCA, secret scanning).
- PO.4: Define criteria for software security checks.
- PO.5: Implement and maintain secure environments for development.

### Protect the Software (PS)
- PS.1: Protect all forms of code from unauthorized access and tampering.
- PS.2: Provide a mechanism for verifying software release integrity.
- PS.3: Archive and protect each software release.

### Produce Well-Secured Software (PW)
- PW.1: Design software to meet security requirements and mitigate threats.
- PW.2: Review software design to verify compliance with security requirements.
- PW.3: Reuse existing, well-secured software when feasible.
- PW.4: Write code following secure coding practices.
- PW.5: Configure compilation and build processes to improve security.
- PW.6: Review and analyze human-readable code to identify vulnerabilities.
- PW.7: Test executable code to identify vulnerabilities.
- PW.8: Configure software to have secure settings by default.

### Respond to Vulnerabilities (RV)
- RV.1: Identify and confirm vulnerabilities on an ongoing basis.
- RV.2: Assess, prioritize, and remediate vulnerabilities.
- RV.3: Analyze root causes of vulnerabilities and improve processes.

## ISO 27001 (Information Security Management) — Key Controls

### A.5 Information Security Policies
- Maintain and review security policies regularly.
- All code changes must align with organizational security policy.

### A.8 Asset Management
- Identify and classify information assets (code, data, configs).
- Define acceptable use of assets.

### A.9 Access Control
- Implement least privilege access to code repositories.
- Enforce MFA for all repository access.
- Regular access reviews.

### A.12 Operations Security
- Separate development, testing, and production environments.
- Implement change management procedures (traceable commits, PR reviews).
- Log and monitor all operations.

### A.14 System Acquisition, Development, and Maintenance
- Security requirements must be part of the SDLC.
- Secure coding principles applied throughout development.
- Security testing before deployment.
- No live data in test environments.

### A.16 Information Security Incident Management
- Document security incidents.
- Learn from incidents to prevent recurrence.

## OWASP Top 10 — Key Patterns

1. **Broken Access Control**: Check auth on every endpoint. Deny by default.
2. **Cryptographic Failures**: Classify data sensitivity. Encrypt at rest and transit.
3. **Injection**: Parameterize queries. Validate all input. Escape output.
4. **Insecure Design**: Threat model. Limit resource consumption.
5. **Security Misconfiguration**: Harden defaults. Remove debug endpoints.
6. **Vulnerable Components**: Scan dependencies. Keep updated. Remove unused.
7. **Auth Failures**: Rate-limit login. Use secure session management.
8. **Software and Data Integrity Failures**: Verify integrity of dependencies.
9. **Security Logging and Monitoring Failures**: Log auth events. Monitor anomalies.
10. **SSRF**: Validate and sanitize URLs. Use allowlists for outbound requests.

## Language-Specific Guidance
When working in a specific language, always load the corresponding security skill:
- Python: load skill("security-python")
- Rust: load skill("security-rust")
- Go: load skill("security-go")
- JavaScript/TypeScript: load skill("security-javascript")
- Docker: load skill("security-docker")
- K8s/IaC: load skill("security-iac")
