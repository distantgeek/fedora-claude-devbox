---
name: security-rust
description: Rust security scanning with cargo-audit, cargo-deny, and cargo-geiger
compatibility: opencode
---
## Commands

```bash
cargo install cargo-audit cargo-deny cargo-geiger
cargo audit --json > cargo-audit-report.json
cargo deny check
cargo geiger
```

## Common Rust Vulnerabilities

### Unsafe Code
- Minimize `unsafe` blocks. Document safety invariants with `// SAFETY:` comments
- Use cargo-geiger to measure unsafe code percentage. Flag > 5% unsafe
- Prefer safe abstractions (std, crossbeam, parking_lot) over raw unsafe

### Input Validation
- Validate all external input at trust boundaries
- Use `serde` with validation attributes. Custom deserializers for complex validation
- Sanitize path inputs to prevent traversal: check against canonical root

### Memory Safety
- Rust eliminates most memory issues, but still watch for:
  - `unwrap()` / `expect()` in non-prototype code. Use proper error handling
  - `panic!()` for recoverable errors. Return `Result` instead
  - Index out of bounds on vectors/slices. Use `.get()` for safe access
  - Recursion depth control in recursive functions

### Cryptography
- Use crates from RustCrypto project: `aes-gcm`, `chacha20poly1305`, `ed25519-dalek`
- Never: `md-5`, `sha1`, custom ciphers
- Random: `rand::rngs::OsRng` (not `thread_rng()` for security-sensitive)
- Constant-time: Use `subtle` crate for comparison operations

### Authentication & Secrets
- Passwords: `argon2` crate (argon2 crate from RustCrypto)
- Secrets: Use `dotenv`/`dotenvy` for env vars, never hardcode
- Sessions: Use secure, httpOnly, SameSite cookies
- Tokens: `jsonwebtoken` with strong secret, short expiry, algorithm validation

### Web (actix-web/axum/rocket)
- CSRF: Use CSRF middleware for state-changing requests
- XSS: Html escape. Content-Security-Policy headers
- CORS: Explicit origin allowlist, not wildcard
- Rate limiting: Per-endpoint rate limits
- Request size limits: Configure max payload size

### Dependency Security
- Pin exact versions in Cargo.toml (use `=x.y.z`, not `^x.y.z`)
- Run `cargo audit` before every commit
- Run `cargo deny check` for license + duplicate dependency checks
- Review dependency tree for minimality (`cargo tree`)
