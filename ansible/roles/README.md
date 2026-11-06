# Ansible roles

Each `ansible/roles/<name>/` directory is a standard Ansible role:

```
ansible/roles/<name>/
├── tasks/main.yml       required — the role's tasks
├── meta/main.yml        required — galaxy_info.description shows in the Ludus catalog; author + role_name form the installed identity
├── meta/version.yml     optional — `version:` shown by Ludus (overrides git tag detection)
├── defaults/main.yml    default variables
└── handlers/main.yml    handlers
```

Ludus installs a local role under its galaxy identity (`<galaxy_info.namespace>.<galaxy_info.role_name>`, or
`<galaxy_info.author>.<galaxy_info.role_name>` when no namespace is set) when `meta/main.yml` defines them,
otherwise under the directory name; blueprints reference whichever name results. Set `namespace` when the
author is written in display form (`Get-Sybers` would otherwise become the prefix). A local role with the same
name as a galaxy role in a blueprint's `requirements.yml` wins over galaxy.

Start new roles from the [Ludus role template](https://github.com/badsectorlabs/ludus_ansible_role_template).
CI runs `ansible-lint` and the structural checks in `scripts/ludus_source_lint.py` over every role here.

| Role | Purpose |
| --- | --- |
| [`get_sybers.range_homevelo_agent`](./get_sybers.range_homevelo_agent/) | Installs the Home-Velo Velociraptor agent on range VMs (Windows, Debian-family Linux, macOS) from the server's public folder, on an explicit config that trusts the Proxmox cluster CA; coexists with the CCXDFIR digger agent. |
