> **Prerequisite:** the build runs the [`badsectorlabs.ludus_flarevm`](https://github.com/badsectorlabs/ludus_flarevm)
> role, which the building user must install first (`ludus ansible role add badsectorlabs.ludus_flarevm`,
> or `ludus source add https://github.com/badsectorlabs/ludus-source-bsl --source-roles ludus_flarevm`).

To use this template you must have the [`badsectorlabs.ludus_flarevm`](https://github.com/badsectorlabs/ludus_flarevm) role added by the Ludus user that builds the template.
```bash
ludus ansible role add badsectorlabs.ludus_flarevm
git clone https://gitlab.com/badsectorlabs/ludus.git
cd ludus/templates
ludus templates add -d flare-vm
ludus templates build
```
