---
name: security-iac
description: IaC security with checkov, kube-linter, and CIS K8s Benchmark rules
compatibility: opencode
---
## Commands

```bash
pip install checkov
checkov -d . --output json > checkov-report.json
kube-linter lint . --format json > kube-linter-report.json
```

## CIS Kubernetes Benchmark Checklist

### Pod Security
- [ ] `securityContext.runAsNonRoot: true`
- [ ] `securityContext.runAsUser` > 10000
- [ ] `securityContext.readOnlyRootFilesystem: true`
- [ ] `securityContext.allowPrivilegeEscalation: false`
- [ ] `securityContext.capabilities.drop: [ALL]`
- [ ] `seccompProfile.type: RuntimeDefault`
- [ ] Resources: requests and limits defined (CPU + memory)
- [ ] Liveness and readiness probes configured

### Secrets
- [ ] No secrets in plain YAML. Use External Secrets Operator or Vault
- [ ] encryption-provider-config configured at cluster level
- [ ] `automountServiceAccountToken: false` when API access not needed

### Network
- [ ] NetworkPolicy defined with default deny
- [ ] Only required ingress/egress allowlisted
- [ ] No hostNetwork, hostPID, hostIPC unless justified

### RBAC
- [ ] ServiceAccount per component, not shared
- [ ] Roles scoped to minimum required resources
- [ ] No cluster-admin for application workloads
- [ ] ClusterRoleBindings limited to system components

### Deployment Security
- [ ] `replicas` >= 2 for production workloads
- [ ] `strategy.type: RollingUpdate` (not Recreate) for stateful workloads
- [ ] `podAntiAffinity` for HA across nodes/zones
- [ ] `terminationGracePeriodSeconds` adequate for cleanup
- [ ] Init containers for pre-flight checks

## Common IaC Misconfigurations (K8s)
- [ ] No securityContext at all → Fix: add securityContext
- [ ] privileged: true → Fix: remove, use specific capabilities
- [ ] hostPath volumes → Fix: use PVC/persistent volumes
- [ ] hostPort → Fix: use Service + ingress
- [ ] No resource limits → Fix: add requests/limits

## Common IaC Misconfigurations (Terraform)
- [ ] AWS S3 bucket public access
- [ ] Security group with 0.0.0.0/0 ingress on sensitive ports
- [ ] RDS not encrypted at rest
- [ ] IAM policies with `*` resource/action
- [ ] No logging enabled (CloudTrail, VPC Flow Logs, S3 access logs)
- [ ] Hardcoded credentials in provider blocks
