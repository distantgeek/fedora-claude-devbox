---
name: security-python
description: Python security scanning with bandit, pip-audit, and OWASP Python-specific patterns
compatibility: opencode
---
## Commands

```bash
pip install bandit pip-audit
bandit -r . -f json -o bandit-report.json
pip-audit --format json -o pip-audit-report.json
```

## Common Python Vulnerabilities

### Injection
- SQL: Use parameterized queries (`cursor.execute("SELECT * FROM t WHERE id = %s", (id,))`). Never f-strings or %
- Command: Use `subprocess.run(args, shell=False)`. Never `os.system()` or `shell=True` with user input
- Template: Auto-escape in Jinja2/Django templates. Never mark_safe() with user data
- Pickle: Never unpickle untrusted data. Use JSON instead
- XML: Use defusedxml for XML parsing to prevent XXE/billion laughs

### Authentication & Cryptography
- Passwords: Use `django.contrib.auth.hashers` or `bcrypt`/`argon2-cffi`. Never SHA/MD5
- Secrets: Use `python-decouple`, `pydantic-settings`, or `django-environ`. Never hardcode
- Random: Use `secrets` module (not `random`). `secrets.token_urlsafe()` for tokens
- Crypto: Use `cryptography` library (not `pycrypto`, not `pycryptodome`)

### File & Path Safety
- Path traversal: Use `pathlib.Path` and validate against a root directory. Never raw string concatenation
- File uploads: Validate type, size, and scan content. Store outside web root
- Temporary: Use `tempfile.mkstemp()` (not `tempfile.mktemp()`)

### Web (Django/Flask/FastAPI)
- CSRF: Django CSRF middleware enabled. FastAPI/Flask use CSRF tokens
- XSS: Escape output. Never `mark_safe()` with user data. Set Content-Security-Policy headers
- CORS: Explicit allowlist, not `*`. django-cors-headers configured properly
- Debug: `DEBUG=False` in production. No `display_details()` in error handlers
- Secrets: `SECRET_KEY` from env var, 50+ chars, cryptographically random

### Dependency Security
- Pin exact versions in requirements.txt or pyproject.toml
- Run pip-audit before every commit
- Remove unused dependencies (pip-autoremove or manual)
- Review dependency licenses for compliance

## Bandit Severity Thresholds
- HIGH: Block merge (subprocess, hardcoded passwords, SQL injection, yaml.load, pickle)
- MEDIUM: Fix this sprint (http not https, tempfile.mktemp, assert used, hardcoded tmp dir)
- LOW: Document (hashlib.md5 for non-crypto, flask debug true, telnet)
