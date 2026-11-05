# Building the macOS Sonoma 14.1.1 template unattended

This template runs the same unattended build as [`macos-sequoia-15`](../macos-sequoia-15/):
the `get_sybers.templates.macos_template` role, installed at build time from the git pin in
[`requirements.yml`](requirements.yml) and run by Packer's `null` source. One
`ludus templates build -n macos-sonoma-14-template` takes the VM through PREPARE, the console-driven
install from macOS Recovery, first boot and FINALIZE with no console interaction.
[`../macos-sequoia-15/Building.md`](../macos-sequoia-15/Building.md) explains why the build is
shaped the way it is (the Recovery image staged out of the installer ISO, local build storage,
the stdlib-only console driver, the first-boot daemon) and applies to this release unchanged.

## What differs for this release

- **Installer media:** `macOS-Sonoma-14.1.1.iso` (`source_url` / `source_iso_name` in the `.pkr.hcl`).
- **ISO checksum:** **not pinned** - record the sha256 of the copy you fetch and set `source_checksum` before `ludus templates add`; the build refuses to run without it.
- **Verification:** the unattended flow was taken end-to-end on a stock Ludus node for macOS
  Sequoia 15.4 only. This release runs the identical role, but the console driver's screen
  probes (which assume the 1280x800 console the `vmware` VGA gives OpenCore and Recovery)
  have not been exercised against its Recovery and installer screens. Treat the first build
  as a bring-up: watch `ludus templates logs`, and if the driver stops, inspect the PNG it
  saves for every state change under the build's `ANSIBLE_LOCAL_TEMP/macos-template/console-<vmid>/`
  on the node, then `ludus templates rm` the template (or destroy the VM) and re-run.

Everything else - host prerequisites (`7z` on the node, `import` content on the ISO storage,
a local build storage the Ludus token can allocate on), the AMD-only root step, credentials
(`localuser` / `password`) and the FINALIZE tuning for `ludus range deploy` - is as the
[README](README.md) describes.
