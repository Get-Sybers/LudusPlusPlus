# get_sybers.templates

Shared Packer template-baking content for the Get-Sybers Ludus sources. It exists
to remove the per-template duplication that used to live under `templates/`: the
same role, module, and build playbooks were copied verbatim into every template
directory. They now live here once and are consumed by each template's `.pkr.hcl`
build by FQCN: `ludus source add --source-collections get_sybers.templates` installs
the collection for the building user, and the Ludus server exports the user's
installed collections to every template build (`ANSIBLE_COLLECTIONS_PATH`).

> Design rule (ansible-standards §2): **the role acts, the playbook decides.** The
> roles below carry the actions; each template keeps only a thin build entry point
> (its `.pkr.hcl`, and for Windows a two-line `import_playbook` wrapper) that
> selects which of them run.

## Contents

| Kind | Reference | Was |
|---|---|---|
| role | `get_sybers.templates.macos_template` | `templates/macos-*/roles/macos_template/` (×5, identical) |
| module | `get_sybers.templates.proxmox_iso_download` | `.../macos_template/library/proxmox_iso_download.py` (×5) |
| role | `get_sybers.templates.windows_ngen` | `templates/win*/ansible/ngen.yml` (×3, identical) |
| role | `get_sybers.templates.metasploitable_provision` | `templates/metasploitable-*/ansible/provision.yml` (×2, identical) |
| playbook | `playbooks/build.yml` | `templates/macos-*/build.yml` (×5) + `macos_vars.yml` (×5) |
| playbook | `playbooks/ngen.yml` | thin play around `windows_ngen` |
| playbook | `playbooks/provision.yml` | thin play around `metasploitable_provision` |

The three roles and the module are referenced by FQCN; the playbooks are invoked
by their collection-qualified name (the collection name followed by the playbook
stem). Each consuming template's build definition holds the exact command.

## How templates consume it

Install the collection with the templates that need it and the builds find it
through the collections path the Ludus server exports:

```bash
ludus source add https://github.com/Get-Sybers/LudusPlusPlus \
  --templates macos-sequoia-15-template,win2022-server-x64-appxfix-template \
  --source-collections get_sybers.templates
```

- **macOS** (`templates/macos-*`): the `.pkr.hcl` `shell-local` provisioner runs
  the collection's `build.yml` play by FQCN. The build env-bridge lives in
  `playbooks/vars/macos_vars.yml`.
- **Windows** (`templates/win*`): the Packer `ansible` provisioner runs the two-line
  `ansible/ngen.yml`, which `import_playbook`s the collection's `ngen.yml` play.
- **Metasploitable** (`templates/metasploitable-*`): `scripts/import.sh` invokes
  the collection's `provision.yml` play.

A template directory must never carry a `requirements.yml` that points outside
itself: Ludus installs each template directory on its own, so relative paths to
`ansible/collections/` do not exist at build time.

## Requirements

- `ansible-core >= 2.15` (`meta/runtime.yml`).
- `community.windows` (for `windows_ngen`), declared in `galaxy.yml`; the Ludus
  server installs it (`ludus-server/ansible/requirements.yml`).

## Testing

`extensions/molecule/` holds the native molecule scenarios (docker driver,
Debian substrate), run with `molecule test --all`. Roles whose real target is a
live Proxmox node / a Windows guest / a legacy Linux image are exercised by
negative scenarios (clean failure on bad input) here and against real
infrastructure in CI, matching the `get_sybers.range` and `get_sybers.cluster`
pattern.
