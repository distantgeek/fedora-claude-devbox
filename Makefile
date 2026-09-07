# open-atomic Makefile
# Usage: make <target> [VM_HOST=192.168.x.x] [VM_USER=devbox] [TAG=latest]

REGISTRY        ?= ghcr.io/distantgeek
IMAGE_NAME      ?= open-atomic
AGENT_IMAGE     ?= open-atomic-agent
TAG             ?= latest
FULL_IMAGE      ?= $(REGISTRY)/$(IMAGE_NAME):$(TAG)
FULL_AGENT      ?= $(REGISTRY)/$(AGENT_IMAGE):$(TAG)
VM_HOST         ?= $(error VM_HOST is required for this target)
VM_USER         ?= devbox
SSH_KEY         ?= ~/.ssh/id_ed25519
SSH_PUBKEY      ?= $(shell cat $(SSH_KEY).pub 2>/dev/null)
ANSIBLE_OPTS    ?=
DEVBOX_USER     ?= devbox

# Kubernetes optional gate
ENABLE_KUBERNETES ?= false
K8S_BACKEND       ?= k3s

.PHONY: help build-image build-agent-image push-image push-images deploy upgrade \
        rollback enable-kubernetes validate test-connection clean build-disk-image

help:
	@echo ""
	@echo "open-atomic — build and deployment targets"
	@echo ""
	@echo "Image targets:"
	@echo "  make build-image                   Build bootc VM image"
	@echo "  make build-agent-image             Build agent container image (opencode + framework)"
	@echo "  make push-image                    Push VM image to registry"
	@echo "  make push-images                   Push both images"
	@echo ""
	@echo "VM targets (require VM_HOST=<ip>):"
	@echo "  make deploy VM_HOST=<ip>           Run thin Ansible config against VM"
	@echo "  make upgrade VM_HOST=<ip>          bootc upgrade + reboot (requires root SSH)"
	@echo "  make rollback VM_HOST=<ip>         bootc rollback + reboot (requires root SSH)"
	@echo "  make validate VM_HOST=<ip>         Verify deployment health"
	@echo "  make test-connection VM_HOST=<ip>  Test SSH connectivity"
	@echo ""
	@echo "Options:"
	@echo "  VM_HOST         Target VM IP address"
	@echo "  VM_USER         SSH user (default: devbox)"
	@echo "  SSH_KEY         SSH private key (default: ~/.ssh/id_ed25519)"
	@echo "  SSH_PUBKEY      Public key baked into the image as authorized_keys"
	@echo "  TAG             Image tag (default: latest)"
	@echo "  REGISTRY        Image registry (default: ghcr.io/distantgeek)"
	@echo ""

# ---------------------------------------------------------------------------
# Image build
# ---------------------------------------------------------------------------

build-image:
	@echo ">>> Building $(FULL_IMAGE) (DEVBOX_USER=$(DEVBOX_USER))"
	podman build \
		--tag $(FULL_IMAGE) \
		--tag $(REGISTRY)/$(IMAGE_NAME):$$(git rev-parse --short HEAD) \
		--build-arg DEVBOX_USER=$(DEVBOX_USER) \
		--build-arg SSH_AUTHORIZED_KEYS="$(SSH_PUBKEY)" \
		-f build/Containerfile \
		.

build-agent-image:
	@echo ">>> Building $(FULL_AGENT)"
	podman build \
		--tag $(FULL_AGENT) \
		--tag $(REGISTRY)/$(AGENT_IMAGE):$$(git rev-parse --short HEAD) \
		-f build/agent/Containerfile \
		.

push-image:
	@echo ">>> Pushing $(FULL_IMAGE)"
	podman push $(FULL_IMAGE)
	podman push $(REGISTRY)/$(IMAGE_NAME):$$(git rev-parse --short HEAD)

push-images: push-image
	@echo ">>> Pushing $(FULL_AGENT)"
	podman push $(FULL_AGENT)
	podman push $(REGISTRY)/$(AGENT_IMAGE):$$(git rev-parse --short HEAD)

# ---------------------------------------------------------------------------
# VM deployment
# ---------------------------------------------------------------------------

deploy:
	@echo ">>> Configuring $(VM_USER)@$(VM_HOST)"
	ansible-playbook ansible/playbooks/configure.yml \
		-i $(VM_HOST), \
		-u $(VM_USER) \
		--private-key $(SSH_KEY) \
		-e "vm_host=$(VM_HOST) vm_user=$(VM_USER)" \
		$(ANSIBLE_OPTS)

# bootc upgrade/rollback require root — the devbox user has NO sudo by design.
# Run these as root over SSH (operator maintenance path).
upgrade:
	@echo ">>> Upgrading devbox at $(VM_HOST)"
	ssh -i $(SSH_KEY) root@$(VM_HOST) \
		"bootc upgrade && reboot" || true
	@echo ">>> VM rebooting. Reconnect in ~30 seconds."

rollback:
	@echo ">>> Rolling back devbox at $(VM_HOST)"
	ssh -i $(SSH_KEY) root@$(VM_HOST) \
		"bootc rollback && reboot" || true

# ---------------------------------------------------------------------------
# Optional Kubernetes
# ---------------------------------------------------------------------------

enable-kubernetes:
	@echo ">>> Installing Kubernetes ($(K8S_BACKEND)) on $(VM_HOST)"
	ansible-playbook ansible/playbooks/kubernetes.yml \
		-i $(VM_HOST), \
		-u $(VM_USER) \
		--private-key $(SSH_KEY) \
		-e "vm_host=$(VM_HOST) vm_user=$(VM_USER) k8s_backend=$(K8S_BACKEND)" \
		$(ANSIBLE_OPTS)

# ---------------------------------------------------------------------------
# Validation and utilities
# ---------------------------------------------------------------------------

test-connection:
	@echo ">>> Testing SSH to $(VM_USER)@$(VM_HOST)"
	ssh -i $(SSH_KEY) -o ConnectTimeout=5 $(VM_USER)@$(VM_HOST) \
		"echo 'Connection OK' && uname -a && bootc status 2>/dev/null | head -5"

validate:
	@echo ">>> Validating deployment on $(VM_HOST)"
	ansible-playbook ansible/playbooks/validate.yml \
		-i $(VM_HOST), \
		-u $(VM_USER) \
		--private-key $(SSH_KEY) \
		$(ANSIBLE_OPTS)

clean:
	@echo ">>> Cleaning build artifacts"
	rm -f output/disk.raw
	podman rmi $(FULL_IMAGE) 2>/dev/null || true
	podman rmi $(FULL_AGENT) 2>/dev/null || true
	@echo ">>> Done."

# ---------------------------------------------------------------------------
# bootc-image-builder — convert to raw disk for Proxmox import
# ---------------------------------------------------------------------------

build-disk-image:
	@echo ">>> Pulling $(FULL_IMAGE) into root storage for bootc-image-builder"
	sudo podman pull --authfile /run/user/$(shell id -u)/containers/auth.json $(FULL_IMAGE)
	@echo ">>> Converting $(FULL_IMAGE) to raw disk image for Proxmox"
	mkdir -p output
	sudo podman run --rm -i \
		--privileged \
		--pull=newer \
		-v $(PWD)/output:/output \
		-v /var/lib/containers/storage:/var/lib/containers/storage \
		quay.io/centos-bootc/bootc-image-builder:latest \
		--type raw \
		--local \
		$(FULL_IMAGE)
	@echo ">>> Raw disk image at output/image/disk.raw"
	@echo ">>> Import to Proxmox (PVE 9):"
	@echo "    scp output/image/disk.raw root@<proxmox>:/tmp/"
	@echo "    ssh root@<proxmox> qm disk import <VMID> /tmp/disk.raw <storage-pool>"
