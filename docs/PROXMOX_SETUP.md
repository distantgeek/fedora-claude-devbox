# Proxmox VM Configuration — fedora-claude-devbox

## Recommended VM Hardware Settings

### General
| Setting | Value | Reason |
|---------|-------|--------|
| VM Type | KVM | Full virtualization, best Fedora compatibility |
| OS Type | Linux 6.x kernel | Correct VirtIO driver set |
| Machine Type | q35 | PCIe support, modern chipset, required for UEFI |
| BIOS | OVMF (UEFI) | Required for bootc/ostree deployments |
| SCSI Controller | VirtIO SCSI Single | Best disk throughput |

### CPU
| Setting | Value | Reason |
|---------|-------|--------|
| CPU Type | **host** | Passes through all host CPU flags; rustup/mise need AVX2 |
| Sockets | 1 | |
| Cores | 4 | Comfortable for parallel builds; 2 minimum |
| NUMA | disabled | Single socket, not needed |

> **Important:** Do NOT use the default `kvm64` CPU type. It strips modern instruction
> sets that Rust compilation and some Node tooling depend on. Use `host` for a devbox
> where migration between Proxmox nodes is not a concern.

### Memory
| Setting | Value | Reason |
|---------|-------|--------|
| RAM | 8192 MB (8GB) | Comfortable floor; Tauri builds and cargo are hungry |
| Ballooning | disabled | Devbox has variable memory pressure; ballooning causes latency spikes |

> Bump to 12288 MB (12GB) if you plan to run local LLM inference or heavy Rust workloads.

### Disk
| Setting | Value | Reason |
|---------|-------|--------|
| Bus | VirtIO SCSI (scsi0) | Best throughput |
| Size | 60 GB | Base image + toolchains + repos |
| Cache | Write Back | Better write performance |
| Discard | enabled | SSD TRIM passthrough |
| IO Thread | enabled | Better multi-queue disk performance |

### Network
| Setting | Value | Reason |
|---------|-------|--------|
| Model | VirtIO | Best throughput |
| Bridge | vmbr0 | Direct LAN access |
| Firewall | disabled at Proxmox level | firewalld inside the VM handles this |
| MAC Address | static/fixed | Reserve a DHCP lease for consistency |

### QEMU Guest Agent
Enable in Proxmox UI and it is already installed + enabled in the image.
Without it, Proxmox cannot gracefully shut down the VM or report IP addresses.

> **Known limitation:** SELinux restricts the guest agent (`virtd_t` domain) from
> executing arbitrary binaries. `qm guest exec` calls to run tools like `ip` or
> `useradd` will fail with Permission denied. Use SSH for all VM management.

### Display
| Setting | Value | Reason |
|---------|-------|--------|
| Display | Serial Terminal | Devbox is headless SSH-only; serial is lightweight |
| Serial | socket (serial0) | Required for serial terminal to work |

---

## Proxmox API Token Setup

Claude Code manages Proxmox via REST API using a dedicated token. This is required
for automated VM provisioning — do not use your personal root credentials.

### Create the service account and token

In Proxmox UI:

1. **Create user:** Datacenter → Users → Add
   - User: `claude`, Realm: `pve` (PAM realm — this creates a Linux user)
   - Or use an existing user; the key is a scoped token

2. **Create role:** Datacenter → Permissions → Roles → Create
   - Name: `ClaudeDevbox`
   - Privileges: `VM.Allocate, VM.Config.Disk, VM.Config.CPU, VM.Config.Memory,
     VM.Config.Network, VM.Config.Options, VM.Config.Boot, VM.PowerMgmt, VM.Snapshot,
     VM.Audit, Datastore.AllocateSpace, Datastore.Audit, Sys.Audit`

3. **Create token:** Datacenter → API Tokens → Add
   - User: `claude@pam`, Token ID: `claudeToken`
   - **Disable** privilege separation (simplifies ACL management)

4. **Grant permissions** (Datacenter → Permissions → Add → User Permissions):
   - `/nodes/<node>` → `claude@pam` → `ClaudeDevbox`
   - `/vms` → `claude@pam` → `ClaudeDevbox`
   - `/storage` → `claude@pam` → `ClaudeDevbox`
   - `/sdn/zones` → `claude@pam` → `PVESDNUser` (required for VirtIO NIC on vmbr0 in PVE 9+)

### Store credentials

`~/.config/proxmox/token` on the operator machine (never commit this file):

```bash
PROXMOX_HOST=192.168.x.x
PROXMOX_USER=claude@pam
PROXMOX_TOKEN_NAME=claudeToken
PROXMOX_TOKEN_VALUE=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Source it in `~/.bashrc` or `~/.zshrc`:
```bash
if [ -f "$HOME/.config/proxmox/token" ]; then
    set -a; source "$HOME/.config/proxmox/token"; set +a
fi
```

### Dedicated SSH key for Proxmox host access

Disk import and some diagnostics require SSH to the Proxmox host. Use a dedicated
key — not your personal SSH key:

```bash
ssh-keygen -t ed25519 -C "claude-code@fedora-claude-devbox" \
  -f ~/.ssh/id_ed25519_claude_proxmox -N ""

# Install on Proxmox host (as root):
cat ~/.ssh/id_ed25519_claude_proxmox.pub >> /root/.ssh/authorized_keys
```

---

## Full Deployment Workflow (PVE 9+)

### 1. Build and push the image

```bash
make build-image DEVBOX_USER=yourname
make push-image
```

### 2. Convert to raw disk

```bash
make build-disk-image
# Output at: output/image/disk.raw  (~10GB)
```

### 3. Transfer disk to Proxmox host

```bash
scp output/image/disk.raw root@<proxmox-host>:/tmp/
```

### 4. Create the VM via API

The Makefile does not include a `create-vm` target yet — use curl or the Proxmox UI.
Full API example (requires `~/.config/proxmox/token` sourced):

```bash
set -a && source ~/.config/proxmox/token && set +a

curl -sk -X POST \
  -H "Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}" \
  -H "Content-Type: application/json" \
  -d '{
    "vmid": <VMID>,
    "name": "fedora-claude-devbox",
    "machine": "q35",
    "bios": "ovmf",
    "scsihw": "virtio-scsi-single",
    "cpu": "host",
    "cores": 4,
    "sockets": 1,
    "memory": 8192,
    "balloon": 0,
    "net0": "virtio,bridge=vmbr0,firewall=0",
    "agent": "enabled=1",
    "efidisk0": "local-lvm:0,efitype=4m,pre-enrolled-keys=0",
    "serial0": "socket",
    "vga": "serial0",
    "ostype": "l26",
    "onboot": 1
  }' \
  "https://${PROXMOX_HOST}:8006/api2/json/nodes/<node>/qemu"
```

### 5. Import the disk (PVE 9 syntax — run on Proxmox host)

```bash
# PVE 9+ — note: qm disk import, NOT qm importdisk
ssh root@<proxmox-host> "qm disk import <VMID> /tmp/disk.raw local-lvm"

# Attach with optimal options
ssh root@<proxmox-host> \
  "qm set <VMID> --scsi0 'local-lvm:vm-<VMID>-disk-1,cache=writeback,discard=on,iothread=1'"

# Resize to 60GB
ssh root@<proxmox-host> "qm disk resize <VMID> scsi0 60G"

# Set boot order
ssh root@<proxmox-host> "qm set <VMID> --boot order=scsi0"

# Clean up
ssh root@<proxmox-host> "rm -f /tmp/disk.raw"
```

> **PVE 9 note:** `qm importdisk` still exists but can silently write the VM config
> entry without creating the LVM volume. Use `qm disk import` instead and verify
> with `lvs pve | grep vm-<VMID>`.

### 6. Start VM and get IP

```bash
# Start via API
curl -sk -X POST \
  -H "Authorization: PVEAPIToken=${PROXMOX_USER}!${PROXMOX_TOKEN_NAME}=${PROXMOX_TOKEN_VALUE}" \
  "https://${PROXMOX_HOST}:8006/api2/json/nodes/<node>/qemu/<VMID>/status/start"

# Get IP via guest agent (from Proxmox host — avoids API permission requirement)
ssh root@<proxmox-host> "qm guest cmd <VMID> network-get-interfaces"
```

### 7. Bootstrap SSH access (first boot only)

The image creates the `DEVBOX_USER` with no SSH key. For first access, inject your
key via the Proxmox host while the VM is stopped:

```bash
# Stop VM
ssh root@<proxmox-host> "qm stop <VMID>"

# Map partitions and inject key into root's home in the ostree layout
ssh root@<proxmox-host> bash << 'EOF'
LOOP=$(losetup -f --show -P /dev/pve/vm-<VMID>-disk-1)
ROOTHOME=/mnt/vm/ostree/deploy/default/var/roothome
mkdir -p /mnt/vm && mount ${LOOP}p4 /mnt/vm
mkdir -p ${ROOTHOME}/.ssh && chmod 700 ${ROOTHOME}/.ssh
echo "YOUR_SSH_PUBLIC_KEY" > ${ROOTHOME}/.ssh/authorized_keys
chmod 600 ${ROOTHOME}/.ssh/authorized_keys && chown -R 0:0 ${ROOTHOME}/.ssh
umount /mnt/vm && losetup -d $LOOP
EOF

# Start VM and SSH in as root
ssh root@<proxmox-host> "qm start <VMID>"
ssh root@<vm-ip>
```

Once SSHed in as root, create the primary user and run Ansible:

```bash
# On the VM as root — create primary user
useradd -m -G wheel,podman -s /bin/bash <username>
echo "<username> ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/<username>
chmod 440 /etc/sudoers.d/<username>
mkdir -p /home/<username>/.ssh
echo "YOUR_SSH_PUBLIC_KEY" > /home/<username>/.ssh/authorized_keys
chmod 700 /home/<username>/.ssh && chmod 600 /home/<username>/.ssh/authorized_keys
chown -R <username>:<username> /home/<username>/.ssh
loginctl enable-linger <username>

# From the build machine — run Ansible to finish config
make deploy VM_HOST=<vm-ip>
```

> Future builds with `DEVBOX_USER=yourname` eliminate the manual useradd step.
> The next `make upgrade` will have the user baked in with skel pre-populated.

---

## Ongoing Upgrade Workflow

```bash
# Modify Containerfile or config, then:
make build-image DEVBOX_USER=yourname
make push-image
make upgrade VM_HOST=<devbox-ip>
# (runs: bootc upgrade + reboot on the devbox via SSH)

# If something breaks:
make rollback VM_HOST=<devbox-ip>
```

bootc's 3-way `/etc` merge preserves local changes (users, SSH keys, sudoers rules)
across upgrades. `/var` (home directories, data) is never touched by upgrades.

---

## VM Snapshot Strategy

| When | Action | Reason |
|------|--------|--------|
| After initial deploy | Proxmox snapshot: `initial-deploy` | Clean baseline |
| Before first `bootc upgrade` | Proxmox snapshot: `pre-upgrade-v<tag>` | External safety net |
| Before major project work | Proxmox snapshot: `pre-<project>` | Quick restore if state corrupts |
| Routine | Proxmox scheduled backup (weekly) | Persistent coverage |

bootc rollback handles upgrade failures; Proxmox snapshots handle everything else.
