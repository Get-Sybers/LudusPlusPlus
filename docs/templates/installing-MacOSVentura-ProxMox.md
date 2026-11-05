# Installing macOS 13 Ventura on Proxmox 7.2

This tutorial for installing macOS 13 Ventura has been adapted for Proxmox from Kholia's OSX-KVM project and Leoyzen's OpenCore configuration for KVM. You can get the full source code of the OpenCore release on the author's GitHub.

## Requirements

You'll need Proxmox 7.2 already installed, plus a real Mac to fetch the OSK key.

Ventura requires that your CPU supports AVX2, so for Intel CPUs it must be at least as new as Haswell. However, the CryptexFixup kext works around this restriction, allowing Ventura to run on CPUs that only support SSE 4.2 and AVX1.

> **Note:** AMD graphics card drivers won't work in this situation, and other apps that assume AVX2 is present could break. See the CryptexFixup readme for details.

Modern AMD CPUs also support AVX2 and should work with this guide.

### Checking your TSC

Since Monterey, your host must have a working TSC (timestamp counter). Otherwise, if the VM has more than one core, macOS will observe skew between cores and panic when time appears to go backwards.

To check, run this on Proxmox:

```bash
dmesg | grep -i -e tsc -e clocksource
```

**On a working host**, you'll see:

```
tsc: Refined TSC clocksource calibration: 3399.998 MHz
clocksource: tsc: mask: 0xffffffffffffffff max_cycles: 0x31024cfe468, max_idle_ns: 440795307017 ns
clocksource: Switched to clocksource tsc
```

**On a broken host**, you'll see:

```
TSC synchronization [CPU#0 -> CPU#1]:
Measured 3358870891203288 cycles TSC warp between CPUs, turning off TSC clock.
tsc: Marking TSC unstable due to check_tsc_sync_source failed
clocksource: Switched to clocksource hpet
kvm: SMP vm created on host with unstable TSC; guest TSC will not be reliable
```

If you have a broken TSC, sometimes you can simply power-cycle the host to resync the TSCs, especially if the server has a high uptime.

---

## Step 1: Create an Installation ISO

Download the OSX-KVM repository from [github.com/thenickdude/OSX-KVM](https://github.com/thenickdude/OSX-KVM) using the download button, then unzip it.

### Install build requirements

**On macOS**, open Terminal and install the command line tools:

```bash
xcode-select --install
```

**On Linux** (Ubuntu or similar; package names may vary on other distributions):

```bash
sudo apt install qemu-utils make
```

### Build the recovery image

From the root of OSX-KVM, run:

```bash
cd scripts/ventura
make Ventura-recovery.img
```

This downloads the Ventura installer from Apple's software distribution servers and builds a `Ventura-recovery.img` file. Upload it to your Proxmox ISO store directory (typically `/var/lib/vz/template/iso`). Although it lives with the ISOs so you can use Proxmox's ISO picker, it is a raw disk image rather than a true ISO.

### Build a full installer (macOS only)

If you're building on macOS, you can create a full installer instead. macOS won't need to download Ventura files during installation, so no Internet connection is required:

```bash
cd scripts/ventura
make Ventura-full.img
```

This option isn't available when building on Linux.

---

## Step 2: Prepare an OpenCore Image

Download `OpenCore.iso.gz` from the newest release in the repository (v19 or newer), unpack it by double-clicking, and upload it to `/var/lib/vz/template/iso` on Proxmox. Although it has an `.iso` extension, it's actually a hard disk image.

---

## Step 3: Fetch the OSK Authentication Key

macOS checks that it's running on real Mac hardware and refuses to boot on third-party hardware. To get around this, you read an authentication key (the OSK) from your real Mac.

1. Save the first block of C code from the source page as `smc_read.c`.
2. In a terminal, change into that directory and run:

```bash
xcode-select --install   # If you don't already have gcc
gcc -o smc_read smc_read.c -framework IOKit
./smc_read
```

The program prints a 64-character OSK. Make a note of it.

> **Note:** Every Mac uses the same OSK, so don't be surprised that it doesn't look like a random string.

---

## Step 4: Create the VM

In the Proxmox web UI, create a new virtual machine with these settings:

| Setting | Value |
|---|---|
| **ID** | Note this down, you'll need it later |
| **ISO** | Select the OpenCore ISO you uploaded |
| **OS type** | Other |
| **Graphics** | VMware Compatible |
| **BIOS** | OVMF (UEFI) |
| **Machine** | Q35 |
| **QEMU Agent** | Ticked |
| **EFI Disk** | Ticked, pick storage. **Untick "pre-enroll keys"** |
| **Hard disk** | 64 GB or greater (32 GB is too small). Bus/Device: VirtIO Block 0. Enable **discard** for TRIM |
| **Cores** | A power of two (1, 2, 4, 8) |
| **CPU** | Haswell |
| **Memory** | 4096 MB, with **ballooning disabled** |
| **Network model** | VirtIO (paravirtualized) |

**Options tab:** Ensure **"Use tablet for pointer"** is set to Yes (the default).

**Hardware tab:** Add a second DVD drive at **IDE0** and set it to use `Ventura-full.img`.

Don't start the VM yet. First, SSH into your Proxmox server to edit the configuration.

### Edit the VM configuration

Open `/etc/pve/qemu-server/YOUR-VM-ID-HERE.conf` in nano or vim and add this line, substituting your OSK:

```
args: -device isa-applesmc,osk="THE-OSK-YOU-EXTRACTED-GOES-HERE" -smbios type=2 -device usb-kbd,bus=ehci.0,port=2 -global nec-usb-xhci.msi=off -global ICH9-LPC.acpi-pci-hotplug-with-bridge-support=off -cpu host,vendor=GenuineIntel,+invtsc,+hypervisor,kvm=on,vmware-cpuid-freq=on
```

Keep the args on a single line. Here's what the flags do:

- **USB keyboard:** macOS doesn't support QEMU's default PS/2 keyboard.
- **MSI disabled on the USB controller:** Fixes QEMU panics when USB 3 devices are passed through.
- **ACPI PCIe hotplug disabled:** Fixes VMs with passthrough devices.

**Optional:** Remove `+invtsc` from the `-cpu` list if your CPU doesn't support it, or if you want to migrate a running VM between Proxmox nodes.

**AMD CPUs:** If the installer reboots while loading or the loading bar doesn't appear, replace `-cpu host` with `-cpu Haswell-noTSX`. The author needed this on an AMD EPYC 7R13.

Next, find the lines defining the two "ISOs" (`ide0` and `ide2`) and replace `,media=cdrom` with `,cache=unsafe`. This makes them behave as hard disks rather than DVD drives.

Save, return to the Options tab, and set the boot order so **IDE2** (the OpenCore image) comes first. Your final configuration should look something like this:

```
agent: 1
args: -device isa-applesmc,osk="..." -smbios type=2 -device usb-kbd,bus=ehci.0,port=2 -global nec-usb-xhci.msi=off -global ICH9-LPC.acpi-pci-hotplug-with-bridge-support=off -cpu host,vendor=GenuineIntel,+invtsc,+hypervisor,kvm=on,vmware-cpuid-freq=on
balloon: 0
bios: ovmf
boot: order=ide2;virtio0
cores: 4
cpu: Haswell
efidisk0: local-lvm:vm-100-disk-0,efitype=4m,size=4M
ide0: local:iso/Ventura-full.img,cache=unsafe,size=14G
ide2: local:iso/OpenCore-v18.iso,cache=unsafe,size=150M
machine: q35
memory: 4096
meta: creation-qemu=6.2.0,ctime=1655001118
name: macos-ventura
net0: virtio=...,bridge=vmbr0,firewall=1
numa: 0
ostype: other
scsihw: virtio-scsi-single
smbios1: uuid=...
sockets: 1
vga: vmware
virtio0: local-lvm:vm-100-disk-1,cache=unsafe,discard=on,iothread=1,size=64G
vmgenid: ...
```

---

## Step 5: Configure Proxmox

On Proxmox, run the following to avoid a bootloop during macOS boot:

```bash
echo 1 > /sys/module/kvm/parameters/ignore_msrs
```

To make this persist across reboots:

```bash
echo "options kvm ignore_msrs=Y" >> /etc/modprobe.d/kvm.conf && update-initramfs -k all -u
```

---

## Step 6: Install Ventura

1. Start the VM. It should boot to the OpenCore boot picker.
2. Press Enter on the **"Install macOS 13 Ventura"** entry. The installer should appear.
   > If your keyboard isn't working, leave the Proxmox Console page and re-enter it.
3. Select **Disk Utility** and erase the main disk (it appears as *VirtIO Block Media*). Choose **APFS** and name it something like "Main".
4. Quit Disk Utility from the top menu (**Disk Utility > Quit Disk Utility**).
5. Proceed with the installation.

### During installation

- The VM will reboot a couple of times in quick succession. Each time, **manually select the "macOS Installer" entry** (the one with the hard disk icon). It won't be selected automatically.
- If the keyboard stops responding, exit and re-enter the Console tab in Proxmox.
- If a "prohibited" sign appears, press **Reset** on the VM and try again.
- Once the installer entry disappears, select your main disk (e.g. "Main") to boot.
- Keep selecting the "Main" entry until you boot into Ventura.

Answer the initial setup questions to log in.

> **Tip:** Hold off on logging into your Apple ID until you've configured your Mac's serial number in OpenCore. Otherwise, a Mac with the default shared serial number will be added to your Apple ID.

The first boot will be sluggish for a few minutes while the system performs housekeeping tasks.

---

## Step 7: Make the OpenCore Install Permanent

You're currently booting OpenCore from the attached ISO. To install it to the hard drive instead:

1. Open Terminal and run `diskutil list` to see your drives.
2. Copy the EFI partition from the OpenCore CD over the EFI partition on the hard disk:

```bash
sudo dd if=<source> of=<dest>
```

The OpenCore CD is the small (~150 MB) disk with only an EFI partition. The main hard disk is the one with the large (>30 GB) Apple_APFS "Container" partition.

In the author's case, these were `disk2s1` and `disk0s1`, so the command was:

```bash
sudo dd if=/dev/disk2s1 of=/dev/disk0s1
```

> **Warning:** If you get these names wrong, you'll overwrite the wrong disk and need to start the installation over.

3. Shut down the VM and remove both the OpenCore and Ventura installer drives from the Hardware tab.
4. On the Options tab, set the boot order so `virtio0` (your disk) is first.
5. Boot up. You should see the OpenCore boot menu. Select your "Main" disk to boot Ventura.

---

## Additional Configuration

### Sleep management

Ventura may not wake from sleep using mouse or keyboard. You can either disable system sleep in Energy Saver settings, or wake the VM from Proxmox:

```bash
qm monitor YOUR-VM-ID-HERE
system_wakeup
quit
```

### Editing OpenCore / EFI settings

The `Configuration.pdf` explaining `config.plist` is included with the OpenCore release on GitHub.

**From within macOS:** First find your EFI partition's identifier:

```bash
diskutil list
```

Example output:

```
/dev/disk0 (external, physical):
   #:                   TYPE NAME              SIZE       IDENTIFIER
   0:  GUID_partition_scheme                  *512.1 GB   disk0
   1:                    EFI EFI               209.7 MB   disk0s1
   2:             Apple_APFS Container disk1   511.9 GB   disk0s2
```

Then mount it:

```bash
sudo mkdir /Volumes/EFI
sudo mount -t msdos /dev/disk0s1 /Volumes/EFI
```

Edit `/Volumes/EFI/OC/config.plist` with a text editor. **Avoid TextEdit**, as it inserts curly quotes that break the file. Use a dedicated plist editor or Xcode instead.

**If macOS won't boot:** Use the **UEFI Shell** option in the OpenCore boot menu:

1. Enter `FS0:` and press Enter (if the file isn't found, try `fs1:`).
2. Run `edit EFI\OC\config.plist`.
3. When finished, press **Ctrl+Q**, then **Y** to save.
4. Run `exit` to return to the OpenCore menu, then reboot.

**From the Proxmox host:** If booting from an attached `OpenCore.img`, mount the file as a loop device. If booting from the VM's disk, it must be in raw format (typical for LVM or ZFS) rather than qcow2.

```bash
# Mount an OpenCore image:
losetup --partscan /dev/loop0 /var/lib/vz/template/iso/OpenCore-v15.img
# or a VM boot disk:
losetup --partscan /dev/loop0 /dev/zvol/tank/vms/vm-100-disk-1

mount /dev/loop0p1 /mnt
```

Edit `/mnt/EFI/OC/config.plist`, then unmount:

```bash
umount /mnt
losetup --detach /dev/loop0
```

### Automatic boot

Set `Misc/Boot/Timeout` in `config.plist` to a non-zero value to auto-select the default boot option after that many seconds. This is disabled by default because it causes the installer ISO to return to its main menu instead of continuing the second installation stage.

To set the default boot option manually, press **Ctrl+Enter** on it.

### Verbose boot

- To boot in Verbose mode, press **Cmd+V** at the OpenCore menu before pressing Enter (no need to hold it down).
- If a kernel panic reboots the system too quickly to read, add `debug=0x100` to the kernel arguments in `config.plist`.

### Changing screen resolution

Edit `UEFI/Output/Resolution` in `config.plist`. The default is `1920×1080@32`.

Available modes are listed in the OVMF menu. Press **F2** at guest boot and choose **Device Manager > OVMF Platform Configuration**.

### Video performance

There's no guest video acceleration for macOS, so video performance is poor.

- In Google Chrome, turn off **"Use hardware acceleration when available"** to fix missing or flickering elements, especially video. Safari may work better.
- For much better frame rates and latency, enable **Screen Sharing** in the VM's Sharing settings and connect from a real Mac using the Screen Sharing app. RealVNC clients also work.
- For near-native performance, pass through a compatible video card using PCIe passthrough (AMD cards only).

### USB passthrough

To use a keyboard and mouse plugged directly into Proxmox:

1. Run `qm monitor YOUR-VM-ID-HERE`, then `info usbhost` to list USB devices:

```
qm> info usbhost
 Bus 3, Addr 12, Port 6, Speed 480 Mb/s
 Class 00: USB device 8564:1000, Mass Storage Device
 Bus 3, Addr 11, Port 5.4, Speed 12 Mb/s
 Class 00: USB device 04d9:0141, USB Keyboard
 Bus 3, Addr 10, Port 5.1.2, Speed 12 Mb/s
 Class 00: USB device 046d:c52b, USB Receiver
 Bus 3, Addr 9, Port 14.4, Speed 12 Mb/s
 Class 00: USB device 046d:c227, G15 GamePanel LCD
 Bus 3, Addr 8, Port 14.1, Speed 1.5 Mb/s
 Class 00: USB device 046d:c226, G15 Gaming Keyboard
```

2. Quit `qm`, then add devices using their IDs:

```bash
qm set YOUR-VM-ID-HERE -usb1 host=04d9:0141
qm set YOUR-VM-ID-HERE -usb2 host=046d:c52b
```

3. Reboot the VM for the changes to apply.

For better compatibility, pass through an entire USB controller using Proxmox's PCIe passthrough feature.

### Odd core counts

macOS requires a power-of-two core count (1, 2, 4, 8), but it accepts odd socket counts. On AMD, if you want 6 cores, configure **3 sockets with 2 cores each**.

---

## Troubleshooting

### Guest boots to the UEFI shell

This often happens after updating OpenCore. Fix the boot entries:

1. At the very start of boot, press **F2** to enter UEFI settings.
2. **Remove old entries:** Go to **Boot Maintenance > Boot Options > Delete Boot Option**. Use the spacebar to tick any old Clover or OpenCore entries. **Don't tick "EFI Internal Shell"**. Select **Commit Changes and Exit**.
3. **Add the OpenCore entry:** Select **Add Boot Option**, navigate to `EFI/OC/OpenCore.efi`, and name it "OpenCore". Commit Changes and Exit.
4. **Reorder:** Go to **Change Boot Order** and move OpenCore to the top. Commit Changes and Exit.
5. Back out to the main menu, choose **Reset**, and you should boot into OpenCore.

### iMessage

iCloud and the App Store should work already. For iMessage, mark your network adapter as built-in by following the guide at [dortania.github.io](https://dortania.github.io/OpenCore-Post-Install/universal/iservices.html#fixing-en0).

---

## Maintenance

### Disabling SIP (System Integrity Protection)

This may be needed to run unsigned kexts or perform other modifications.

1. Select **Recovery** from the OpenCore boot menu.
2. Open Terminal from the top menu and run:

```bash
csrutil disable --no-internal
```

3. Reboot.

### Upgrading OpenCore

Sometimes you need a newer OpenCore release to support a macOS update. This assumes you have no `config.plist` customizations to keep.

> **Important:** Take a snapshot first so you can roll back if something goes wrong.

**If macOS still boots:** Update from within the guest. Mount your EFI partition (see "Editing OpenCore / EFI settings"), delete the `EFI` folder, and replace it with the one from `OpenCoreEFIFolder.zip` in the new release. Empty the Trash first if needed.

**If macOS won't boot:**

1. Unpack and upload the new OpenCore ISO to Proxmox's ISO store.
2. Add a new CD drive to the VM using that ISO.
3. In the Proxmox terminal, edit the VM config in `/etc/pve/qemu-server` and replace `media=cdrom` with `cache=unsafe` for the OpenCore drive.
4. On the Options tab, set the new OpenCore drive as first in the boot order.
5. Boot into macOS from the new drive, then follow "Make the OpenCore Install Permanent" to write it to your main disk. Afterwards, detach the OpenCore drive.

### Upgrading from macOS Monterey

> **Important:** Make a backup or snapshot first.

1. **Update OpenCore to v19** before upgrading (see the section above). Reboot and confirm Monterey still boots.
2. **Disable PCIe passthrough devices** (especially video cards) and set `vga: vmware`. This lets you install from Proxmox's web console during the upgrade and avoids passthrough-related installer problems, including host lockups caused by the AMD Reset Bug.
3. **AMD CPUs:** Replace the `-cpu` argument in your args line with:

```
-cpu Haswell-noTSX,vendor=GenuineIntel,+invtsc,+hypervisor,kvm=on,vmware-cpuid-freq=on
```

Intel CPUs should work with `-cpu host`.

4. **Upgrade:** If your CPU supports AVX2, use Software Update or the App Store as on a real Mac.
   - If the update doesn't appear, check your SIP mode with `csrutil status`. If it says "Apple Internal", reboot, select **Recovery** at the OpenCore menu, and run `csrutil enable --no-internal` (or `csrutil disable --no-internal`). Then reboot into macOS and try again.

**Alternative:** Build a Ventura full or recovery installer and install over Monterey. This keeps your user data intact.

If your CPU doesn't support AVX2, you'll need to create a full or recovery installer, since the Monterey and Big Sur kernel patch that allows the Ventura App Store app to run inside macOS isn't enabled.
