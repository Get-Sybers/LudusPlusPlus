# get_sybers.range_homevelo_agent

Installs the **Home-Velo** Velociraptor agent on a range VM so it reports to the Home-Velo server,
in the one way that has been shown to work from inside a Ludus range: every platform runs the agent
on an **explicit client config** — the server's published `client.config.yaml` with the Proxmox
cluster CA added under `Client.Crypto.root_certs`. Nothing secret is carried in the role: the
published config (which holds the enrolment nonce) and the CA are fetched from the server's public
folder at deploy time, sha256-pinned, and merged on the Ludus host. The role runs at the Ludus
`user-defined-roles` stage and is self-contained (`dependencies: []`).

## The server

| | |
| --- | --- |
| Home-Velo | a Velociraptor **0.77.3** server on the operator's network; its address is `range_homevelo_agent_server_host` (set it in the range config's `global_role_vars`, the default is an RFC 5737 placeholder) |
| frontend / GUI | `https://<server-host>:8000/` (clients) and `:8889` (GUI); `use_self_signed_ssl: false`; the frontend certificate is issued by the **PVE Cluster Manager CA** of the Proxmox cluster with a SAN for the server's address |
| public folder | `https://<server-host>:8000/public/`: `velociraptor-client-amd64.msi` (repacked), `velociraptor-linux-amd64`, `velociraptor-darwin-amd64`, `pve-root-ca.crt`, `client.config.yaml`, `install.sh`, `install.ps1`, `AGENT_VERSION` |
| server firewall | the server's host firewall admits its own LAN on 8000/8889; range traffic arrives as the Ludus host's address (router NAT, then host NAT) and is admitted |
| containment | a contained range (`ludus testing start`) drops all egress; run `ludus testing allow -i <server-host>` after every `testing start`, or keep the address in an operator allow-list applied with `ludus testing allow -f` |

## What the role does

| platform | steps |
| --- | --- |
| all (controller) | download the platform's artifact, `pve-root-ca.crt` and `client.config.yaml` **once** to `/opt/ludus/resources/homevelo`, each pinned in `range_homevelo_agent_artifacts`; merge the CA into the config as `Client.Crypto.root_certs` (`client.config.homevelo.yaml`, mode 0600) |
| Windows | CA into `LocalMachine\Root` (as `install.ps1` does); the published MSI via `win_package`; the merged config → `C:\Program Files\Velociraptor\client.config.yaml`; the `Velociraptor` service's command line set to `Velociraptor.exe --config <that file> service run`; restart on change |
| Linux (Debian family) | CA into `/usr/local/share/ca-certificates` (as `install.sh` does); binary → `/usr/local/bin/velociraptor-client`; config → `/etc/velociraptor-homevelo.client.config.yaml`; own unit `velociraptor-homevelo.service` (`--config … client --quiet`) |
| macOS (amd64) | config → `/etc/velociraptor-homevelo.client.config.yaml`; binary → `/usr/local/bin/velociraptor-client`; `velociraptor-client --config <file> service install` → launchd `com.velocidex.velociraptor` (the plist keeps `--config`) |
| all | warn-only verify: service state and a TCP probe of the frontend from the VM |

## Why it is built this way

Three things that look right do **not** work from a range:

1. **The MSI's embedded config.** Installed as published (`msiexec /i … /quiet`, service on the embedded
   config), the Windows agents of a test range ran for over 20 minutes with the service started and
   the frontend port reachable, held no connection to the frontend and never enrolled. The same hosts
   enrolled within a minute once the service was pointed at the explicit config. Velociraptor's own
   `service install --config` is no substitute: it copies the config beside the binary and registers
   plain `service run`, so the embedded config still wins. Setting the service path is what works.
2. **macOS keychain trust over SSH.** `install.sh` runs `security add-trusted-cert -d -r trustRoot -k
   /Library/Keychains/System.keychain`, which needs an interactive authorization; from an SSH session
   it fails with `SecTrustSettingsSetTrustSettings: The authorization was denied since no user
   interaction was possible`. The role never touches the keychain; the CA travels inside the config
   (`Client.Crypto.root_certs`, which Velociraptor appends to its TLS root pool — `crypto/root.go`,
   `AddDefaultCerts`).
3. **The stock Linux installer collides with digger.** `velociraptor service install` on Linux writes
   `/usr/local/bin/velociraptor_client` and `velociraptor_client.service`, exactly what the CCXDFIR
   digger agent's `.deb` (`get_sybers.range_digger_agent`) owns on the same VMs. The role uses its own
   binary name, config path and unit, so both agents run side by side (digger keeps its own writeback
   file; on Windows digger is the separate `digger` service).

## Variables

| name | default | purpose |
| --- | --- | --- |
| `range_homevelo_agent_server_host` / `_server_port` | `203.0.113.10` (placeholder — set yours) / `8000` | the frontend; also the reachability check target |
| `range_homevelo_agent_base_url` | `https://<host>:<port>/public` | the server's public download folder |
| `range_homevelo_agent_artifacts` | see `defaults/main.yml` | filename → sha256 pins (recorded 2026-11-06, AGENT_VERSION 0.77.3) |
| `range_homevelo_agent_validate_certs` | `false` | controller-side TLS verification of the download (integrity comes from the pins) |
| `range_homevelo_agent_controller_cache_dir` | `/opt/ludus/resources/homevelo` | controller cache |
| `range_homevelo_agent_windows_config` | `C:\Program Files\Velociraptor\client.config.yaml` | explicit config the Windows service runs on |
| `range_homevelo_agent_linux_bin` / `_linux_config` / `_linux_service` | `/usr/local/bin/velociraptor-client` / `/etc/velociraptor-homevelo.client.config.yaml` / `velociraptor-homevelo` | Linux install, digger-safe |
| `range_homevelo_agent_darwin_bin` / `_darwin_config` / `_darwin_label` | `/usr/local/bin/velociraptor-client` / `/etc/velociraptor-homevelo.client.config.yaml` / `com.velocidex.velociraptor` | macOS install |
| `range_homevelo_agent_verify_connectivity` | `true` | warn-only TCP check to the frontend from each VM |

## Applying it

```bash
# installed per user by `ludus source add <this source> --all` (or --source-roles get_sybers.range_homevelo_agent);
# then, in the range config, set the server under global_role_vars:
#   global_role_vars:
#     range_homevelo_agent_server_host: <your Home-Velo address>
# add get_sybers.range_homevelo_agent to each VM's roles:, apply it with `ludus range config set`, and
ludus range deploy -t user-defined-roles --only-roles get_sybers.range_homevelo_agent [--limit localhost,<vm>,...]
```

Because a failed single-host play ends a Ludus deploy, run new platforms behind a `--limit` first.
The role is idempotent; re-running it restarts an agent only when its config or command line changed.

## Verifying enrolment

On the server, from the datastore, because a standalone
`velociraptor --config /etc/velociraptor/server.config.yaml query 'SELECT … FROM clients()'` returns
nothing on this server. Count, and list only hostnames; never print record contents (they hold
client keys and identifiers):

```bash
ls -d /opt/velociraptor/clients/C.*/ | wc -l                                  # enrolled clients
ls /opt/velociraptor/clients/C.*.db | wc -l                                   # interrogated (have hostname/OS)
grep -ahoE '<range-id>-[A-Za-z0-9-]+' /opt/velociraptor/clients/C.*.db | sort -u   # range hostnames seen
ss -tn state established '( sport = :8000 )' | grep -c <ludus-host-ip>        # live range connections (+1 if the Ludus host runs an agent)
```

Verified on a range spanning all three platforms: every VM enrolled, and the Windows agents enrolled
within two minutes of the service being pointed at the explicit config.

## When the server republishes

New agent version, new CA or new config: fetch each published file, recompute its `sha256sum`,
update `range_homevelo_agent_artifacts`, bump `meta/version.yml`, and re-run the role; agents restart
only where the merged config changed.
