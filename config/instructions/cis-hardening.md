# CIS Hardening Guidelines

## CIS Docker Benchmark

### Host Configuration
- Use a dedicated Docker host, not a general-purpose server.
- Secure the Docker daemon socket (only authorized users).
- Enable Docker Content Trust (DOCKER_CONTENT_TRUST=1).
- Restrict network traffic between containers (use custom bridge networks).

### Docker Daemon Configuration
- Run Docker in rootless mode when possible.
- Enable user namespace support (userns-remap).
- Set default ulimits for containers.
- Enable audit logging for the Docker daemon.
- Configure centralized logging (json-file or journald).

### Container Images
- Use minimal base images (alpine, distroless, scratch).
- Never use the `latest` tag — pin exact versions.
- Remove setuid/setgid permissions from images.
- HEALTHCHECK instruction in every container.
- Scan images for vulnerabilities before deployment (trivy, grype).
- Sign images using Docker Content Trust or cosign.
- Use multi-stage builds to minimize attack surface.

### Container Runtime
- Run containers as non-root user (USER directive).
- Mount filesystems as read-only when possible (--read-only).
- Do not mount the Docker socket inside containers.
- Do not use privileged containers. Capabilities: drop ALL, add only required.
- Limit container memory and CPU (--memory, --cpus).
- Set restart policy to on-failure with max retries.
- Do not expose privileged ports (< 1024). Use port mapping.
- Bind mounts should be read-only unless write is required.

### Networking
- Use custom bridge networks for inter-container communication.
- Do not expose ports unless necessary.
- Encrypt container network traffic when crossing trust boundaries.

## CIS Kubernetes Benchmark

### API Server
- Anonymous auth: disabled (--anonymous-auth=false).
- Always pull images (--AlwaysPullImages admission plugin).
- Enable security context denial (--PodSecurityPolicy or admission plugin).
- Set authorization mode to RBAC + Node.
- Enable audit logging.

### Controller Manager
- Use service account credentials (--use-service-account-credentials=true).
- Set terminated pod GC threshold.

### Scheduler
- Disable profiling (--profiling=false).

### Etcd
- Enable client certificate authentication.
- Enable peer client certificate authentication.
- Restrict etcd access to API server only.

### Pod Security
- readOnlyRootFilesystem: true (unless temporary writable dirs needed).
- runAsNonRoot: true.
- runAsUser > 10000 (not root, not system UIDs).
- Drop all capabilities, add only required ones.
- Seccomp profile: RuntimeDefault or custom.
- AppArmor/SELinux profile where supported.
- Do not use hostPath volumes unless absolutely necessary.
- Do not use hostNetwork or hostPID.
- Resource limits (CPU and memory) must be defined.
- Liveness and readiness probes configured.

### Network Policies
- Default deny all ingress/egress.
- Allowlist only required pod-to-pod communication.
- Restrict external egress to approved endpoints.

### Secrets Management
- Use Kubernetes secrets only for non-sensitive config. Use external secret stores (Vault, Sealed Secrets, External Secrets Operator) for credentials.
- Encrypt secrets at rest (EncryptionConfiguration).
- Rotate secrets regularly.

### RBAC
- Principle of least privilege for all roles.
- Avoid cluster-admin for application workloads.
- Service accounts per component, not shared.
- AutomountServiceAccountToken: false when not needed.

### Logging & Monitoring
- Enable audit logging and ship to central SIEM.
- Monitor cluster events for security anomalies.
- Enable Pod Security Admission (PSA) in enforce mode.

## CIS Linux Host Benchmark

### Filesystem
- /tmp mounted with noexec, nosuid, nodev.
- /var and /var/log on separate partitions.
- Sticky bit on world-writable directories.

### System Access
- SSH: disable root login, disable password auth (keys only).
- Enforce password complexity (PAM pwquality).
- Set account lockout after failed attempts.
- Remove/disable unused accounts and services.

### Audit & Logging
- auditd enabled and configured.
- Log sudo usage, authentication events, file deletions.
- Centralized log collection (rsyslog/journald forward).

### Network
- Disable unused network protocols (DCCP, SCTP, RDS, TIPC).
- Enable firewall (iptables/nftables). Default deny, allowlist.
- Disable IP forwarding unless needed.
- Rate-limit incoming connections (fail2ban).

### Maintenance
- Automatic security updates configured (unattended-upgrades/dnf-automatic).
- Regular filesystem integrity checks (AIDE or equivalent).
