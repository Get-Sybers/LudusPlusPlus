Builds a **macOS Ludus template on Proxmox** via the OpenCore bootloader,
orchestrated over the Proxmox REST API. It is invoked by each `macos-*` template's
`build.yml` (which the template's `.pkr.hcl` runs through a packer `shell-local`
provisioner). One shared, byte-identical copy of this role lives in each `macos-*`
template directory so every template stays self-contained.
The Proxmox modules moved out of `community.general` into a separate
[`community.proxmox`](https://github.com/ansible-collections/community.proxmox)
collection, which is **not guaranteed present** on every Ludus build host. To
avoid a fragile external dependency this role stays on **ansible-core only** —
`ansible.builtin.uri` for the API, plus a bundled `library/proxmox_iso_download.py`
for the one operation core has no module for (Proxmox's `download-url`, with
checksum verification and task polling). Every API task is guarded (query, then
act) so the role is **idempotent**.
`ludus templates build -n <name>` runs the whole `build.yml` on each invocation;
the role picks the phase from whether a VM of that name exists:
1. **PREPARE** (`tasks/prepare.yml`, no VM yet): assert the ISO checksums, have
   Proxmox download + verify both ISOs, create + configure the VM, set the CPU
   `args` **only on AMD hosts** (Intel needs none — the OpenCore ISO bundles
   VirtualSMC, so there is no isa-applesmc/OSK requirement and no root step), boot
   it. No template is produced; the operator does the one-time interactive install.
2. **FINALIZE** (`tasks/finalize_discover.yml` → provision → `finalize_convert.yml`):
   find the guest IP (DHCP lease), provision in-guest over SSH, embed OpenCore onto
   the disk ESP, detach install media, and convert to a template.
macOS has no unattended installer, so the interactive install between the phases
is unavoidable — see the template README.
Ludus's own macOS deploy path drove several of these — without them a built
template will not deploy with `ludus range deploy`:
- **User `localuser` / `password`** with sudo (Ludus's `group_vars/macos.yml`).
- **virtio NIC** — Ludus rewrites `net0` to virtio on every clone, so the template
  must be installed and finalized on virtio too.
- **QEMU guest agent** (`mav2287/mac-guest-agent`, MIT, ISA-serial) — Ludus resolves
  a VM's IP only via the guest agent; the VM is created with `agent=enabled=1,type=isa`.
- **Working `/usr/bin/python3`** via the Command Line Tools — Ludus's deploy uses
  real Ansible modules with `ansible_python_interpreter: /usr/bin/python3`.
- **Clone hygiene** — regenerated SSH host keys, reset network interfaces, disabled
  automatic software updates.
- The registered `vm_name` **must contain `macos`** — Ludus's inventory keys the
  macOS handling on that substring.
| Variable | Meaning |
|---|---|
| `macos_api_host` | Proxmox API base URL (`https://host:8006`) |
| `macos_api_user` | token id `user@realm!tokenid` (or `user@realm` for ticket auth) |
| `macos_api_token_secret` | API token secret (preferred auth); else `macos_api_password` |
| `macos_node` | Proxmox node name |
| `macos_storage_pool` / `macos_storage_format` | VM disk storage + format |
| `macos_iso_storage` | storage holding the ISOs (must allow `iso` content) |
| `macos_pool` | Proxmox resource pool |
| `macos_bridge` | build network bridge (Ludus NAT, e.g. `vmbr1000`) |
| `macos_vm_name` | registered template name (**must contain `macos`**) |
| `macos_iso_url` / `macos_iso_checksum` / `macos_iso_name` | macOS installer ISO |
| `macos_opencore_url` / `macos_opencore_checksum` / `macos_opencore_name` | OpenCore ISO |
| `macos_template_description` | Proxmox description string |
`macos_guest_cpu` (`Skylake-Client-v4`), `macos_guest_nic_model` (`virtio`),
`macos_vga` (`vmware`), `macos_machine` (`q35`), `macos_bios` (`ovmf`),
`macos_efitype` (`4m`), `macos_qemu_args` (full override; AMD tuning),
`macos_balloon` (`0`), `macos_vm_memory`/`macos_vm_cores`/`macos_vm_disk_size`,
`macos_ssh_username`/`macos_ssh_password` (`localuser`/`password`),
`macos_install_guest_agent` + `macos_guest_agent_url`/`macos_guest_agent_checksum`,
`macos_install_clt`, `macos_embed_opencore`, `macos_skip_provision`,
`macos_validate_certs`, `macos_task_timeout`, `macos_ip_retries`,
`macos_ssh_wait_timeout`.
The Proxmox token/password and the guest SSH password arrive from the Ludus build
environment at runtime (never committed). Tasks that template a secret into a fact
or an `add_host` set `no_log: true`; in-guest privileged steps use `become` (the
password comes from `ansible_become_pass`, never a command line). Run the build
without `-vvv` to keep the API token out of task dumps.
VM creation runs only when no VM of that name exists; `args`, `start`, and the ISO
downloads all check current state first. Re-running PREPARE before the install is
done, or FINALIZE before Remote Login is enabled, ends cleanly with no template.
Provisioning flags success on localhost; FINALIZE converts to a template **only**
if provisioning succeeded (or was explicitly skipped), so a half-configured VM is
never templated — just re-run to resume.
