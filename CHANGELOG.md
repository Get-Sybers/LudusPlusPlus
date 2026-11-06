# Changelog

All notable changes to the LudusPlusPlus Ludus source — its Packer templates, the
`get_sybers.templates` collection copy, the example blueprint and the CI that holds them to the
Ludus conventions — are documented here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the repository has no release tags yet.

## [Unreleased]

### Added — the Home-Velo Velociraptor agent role

- `ansible/roles/get_sybers.range_homevelo_agent` installs the Home-Velo Velociraptor agent on range
  VMs — Windows, Debian-family Linux and macOS — from the server's public folder. The artifact, the
  Proxmox cluster CA and the published client config are downloaded once to the Ludus host
  (sha256-pinned; nothing secret lives in the role), the CA is merged into the config as
  `Client.Crypto.root_certs`, and every platform runs the agent on that explicit config: on
  Windows the published MSI's service is pointed at it with `--config … service run`, on Linux the
  agent gets its own binary, config path and `velociraptor-homevelo` unit so it coexists with the
  CCXDFIR digger agent, on macOS `service install --config` registers the launchd daemon. The README
  records why: agents left on the MSI's embedded config never enrolled from a range, macOS keychain
  trust cannot be granted over SSH, and the stock Linux installer overwrites digger's unit. Verified
  on an FGNW range on 2026-11-07: all 20 VMs enrolled. `ansible/roles/README.md` now also states
  that Ludus takes `galaxy_info.namespace` for the installed name when it is set.

### Fixed — the AppX-fix images disable the Edge updater's scheduled tasks too (from FGNW)

- `remove-appx-sysprep-blockers.ps1` in `win2022-server-x64-appxfix`, `win2022-exchange2019-x64`,
  `win10-22h2-x64-enterprise-appxfix` and `win11-22h2-x64-enterprise-appxfix` now stops a running
  updater, stops and disables the `MicrosoftEdgeUpdateTaskMachineCore` / `…UA` scheduled tasks and
  sets `UpdateDefault`, `Update{56EB18F8-…}` (the Stable channel) and `AutoUpdateCheckPeriodMinutes`
  to 0, not only the two services. The tasks launch `MicrosoftEdgeUpdate.exe` directly, so on a
  deployed clone the updater still ran, installed a newer Edge, and Edge's installer registered the
  `Microsoft.MicrosoftEdge.Stable` sparse package for the logged-on user; the first deploy-time
  Sysprep then failed on it (0x80073cf2) and fell back to Ludus's remove-and-retry rescue. The
  Windows 10 and 11 images had no updater handling at all. Synced from FGNW `dd948fa`; rebuild the
  four templates to pick it up.

### Changed — the templates follow Get-Sybers/FGNW

- The five templates FGNW maintains (`ninjasploitable`, `win2022-server-x64-appxfix`,
  `win2022-exchange2019-x64`, `win10-22h2-x64-enterprise-appxfix`, `macos-sequoia-15`) and the
  `get_sybers.templates` collection are synced from FGNW `76afe75`. The macOS build is fully
  unattended (Recovery-driven install over the Proxmox console API, local build storage), and all
  five macOS releases here run it; only Sequoia is verified end-to-end upstream, and the other
  releases say so in their README and `Building.md`.
- Templates that need Ansible content beyond what the Ludus server ships install it at build time
  from a `requirements.yml` in the template directory (git sources pinned to a commit, Galaxy
  entries at exact versions) with a `shell-local` provisioner, instead of relying on
  `--source-collections` or the Packer ansible provisioner's `galaxy_file`. The Metasploitable
  templates pin this repository's collection commit, which still carries their provisioning role.
- The collection copy is FGNW's 0.2.0 plus the `metasploitable_provision` role; its macOS
  variables carry the role prefix, so the ansible-lint skip is gone.
- Kept from this repository: the `boot_iso` form of the Windows 10 template, no placeholder icons,
  and macOS installs into the user's collections rather than overriding `ANSIBLE_COLLECTIONS_PATH`.

### Added — CI improvements adopted from FGNW

- A provenance-pinned `ludus-reference/` check on every run; the reference tool normalises the
  vendored schema's whitespace.
- Workflow hardening: no workflow-level permissions, read-only checkouts without persisted
  credentials, a pinned runner image, and an `all-green` aggregate job to require on `main`
  (`.github/rulesets/main.json` is the matching ruleset to import).
- Grouped weekly Dependabot updates, the stricter shellcheck profile, and the pin discipline for
  template requirements in the linter (T021), with tests.
- `scripts/install_ansible_deps.sh` installs each template's build-time requirements before this
  source's own collections, so ansible-lint resolves the repository's content.

## 2026-11-05 — Get-Sybers templates landed

- The 13 templates from `Get-Sybers/Proxmox` and the `get_sybers.templates` collection moved in and
  were made to conform (no relative-collection installs, current Proxmox builder attributes, the
  truncated Ninjasploitable build completed, placeholder icons dropped). The FLARE VM template was
  renamed `GS-flare-template` to coexist with the Bad Sector Labs one.
- Linter rules for orchestrated templates (T020), Ansible dependencies (T018), deprecated builder
  attributes (T019), requirements files (T021), placeholder icons and the macOS `variable "os"` rule.

## 2026-11-05 — the source and its CI

- Repository laid out as a Ludus source with a Debian 13 template and an example blueprint.
- `scripts/ludus_source_lint.py`, the Packer smoke test with the Ludus-pinned toolchain, the
  vendored `ludus-reference/` with its weekly drift check, and the CI workflow.
