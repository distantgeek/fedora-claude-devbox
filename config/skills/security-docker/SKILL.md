---
name: security-docker
description: Docker security scanning with hadolint, trivy, and CIS Docker Benchmark rules
compatibility: opencode
---
## Commands

```bash
hadolint Dockerfile -f json > hadolint-report.json
trivy image --severity HIGH,CRITICAL IMAGE_NAME -f json -o trivy-report.json
```

## CIS Docker Benchmark Checklist

### Image Build
- [ ] Base image pinned to exact digest, not tag. No `:latest`
- [ ] Multi-stage build used to minimize final image size
- [ ] Non-root user created and used (USER directive)
- [ ] HEALTHCHECK instruction present
- [ ] No secrets in build context (use .dockerignore, multi-stage, or build secrets)
- [ ] Minimal packages installed (no dev tools, compilers in final image)
- [ ] setuid/setgid permissions removed from binaries
- [ ] Image signed (cosign or Docker Content Trust)

### Runtime
- [ ] Container runs as non-root user
- [ ] Read-only root filesystem (--read-only) unless writable dirs needed
- [ ] No privileged mode (--privileged=false)
- [ ] Capabilities dropped: --cap-drop=ALL, --cap-add=only_required
- [ ] No host network (--network=host) unless explicitly justified
- [ ] Resource limits: --memory, --cpus, --pids-limit
- [ ] Restart policy: --restart=on-failure:N
- [ ] No Docker socket mounted inside container
- [ ] Sensitive mounts: /proc (ro), /sys (ro), tmpfs for /tmp
- [ ] Seccomp/AppArmor/SELinux profile applied

### Networking
- [ ] Custom bridge networks for inter-container communication
- [ ] Only necessary ports exposed (no --expose=*)
- [ ] TLS for inter-container communication when crossing trust boundaries

## Hadolint Rules (Key)
- DL3006: Always tag version explicitly
- DL3007: Use :latest only when external tracking necessary
- DL3018: Pin versions in apk add (use `=`)
- DL3025: Use JSON array for CMD/ENTRYPOINT
- DL4001: Specify non-root USER
- DL3059: Use COPY --chown to set ownership

## Trivy Thresholds
- CRITICAL: Block merge. Fix immediately.
- HIGH: Fix before production deploy.
- MEDIUM: Fix this sprint.
