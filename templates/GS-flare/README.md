> **Prerequisite:** the build runs the [`badsectorlabs.ludus_flarevm`](https://github.com/badsectorlabs/ludus_flarevm)
> role, which the building user must install first (`ludus ansible role add badsectorlabs.ludus_flarevm`,
> or `ludus source add https://github.com/badsectorlabs/ludus-source-bsl --source-roles ludus_flarevm`).

To use this template you must have the [`badsectorlabs.ludus_flarevm`](https://github.com/badsectorlabs/ludus_flarevm) role added by the Ludus user that builds the template.
Registered template name: **`GS-flare-template`** (the `vm_name` default), distinct from the
`flare-vm-template` the Bad Sector Labs source ships, so both can be installed side by side.

```bash
ludus ansible role add badsectorlabs.ludus_flarevm
ludus source add https://github.com/Get-Sybers/LudusPlusPlus --templates GS-flare-template
ludus templates build -n GS-flare-template
```
