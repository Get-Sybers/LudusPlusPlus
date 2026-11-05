# Ansible content

Roles and collections shipped by this source. Both are installed per user by `ludus source add`
(instance-wide with `--global`) and can be vendored as git submodules.

- [`roles/`](./roles/README.md) — one standard Ansible role per directory (`tasks/main.yml`, `meta/main.yml` required).
- [`collections/`](./collections/README.md) — one Ansible collection per directory (`galaxy.yml` required).

| Collection | Purpose |
|---|---|
| [`get_sybers.templates`](./collections/get_sybers.templates/) | Template-build content run by the Windows (`ngen`), macOS (OpenCore orchestration) and Metasploitable (imported-image provisioning) templates. Install it with those templates: `ludus source add ... --source-collections get_sybers.templates`. |

Add a role with `git submodule add <repo> ansible/roles/<name>` or by committing the role directory directly,
then reference it from a blueprint's `range-config.yml` or a template's build playbook.
