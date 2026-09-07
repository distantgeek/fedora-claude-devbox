# Bash Security Scanning

## Tools
- **shellcheck** — static analysis for bash scripts (lint + common pitfalls)

## Commands
```bash
shellcheck -x script.sh
```

## OWASP Bash-Specific Patterns

### Command Injection
- NEVER use `eval` with untrusted input
- NEVER interpolate user input into `$(...)` or backticks
- Use arrays for command arguments
- Quote all variable expansions

### Path Traversal
- Validate file paths before use
- Use `realpath` / `readlink -f` to canonicalize paths

### Secrets
- Never hardcode credentials in scripts
- Use environment variables or secret files with 0600 perms
- Never log secrets or API keys

### Input Validation
- Validate all user input before use
- Use `[[ ]]` for string comparisons
- Set `set -euo pipefail` for strict error handling

### Shell Injection via SSH/Remote
- When passing commands to remote hosts, use arrays or properly escape
- Never interpolate untrusted data into remote command strings without escaping

## Common ShellCheck Warnings to Fix
- SC2086: Double quote to prevent globbing and word splitting
- SC2046: Quote command substitutions
- SC2164: Use `cd ... || exit` to handle cd failure

## Verification
Run `shellcheck -x` on all modified bash scripts before commit.
