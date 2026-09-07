---
name: security-go
description: Go security scanning with gosec, govulncheck, and Go-specific patterns
compatibility: opencode
---
## Commands

```bash
go install github.com/securego/gosec/v2/cmd/gosec@latest
go install golang.org/x/vuln/cmd/govulncheck@latest
gosec -fmt=json -out=gosec-report.json ./...
govulncheck -json ./... > govulncheck-report.json
```

## Common Go Vulnerabilities

### Injection
- SQL: Use `database/sql` with placeholders (`$1`, `$2` or `?`). Never fmt.Sprintf for queries
- Command: Use `exec.Command(name, arg...)` with separate args. Never `exec.Command("sh", "-c", userInput)`
- Template: Use `html/template` for HTML output (auto-escapes). Only use `text/template` for non-HTML

### Authentication & Secrets
- Passwords: Use `golang.org/x/crypto/bcrypt`. Cost factor >= 12
- Secrets: Use `os.Getenv()` or `envconfig`. Never hardcode
- Random: Use `crypto/rand` (not `math/rand`). `crypto/rand.Read()` for tokens
- Crypto: Use `crypto/aes` with GCM mode. `crypto/sha256`. Never `crypto/md5` or `crypto/sha1`
- JWT: Use `github.com/golang-jwt/jwt/v5`. Validate algorithm, expiry, issuer

### File & Path Safety
- Path traversal: Use `filepath.Clean()` and verify result is within intended directory
- Temporary: Use `os.CreateTemp()` (not `ioutil.TempFile()` which is deprecated)
- Permissions: Explicitly set file permissions. Don't use 0777

### Web (net/http/gin/echo)
- CSRF: Use gorilla/csrf middleware for state-changing requests
- XSS: html/template auto-escapes. Content-Security-Policy headers
- CORS: Explicit origin allowlist, not wildcard
- Timeouts: Set ReadTimeout, WriteTimeout, IdleTimeout on http.Server
- Rate limiting: Use `golang.org/x/time/rate` or middleware

### Error Handling
- Never discard errors with `_`. Handle or propagate every error
- Do not expose internal errors to clients (stack traces, SQL errors)
- Log errors server-side, return generic messages to clients

### Dependency Security
- Use go modules with exact versions
- Run `govulncheck ./...` before every commit
- Remove unused imports (goimports)
- Minimize dependency count
