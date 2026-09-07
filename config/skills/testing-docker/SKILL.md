---
name: testing-docker
description: Docker image testing with container-structure-test and goss
compatibility: opencode
---
## Quick Setup

```bash
# container-structure-test
curl -LO https://storage.googleapis.com/container-structure-test/latest/container-structure-test-linux-amd64
chmod +x container-structure-test-linux-amd64
sudo mv container-structure-test-linux-amd64 /usr/local/bin/container-structure-test

# goss (server validation)
curl -fsSL https://goss.rocks/install | sh
```

## Test Structure

```
tests/
├── docker/
│   ├── image-test.yaml       # container-structure-test config
│   └── goss.yaml             # Server validation
```

## container-structure-test Example

```yaml
schemaVersion: "2.0.0"
metadataTest:
  # Verify non-root user
  env:
    - key: "PATH"
      value: "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  exposedPorts: ["8080"]
  volumes: ["/tmp"]
  entrypoint: ["/app/server"]
  cmd: ["--config", "/etc/app/config.yaml"]
  workdir: "/app"
  user: "10001"

fileExistenceTests:
  - name: "binary exists"
    path: "/app/server"
    shouldExist: true
    permissions: "-rwxr-xr-x"
  - name: "no root access files"
    path: "/root"
    shouldExist: false

fileContentTests:
  - name: "non-root user configured"
    path: "/etc/passwd"
    expectedContents: [".*appuser.*"]

commandTests:
  - name: "server starts"
    command: "/app/server"
    args: ["--version"]
    expectedOutput: ["v1."]
    exitCode: 0
```

## goss Example

```yaml
port:
  tcp:8080:
    listening: true
    ip: ["0.0.0.0"]
http:
  http://localhost:8080/health:
    status: 200
    body: ["ok"]
```

## Standard Test Command

```bash
docker build -t app:test .
container-structure-test test --image app:test --config tests/docker/image-test.yaml
```

## Pre-Deploy Checklist
- [ ] Image builds without errors
- [ ] Non-root user verified
- [ ] Setuid/setgid binaries removed
- [ ] No secrets in image layers (docker history check)
- [ ] HEALTHCHECK present
- [ ] Only necessary ports exposed
- [ ] Trivy scan passes (no CRITICAL/HIGH)
- [ ] Image signed (cosign)
