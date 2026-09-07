---
name: testing-iac
description: IaC testing with terraform test, conftest, and validation tooling
compatibility: opencode
---
## Quick Setup

```bash
# conftest (Open Policy Agent-based policy checks)
curl -LO https://github.com/open-policy-agent/conftest/releases/latest/download/conftest_linux_amd64.deb
sudo dpkg -i conftest_linux_amd64.deb

# tflint (Terraform linter)
curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
```

## Test Structure Convention

```
infra/
├── main.tf
├── variables.tf
├── outputs.tf
├── tests/
│   └── main.tftest.hcl     # Terraform test files
├── policy/                  # OPA/Conftest policy files
│   └── security.rego
└── .tflint.hcl              # tflint configuration
```

## Terraform Test Example

```hcl
# tests/main.tftest.hcl
run "validate_s3_bucket" {
  command = plan

  assert {
    condition     = aws_s3_bucket.main.force_destroy == false
    error_message = "S3 bucket must not allow force destroy"
  }

  assert {
    condition     = aws_s3_bucket.main.server_side_encryption_configuration[0].rule[0].apply_server_side_encryption_by_default[0].sse_algorithm == "AES256"
    error_message = "S3 bucket must have SSE enabled"
  }
}

run "validate_security_group" {
  command = plan

  assert {
    condition     = length([for r in aws_security_group.main.ingress : r if r.from_port == 22 && contains(r.cidr_blocks, "0.0.0.0/0")]) == 0
    error_message = "SSH must not be open to the world"
  }
}
```

## conftest Policy Example

```rego
# policy/security.rego
package main

deny[msg] {
  input.resource_type == "aws_s3_bucket"
  not input.resource_changes[_].change.after.encryption
  msg = "S3 buckets must have encryption enabled"
}
```

## Standard Test Commands

```bash
# Terraform validate + lint
terraform validate
tflint --recursive

# Security scanning
checkov -d . --framework terraform
checkov -d . --framework kubernetes

# Policy testing
conftest test main.tf -p policy/

# Terraform tests
terraform test
```

## Pre-Apply Checklist
- [ ] `terraform validate` passes
- [ ] `tflint` passes (no errors)
- [ ] `checkov` passes (no HIGH/CRITICAL)
- [ ] `terraform test` passes
- [ ] No secrets in Terraform state or plan files
- [ ] Encryption enabled for all storage resources
- [ ] Security groups use least-privilege rules
- [ ] IAM policies use resource-level restrictions
- [ ] Logging enabled on all managed resources
