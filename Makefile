# fedora-claude-devbox Makefile
# Usage: make <target> [VM_HOST=192.168.x.x] [VM_USER=kevbot] [TAG=latest]

REGISTRY       ?= ghcr.io/distantgeek
IMAGE_NAME     ?= fedora-claude-devbox
TAG            ?= latest
FULL_IMAGE     ?= $(REGISTRY)/$(IMAGE_NAME):$(TAG)
VM_HOST        ?= $(error VM_HOST is required for this target)
VM_USER        ?= kevbot
SSH_KEY        ?= ~/.ssh/id_ed25519
ANSIBLE_OPTS   ?=

# Kubernetes optional gate
ENABLE_KUBERNETES ?= false
K8S_BACKEND       ?= k3s

.PHONY: help build-image push-image deploy upgrade configure-hooks \
        enable-kubernetes validate test-connection clean

help:
	@echo ""
	@echo "fedora-claude-devbox — build and deployment targets"
	@echo ""
	@echo "Image targets:"
	@echo "  make build-image                  Build bootc container image"
	@echo "  make push-image                   Push image to registry"
	@echo ""
	@echo "VM targets (require VM_HOST=<ip>):"
	@echo "  make deploy VM_HOST=<ip>          Run thin Ansible config against VM"
	@echo "  make upgrade VM_HOST=<ip>         bootc upgrade + reboot target VM"
	@echo "  make configure-hooks VM_HOST=<ip> Deploy/update hooks only"
	@echo "  make validate VM_HOST=<ip>        Verify deployment health"
	@echo "  make test-connection VM_HOST=<ip> Test SSH connectivity"
	@echo ""
	@echo "Optional Kubernetes (not default):"
	@echo "  make enable-kubernetes VM_HOST=<ip> [K8S_BACKEND=k3s|kind]"
	@echo ""
	@echo "Options:"
	@echo "  VM_HOST         Target VM IP address"
	@echo "  VM_USER         SSH user (default: kevbot)"
	@echo "  SSH_KEY         SSH private key (default: ~/.ssh/id_ed25519)"
	@echo "  TAG             Image tag (default: latest)"
	@echo "  REGISTRY        Image registry (default: ghcr.io/distantgeek)"
	@echo "  K8S_BACKEND     k3s or kind (default: k3s)"
	@echo ""

# ---------------------------------------------------------------------------
# Image build
# ---------------------------------------------------------------------------

build-image:
	@echo ">>> Building $(FULL_IMAGE)"
	podman build \
		--tag $(FULL_IMAGE) \
		--tag $(REGISTRY)/$(IMAGE_NAME):$$(git rev-parse --short HEAD) \
		-f build/Containerfile \
		.

push-image:
	@echo ">>> Pushing $(FULL_IMAGE)"
	podman push $(FULL_IMAGE)
	podman push $(REGISTRY)/$(IMAGE_NAME):$$(git rev-parse --short HEAD)

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

upgrade:
	@echo ">>> Upgrading devbox at $(VM_HOST)"
	ssh -i $(SSH_KEY) $(VM_USER)@$(VM_HOST) \
		"sudo bootc upgrade && sudo reboot" || true
	@echo ">>> VM rebooting. Reconnect in ~30 seconds."

rollback:
	@echo ">>> Rolling back devbox at $(VM_HOST)"
	ssh -i $(SSH_KEY) $(VM_USER)@$(VM_HOST) \
		"sudo bootc rollback && sudo reboot" || true

configure-hooks:
	@echo ">>> Deploying hooks to $(VM_HOST)"
	rsync -avz --delete \
		-e "ssh -i $(SSH_KEY)" \
		hooks/ \
		$(VM_USER)@$(VM_HOST):~/.claude/hooks/
	ssh -i $(SSH_KEY) $(VM_USER)@$(VM_HOST) \
		"chmod +x ~/.claude/hooks/pre_tool_use/*.py ~/.claude/hooks/post_tool_use/*.py"
	@echo ">>> Hooks deployed."

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
	@echo ">>> Done."

# ---------------------------------------------------------------------------
# bootc-image-builder — convert to raw disk for Proxmox import
# ---------------------------------------------------------------------------

build-disk-image:
	@echo ">>> Pulling $(FULL_IMAGE) into root storage for bootc-image-builder"
	sudo podman pull $(FULL_IMAGE)
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
	@echo ">>> Raw disk image at output/disk.raw"
	@echo ">>> Import to Proxmox:"
	@echo "    scp output/disk.raw root@<proxmox>:/tmp/"
	@echo "    ssh root@<proxmox> qm importdisk <VMID> /tmp/disk.raw <storage-pool> --format raw"
