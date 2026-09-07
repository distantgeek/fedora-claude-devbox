## Subagent Delegation

Always delegate specialized tasks to the appropriate subagent instead of performing them yourself:

- **@security-auditor**: Security vulnerabilities, CVE checks, dependency audits, Docker/K8s/IaC security, hardcoded secrets, injection patterns, cryptography review
- **@code-reviewer**: Code quality reviews, SOLID compliance, readability, complexity, error handling, test coverage evaluation
- **@docs-writer**: Writing or updating README, API docs, architecture docs, contributing guides, inline documentation
- **@refactor**: Code restructuring without behavior changes, extracting functions, renaming, consolidating duplicates
- **@project-auditor**: Full codebase audits, hallucination risk detection, structural analysis, comprehensive security scanning
- **@spec-assessor**: Spec validation, ambiguity detection, contradiction finding, completeness checks, scope creep identification
- **@verifier**: Output verification, import existence checks, API reference validation, CVE claim confirmation, config schema cross-referencing, false finding detection

Use the Task tool to invoke subagents. Match the task to the subagent's specialization — do not attempt security audits, code reviews, or documentation tasks yourself when a specialized subagent is available.

## Automatic Verification

Always invoke @verifier after these subagents complete their work:

- **@security-auditor** → @verifier: Verify CVE claims, package references, security patterns
- **@refactor** → @verifier: Verify refactored code compiles, tests pass, no behavior change
- **@project-auditor** → @verifier: Verify import existence, scanner findings accuracy

For other subagents, invoke @verifier on-demand when hallucination risk is suspected.

## Hallucination Learning

Before starting any task, review `hallucination-lessons.md` for relevant known hallucination patterns to avoid repeating known mistakes. (The `hallucination-memory` MCP is currently offline; re-enable when that project is revisited.)