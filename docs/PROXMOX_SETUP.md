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
| CPU Type | **host** | Passes through all host CPU flags; rustup/mise need AVX2; Claude Code benefits from full ISA |
| Sockets | 1 | |
| Cores | 4 | Comfortable for parallel builds; 2 minimum |
| NUMA | disabled | Single socket, not needed |
| VCPUs | 4 | Match cores |

> **Important:** Do NOT use the default `kvm64` CPU type. It strips modern instruction
> sets that Rust compilation and some Node tooling depend on. Use `host` for a devbox
> where migration between Proxmox nodes is not a concern.

### Memory
| Setting | Value | Reason |
|---------|-------|--------|
| RAM | 8192 MB (8GB) | Comfortable floor; Tauri builds and cargo are hungry |
| Ballooning | disabled | Devbox has variable memory pressure; ballooning causes latency spikes |
| Minimum RAM | n/a | Disable ballooning entirely |

> Bump to 12288 MB (12GB) if you plan to run local LLM inference or heavy Rust
> workloads (ogoa-character-builder Tauri builds can spike).

### Disk
| Setting | Value | Reason |
|---------|-------|--------|
| Bus | VirtIO Block | Best throughput, lowest latency |
| Size | 60 GB | Base image + toolchains + repos; 80GB if you anticipate large build artifacts |
| Storage Pool | SSD-backed pool | bootc image writes are sequential; NVMe-backed pool ideal |
| Cache | Write Back | Better write performance; acceptable for devbox (not a DB) |
| Discard | enabled | SSD TRIM passthrough |
| IO Thread | enabled | Better multi-queue disk performance |
| Backup | yes | Include in Proxmox backup schedule |

### Network
| Setting | Value | Reason |
|---------|-------|--------|
| Model | VirtIO | Best throughput |
| Bridge | vmbr0 (or your LAN bridge) | Direct LAN access |
| Firewall | disabled at Proxmox level | Firewalld inside the VM handles this |
| MAC Address | static/fixed | So DHCP reservation or static IP stays consistent |

### QEMU Guest Agent
| Setting | Value |
|---------|-------|
| QEMU Guest Agent | **enabled** |

Enable this in Proxmox **and** install `qemu-guest-agent` inside the VM.
Without it, Proxmox can't gracefully shut down the VM or report IP addresses.
Add to `build/Containerfile`:
```
RUN dnf install -y qemu-guest-agent && \
    systemctl enable qemu-guest-agent
```

### Display
| Setting | Value | Reason |
|---------|-------|--------|
| Display | Serial Terminal (or VirtIO) | Devbox is headless SSH-only; serial is lightweight |
| VGA Memory | 4MB | Minimum; you won't use it |

---

## Proxmox Host Settings to Adjust

### Before deploying the VM

**1. Enable IOMMU (if not already enabled)**
Not required for this VM but good practice. In `/etc/default/grub` on the Proxmox host:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"
```
Then `update-grub && reboot`.

**2. Verify SSD-backed storage pool is configured**
In Datacenter → Storage, confirm the pool backing the VM disk is on SSD/NVMe.
If using ZFS, verify the pool is on SSD vdevs with `zpool status`.

**3. Snapshot before first bootc upgrade**
After initial deploy, take a manual snapshot in Proxmox before running
`bootc upgrade` for the first time. bootc has its own rollback (`bootc rollback`)
but a Proxmox snapshot is a clean external safety net.

**4. Reserve a static IP or DHCP reservation**
Set a DHCP reservation for the VM's MAC address on your router/DHCP server so
the IP doesn't change between reboots. Claude Code on your laptop needs a
consistent target address.

**5. SSH access from Proxmox host (optional)**
If you want Claude Code on the laptop to reach the Proxmox API (to create/manage
the VM itself), enable the Proxmox API token:
- Datacenter → Permissions → API Tokens → Add
- Scope it to the specific VM or node
- Store the token in `~/.config/proxmox/token` on the laptop (never in a repo)

---

## bootc Image Deployment to Proxmox

### Method: bootc-image-builder → raw disk image → import to Proxmox

```bash
# On your devbox build machine (Aurora-nvidia or laptop):
# 1. Build the container image
podman build -t fedora-claude-devbox:latest -f build/Containerfile .

# 2. Convert to raw disk image via bootc-image-builder
sudo podman run --rm -it \
  --privileged \
  --pull=newer \
  -v $(pwd)/output:/output \
  -v /var/lib/containers/storage:/var/lib/containers/storage \
  quay.io/centos-bootc/bootc-image-builder:latest \
  --type raw \
  --local \
  fedora-claude-devbox:latest

# 3. Import to Proxmox (adjust VMID and storage pool)
scp output/disk.raw root@proxmox:/tmp/
ssh root@proxmox \
  "qm importdisk <VMID> /tmp/disk.raw <storage-pool> --format raw"

# 4. In Proxmox UI: attach the imported disk to the VM, set boot order, start VM
```

### After first boot
```bash
# SSH into the new VM
ssh kevbot@<devbox-ip>

# Verify bootc is tracking the image
sudo bootc status

# Enable user lingering for rootless Podman services
loginctl enable-linger kevbot

# Run thin Ansible configuration
# (from your laptop, after adjusting inventory)
make deploy VM_HOST=<devbox-ip>
```

---

## Ongoing Upgrade Workflow

```bash
# Rebuild image after changes to Containerfile
make build-image

# Push to registry
make push-image

# Upgrade running devbox atomically
make upgrade VM_HOST=<devbox-ip>
# (this runs: ssh kevbot@<host> "sudo bootc upgrade && sudo reboot")

# If something breaks after upgrade:
ssh kevbot@<devbox-ip> "sudo bootc rollback && sudo reboot"
```

---

## VM Snapshot Strategy

| When | Action | Reason |
|------|--------|--------|
| After initial deploy | Proxmox snapshot: `initial-deploy` | Clean baseline |
| Before first `bootc upgrade` | Proxmox snapshot: `pre-upgrade-v<tag>` | External safety net |
| Before major project work | Proxmox snapshot: `pre-<project>` | Quick restore if devbox state corrupts |
| Routine | Proxmox scheduled backup (weekly) | Persistent coverage |

bootc rollback handles upgrade failures; Proxmox snapshots handle everything else.
