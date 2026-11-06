# Ansible content

Roles and collections shipped by this source. Both are installed per user by `ludus source add`
(instance-wide with `--global`) and can be vendored as git submodules.

- [`roles/`](./roles/README.md) — one standard Ansible role per directory (`tasks/main.yml`, `meta/main.yml` required).
- [`collections/`](./collections/README.md) — one Ansible collection per directory (`galaxy.yml` required).

| Collection | Purpose |
|---|---|
| [`get_sybers.templates`](./collections/get_sybers.templates/) | Template-build content run by the Windows (`ngen`), macOS (unattended OpenCore build) and Metasploitable (imported-image provisioning) templates. Maintained in [Get-Sybers/FGNW](https://github.com/Get-Sybers/FGNW) (this copy adds the Metasploitable role); the templates install it at build time from pinned git sources, and it is also selectable with `--source-collections get_sybers.templates`. |

| Role | Purpose |
|---|---|
| [`get_sybers.range_homevelo_agent`](./roles/get_sybers.range_homevelo_agent/) | Installs the Home-Velo Velociraptor agent on range VMs from the server's public folder, on an explicit config that trusts the Proxmox cluster CA (the MSI's embedded config and macOS keychain trust do not work from a range); coexists with the CCXDFIR digger agent. Selectable with `--source-roles get_sybers.range_homevelo_agent`. |

Add a role with `git submodule add <repo> ansible/roles/<name>` or by committing the role directory directly,
then reference it from a blueprint's `range-config.yml` or a template's build playbook.
