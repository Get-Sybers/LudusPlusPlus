# Packer templates

Each `templates/<name>/` directory is one self-contained Ludus Packer template — the same shape as the
[Bad Sector Labs source templates](https://github.com/badsectorlabs/ludus-source-bsl/tree/main/templates):

```
templates/<name>/
├── <name>.pkr.hcl       the Packer build config — exactly one *.pkr.hcl (or *.pkr.json) per directory
├── icon.png             optional catalog icon referenced by the icon_path variable (square, transparent PNG)
├── http/                Linux: preseed / kickstart / autoinstall files served to the installer
├── ansible/             playbooks run by the ansible provisioner at build time
├── scripts/             shell / PowerShell provisioner scripts
└── Autounattend.xml     Windows only: unattended install answer file (must be in the directory root)
```

The template name users put in a range config is the resolved `vm_name` of the `source` block, **not** the
directory name. Keep the `-template` suffix. `ludus source add` registers templates but does not build them;
run `ludus templates build -n <name>` afterwards. Built images are shared instance-wide by name.

## Available templates

Names in the first column are what `ludus templates build -n` takes. "Needs" lists what the building user must
have installed before the build; the Ludus server exports the user's installed roles and collections to every
template build.

### Linux

| Template | Needs | Description |
| --- | --- | --- |
| `ludusplusplus-debian-13-x64-server-template` | — | Debian 13 (Trixie) minimal x64 server, `debian:debian`. Adapted from the [Ludus Packer starter](https://github.com/badsectorlabs/ludus_packer_template). |
| `ninjasploitable-x64-server-template` | — | Debian 12 target with vulnerable services, realmd/sssd AD-join packages and themed vulnerable web content baked in at build; `debian:debian`. |

### Windows

| Template | Needs | Description |
| --- | --- | --- |
| `win10-22h2-x64-enterprise-appxfix-template` | — | Windows 10 22H2 Enterprise with every AppX sysprep blocker removed at build, for workstation VMs that sysprep. |
| `win11-22h2-x64-enterprise-appxfix-template` | `get_sybers.templates` | Windows 11 22H2 Enterprise with the same AppX sysprep fix. |
| `win2022-server-x64-appxfix-template` | `get_sybers.templates` | Windows Server 2022 with the AppX sysprep blockers removed and EdgeUpdate disabled at build. Use instead of the stock `win2022-server-x64-template` for VMs that sysprep. |
| `win2022-exchange2019-x64-template` | `get_sybers.templates` | Windows Server 2022 with the Exchange 2019 CU15 prerequisites and media baked in; derived from `win2022-server-x64-appxfix`. |
| `GS-flare-template` | role `badsectorlabs.ludus_flarevm` | Windows 10 malware-analysis workstation with FLARE VM tooling (UEFI boot, Defender off). Named apart from the Bad Sector Labs `flare-vm-template` so both can coexist. |

### Imported images (orchestrated builds)

| Template | Needs | Description |
| --- | --- | --- |
| `metasploitable-2-x64-server-template` | `get_sybers.templates` | Metasploitable2 (Ubuntu 8.04), Rapid7's official disk image imported through the Proxmox API; `msfadmin:msfadmin`. |
| `metasploitable-3-ub1404-x64-server-template` | `get_sybers.templates` | Metasploitable3 (Ubuntu 14.04), Rapid7's published Vagrant box imported through the Proxmox API; `vagrant:vagrant`. |

### macOS (orchestrated, OpenCore-booted, one-time interactive install)

| Template | Needs | Description |
| --- | --- | --- |
| `macos-monterey-12-template` | `get_sybers.templates` | macOS Monterey 12.7.1 |
| `macos-ventura-13-template` | `get_sybers.templates` | macOS Ventura 13.6.3 |
| `macos-sonoma-14-template` | `get_sybers.templates` | macOS Sonoma 14.1.1 |
| `macos-sequoia-15-template` | `get_sybers.templates` | macOS Sequoia 15.4 |
| `macos-tahoe-26-template` | `get_sybers.templates` | macOS Tahoe 26.0 (beta media) |

All five build the same way: `ludus templates build` runs twice, PREPARE (download and verify both ISOs, create
and boot the VM) then, after the one-time interactive install at the Proxmox console, FINALIZE (provision over
SSH, embed OpenCore, convert to a template). `localuser:password`, as Ludus expects for macOS. Each directory's
README has the step-by-step and the ISO checksum you must pin before `ludus source add`.

Install a template together with what it needs, for example:

```bash
ludus source add https://github.com/Get-Sybers/LudusPlusPlus \
  --templates win2022-server-x64-appxfix-template,macos-sequoia-15-template \
  --source-collections get_sybers.templates
ludus templates build -n win2022-server-x64-appxfix-template
```

## Two kinds of template

1. **Installer-driven** (`proxmox-iso` builder + preseed / Autounattend): the stock Ludus pattern. Packer boots
   the installer ISO on the Ludus NAT bridge and provisions the result over SSH or WinRM.
2. **Orchestrated** (`source "null"` with `communicator = "none"` and a `shell-local` provisioner): for guests
   with no unattended installer. Packer only runs a local orchestration (an Ansible play from
   `get_sybers.templates`, or `scripts/import.sh`) that drives Proxmox over its REST API with the same Ludus
   variables and API token the Proxmox plugin would use, and ends in the same state: a converted template in the
   `SHARED` pool. The linter holds these to the same variable rules (T020) instead of the builder-attribute rules.

## Authoring rules (enforced by CI)

The `source-structure` job runs `scripts/ludus_source_lint.py`, and the `packer` job runs `packer fmt -check` and
`packer validate` with the exact variables, environment, Packer version and plugin set the Ludus server uses
(`ludus-reference/`). In short, a template must:

1. Declare the Ludus variable block exactly as documented (`proxmox_url`, `proxmox_host`, `proxmox_username`,
   `proxmox_password` (sensitive), `proxmox_storage_pool`, `proxmox_storage_format`, `proxmox_skip_tls_verify`
   (bool), `proxmox_pool`, `iso_storage_pool`, `ansible_home`, `ludus_nat_interface`) with **no defaults**.
   Packer rejects a `-var` that is not declared, so a missing one breaks every build.
2. Give every other variable a default — Ludus passes nothing else, and Packer fails on an unset variable.
3. Wire the Proxmox builder to those variables instead of local values: `proxmox_url`, `node`,
   `insecure_skip_tls_verify`, `pool`, `disks.storage_pool`, `disks.format`, `network_adapters.bridge`,
   `boot_iso.iso_storage_pool` (and `efi_config`/`tpm_config`/`additional_iso_files` storage pools when present).
   Never set `vm_id`, `template_name`, or `skip_convert_to_template`, and never hard-code API credentials.
   Orchestrated templates hand the same variables to their orchestration instead.
4. Resolve `vm_name` to a literal ending in `-template` (Ludus reads it from the file), declare `variable "os"`
   with a literal Proxmox OS type (Ludus classifies the template from it; macOS templates leave it out and carry
   `macos` in the name instead), and use the `ssh` or `winrm` communicator with credentials that match the Ludus
   group_vars for that OS.
5. Set `ANSIBLE_HOME=${var.ansible_home}` and `skip_version_check = true` on every ansible provisioner, never
   override `ANSIBLE_ROLES_PATH` / `ANSIBLE_COLLECTIONS_PATH`, and keep every referenced path (playbooks,
   scripts, `http/`, `cd_files`) inside the template directory. A `requirements.yml` that reaches outside the
   directory is rejected: Ludus installs each template directory on its own.
6. Run only Ansible content that Ludus installs itself (`ludus-reference/ansible-requirements.yml`), that this
   source ships under `ansible/`, or that the README tells the building user to install.
7. Provide a static `description` variable (shown in the catalog), a real icon or no `icon_path`, and, for
   Windows, an `Autounattend.xml`.

Run `make lint-source` and `make packer-validate` locally before pushing.
