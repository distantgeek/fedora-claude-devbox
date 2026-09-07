---
name: testing-coverage
description: Per-language coverage enforcement thresholds and commands
compatibility: opencode
---
## Coverage Thresholds

| Language | Lines | Branches | Critical Paths | Command |
|---|---|---|---|---|
| Python | 80% | — | 90% | `pytest --cov=. --cov-fail-under=80` |
| Rust | 80% | 70% | 90% | `cargo tarpaulin --fail-under 80` |
| Go | 80% | — | 90% | `go test -coverprofile=... && go tool cover -func` |
| TypeScript | 80% | 80% | 90% | `jest --coverage --coverageThreshold` |
| JavaScript | 80% | 80% | 90% | `jest --coverage --coverageThreshold` |
| Java | 80% | 70% | 90% | JaCoCo or `mvn test jacoco:report` |
| C/C++ | 70% | 60% | 80% | gcov/lcov |

## Critical Path Definition
Code is "critical path" if it handles:
- Authentication and authorization
- Cryptographic operations
- Payment processing
- PII/sensitive data handling
- Input validation and sanitization
- Error handling for security-sensitive operations

## Enforcement
- Coverage below threshold → commit guard blocks
- Critical path coverage below 90% → blocks even if overall passes
- Coverage must not decrease from previous run

## Coverage Report
```bash
# After running tests:
cat coverage-report.txt
# Look for: "Coverage: XX% (threshold: YY%) - PASS/FAIL"
```

## Coverage Ignore Patterns
Appropriate to exclude from coverage:
- Generated code (protobuf, OpenAPI clients)
- Configuration constants
- Simple getters/setters (only if truly trivial)
- Third-party integration boilerplate (documented)
