---
name: security-javascript
description: JavaScript/TypeScript security with npm audit, eslint-plugin-security, and OWASP JS patterns
compatibility: opencode
---
## Commands

```bash
npm audit --json > npm-audit-report.json
npx eslint --plugin security .
```

## Common JavaScript/TypeScript Vulnerabilities

### Injection
- SQL: Use parameterized queries (Sequelize/Knex/Prisma parameter binding or pg `$1`). Never template literals
- NoSQL: Sanitize MongoDB queries against operator injection (`$where`, `$regex`)
- Command: Use `child_process.execFile()` (not `exec()`). Avoid `eval()`, `new Function()`
- XSS: Use React/Vue/Angular auto-escaping. Never `dangerouslySetInnerHTML`/`v-html` with user input. DOMPurify for raw HTML

### Authentication & Secrets
- Passwords: Use `bcryptjs` or `argon2`. Never plain text, never SHA
- Secrets: Use `process.env` via dotenv. Never hardcode keys. Use `dotenv-safe` to ensure required vars exist
- Sessions: Secure, httpOnly, SameSite cookies. Session secret from env
- JWT: Use `jsonwebtoken` with RS256 or HS256. Validate audience, issuer, expiry. Short TTL
- Random: Use `crypto.randomBytes()` (not `Math.random()`)

### API Security (Express/Fastify/Nest)
- Input validation: Use Zod or Joi on all request inputs. Validate types, ranges, formats
- Rate limiting: express-rate-limit or similar
- CORS: Explicit origin allowlist. Never `origin: '*'` with credentials
- Helmet: Set security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- Body size limits: Configure max request body size
- CSRF: csurf or double-submit cookie pattern

### File & Path Safety
- Path traversal: Use `path.resolve()` and verify against root directory
- File uploads: Limit size, validate MIME type, scan content, store outside web root

### React/Vue/Angular Specific
- Never use `dangerouslySetInnerHTML` or `v-html` with user-controlled data
- Sanitize URL parameters before rendering
- Validate redirect URLs (open redirect prevention)
- Keep dependencies updated (especially framework patches)

### Dependency Security
- Pin exact versions in package.json. No `^` or `~` prefixes
- Run `npm audit` before every commit
- Review `npm audit fix` carefully — breaking changes possible
- Use lockfiles (package-lock.json, yarn.lock, pnpm-lock.yaml)
- Remove unused dependencies (`npm prune`, `depcheck`)
