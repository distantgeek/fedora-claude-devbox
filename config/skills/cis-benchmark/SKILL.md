---
name: cis-benchmark
description: Full CIS Docker + Kubernetes + Linux hardening checklist and audit guide
compatibility: opencode
---
## CIS Docker Benchmark

### Host
- [ ] Dedicated Docker host (not shared with other services)
- [ ] Docker socket permissions restricted (docker group audited)
- [ ] DOCKER_CONTENT_TRUST=1 enforced
- [ ] Custom bridge networks (default bridge disabled)
- [ ] Docker daemon audit logging enabled
- [ ] Centralized logging configured

### Daemon
- [ ] Rootless mode or userns-remap enabled
- [ ] Default ulimits configured
- [ ] No insecure registries (--insecure-registry=[])

### Images
- [ ] Only signed images pulled (DCT or cosign)
- [ ] No :latest tags in production
- [ ] Minimal base images
- [ ] HEALTHCHECK in every image
- [ ] Vulnerability scanned before deploy

### Runtime
- [ ] Non-root user (USER)
- [ ] --read-only when possible
- [ ] No --privileged
- [ ] --cap-drop=ALL --cap-add=only_required
- [ ] --memory, --cpus limits
- [ ] No Docker socket mount
- [ ] --security-opt=no-new-privileges

## CIS Kubernetes Benchmark

### Control Plane
- [ ] API server: --anonymous-auth=false
- [ ] API server: --authorization-mode=RBAC,Node
- [ ] API server: AlwaysPullImages admission plugin
- [ ] API server: audit logging enabled
- [ ] etcd: client certificate auth
- [ ] etcd: peer client certificate auth

### Worker Nodes
- [ ] Kubelet: --anonymous-auth=false
- [ ] Kubelet: --authorization-mode=Webhook
- [ ] Kubelet: --read-only-port=0
- [ ] Kubelet: --protect-kernel-defaults

### Pod Security
- [ ] runAsNonRoot: true
- [ ] runAsUser > 10000
- [ ] readOnlyRootFilesystem: true
- [ ] allowPrivilegeEscalation: false
- [ ] capabilities drop ALL
- [ ] seccompProfile: RuntimeDefault
- [ ] No hostPath (unless justified)
- [ ] Resource limits always present
- [ ] PodSecurityPolicy or Pod Security Admission enforced

## CIS Linux Host Benchmark (Quick)

### Access
- [ ] SSH: PermitRootLogin no
- [ ] SSH: PasswordAuthentication no
- [ ] SSH: PubkeyAuthentication yes
- [ ] Password complexity enforced (pam_pwquality)
- [ ] FAILLOG_ENAB enabled (login failures)

### Filesystem
- [ ] /tmp: nosuid, nodev, noexec
- [ ] /var: separate partition
- [ ] /var/log: separate partition
- [ ] Sticky bit on world-writable directories

### Audit
- [ ] auditd running and enabled
- [ ] sudo usage logged
- [ ] AIDE filesystem integrity checks scheduled
- [ ] Logs shipped to central collector

### Network
- [ ] Firewall enabled (iptables/nftables/firewalld)
- [ ] Default deny policy
- [ ] Unused protocols disabled (DCCP, SCTP, RDS, TIPC)
- [ ] IP forwarding disabled (unless router)

### Maintenance
- [ ] Automatic security updates enabled
- [ ] Unnecessary services disabled
