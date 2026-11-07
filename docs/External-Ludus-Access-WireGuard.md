# External Ludus Access via WireGuard

Instructions for setting up external access to your Ludus lab through an additional WireGuard configuration. This setup adds a separate interface (`wg1.conf`) without changing anything else in Ludus.

## Assumed addressing

| Role | Address |
|---|---|
| Cloud VPN network | `192.168.100.0/24` |
| Cloud WireGuard server (VPN IP) | `192.168.100.1` |
| Cloud client | `192.168.100.100` |
| Ludus server, `wg1` interface | `192.168.100.10` |
| Ludus bridge network | `192.0.2.0/24` |
| Ludus range network | `10.2.10.0/24` |
| Cloud server endpoint | `<cloud-server-public-ip-or-fqdn>:51280` |

## 1. Ludus server: create `wg1.conf`

The iptables rules let the VPN network route into the Ludus network.

```ini
[Interface]
PrivateKey = <ludus-private-key>
Address = 192.168.100.10/32
PostUp = iptables -t nat -A POSTROUTING -s 192.168.100.0/24 -o vmbr1000 -j MASQUERADE
PostDown = iptables -t nat -D POSTROUTING -s 192.168.100.0/24 -o vmbr1000 -j MASQUERADE

[Peer]
PublicKey = <cloud-server-public-key>
AllowedIPs = 192.168.100.0/24
Endpoint = <cloud-server-public-ip-or-fqdn>:51280
```

## 2. Cloud WireGuard server

The iptables rules NAT VPN traffic out of the external (cloud) interface.

```ini
[Interface]
PrivateKey = <cloud-server-private-key>
Address = 192.168.100.1/32
ListenPort = 51280
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Peer: Ludus server
[Peer]
PublicKey = <ludus-public-key>
AllowedIPs = 192.168.100.10/32, 10.2.10.0/24, 192.0.2.0/24

# Peer: cloud client
[Peer]
PublicKey = <cloud-client-public-key>
AllowedIPs = 192.168.100.100/32
```

The Ludus peer's AllowedIPs cover the lab's VPN IP, the range network, and the bridge network. The cloud client peer covers only its own VPN IP.

## 3. Cloud client

```ini
[Interface]
PrivateKey = <cloud-client-private-key>
Address = 192.168.100.100/32

[Peer]
PublicKey = <cloud-server-public-key>
AllowedIPs = 192.168.100.0/24, 192.0.2.0/24, 10.2.10.0/24
Endpoint = <cloud-server-public-ip-or-fqdn>:51280
```

The client's AllowedIPs cover the VPN network, the bridge network, and the range network.

## Notes

- The source says `198.0.2.0/24` for the bridge network in one place. Every other reference, and the standard documentation range, gives `192.0.2.0/24`, so this conversion uses that.
- The source omits the cloud server's `PostDown` line in some places; the version above includes it as the mirror of `PostUp`.
- Keys are placeholders. Replace them with your own generated keys.
