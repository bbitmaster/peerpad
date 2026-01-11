# PeerPad

Real-time text and file sharing between two peers over a local network or Tailscale.

## Features

- **Real-time text sync** - Type in your box, it appears on your peer's screen instantly
- **Shared folder sync** - `~/PeerPad` directory automatically syncs between peers via Syncthing
- **Simple P2P connection** - One person hosts, the other connects via IP
- **Cross-distro support** - Works on Arch-based (CachyOS, Manjaro) and Debian-based (Ubuntu, Pop!_OS)

## Quick Start

```bash
git clone https://github.com/bbitmaster/peerpad.git
cd peerpad
./install.sh
```

The installer will:
- Detect your distro and install dependencies (prompts before running sudo)
- Optionally install Syncthing for folder sync
- Create a Python virtualenv
- Set up the `~/PeerPad` shared folder

## Usage

```bash
# Launch with GUI connection dialog
./run

# Host mode (wait for peer to connect)
./run --host

# Connect to a peer
./run --connect 192.168.1.5
./run --connect 100.64.0.1:9876  # Tailscale IP with custom port

# Custom port
./run --host -p 8888
```

## How It Works

### Text Sharing
1. **Person A** runs `./run --host` and shares their IP address
2. **Person B** runs `./run --connect <Person A's IP>`
3. Both see a split window:
   - **Top box**: Your text (editable) - synced to peer in real-time
   - **Bottom box**: Their text (read-only) - received from peer

### Folder Sharing
When both peers connect:
1. PeerPad automatically exchanges Syncthing device IDs
2. The `~/PeerPad` folder is configured to sync between both machines
3. Any files placed in the folder will sync automatically

The sync status is shown in the app:
- **Sync: Active** - Folder is syncing with peer
- **Sync: Not available** - Syncthing not installed on one/both machines
- **Sync: Same machine** - Both peers are on the same computer

## Supported Systems

| Distro | Status |
|--------|--------|
| CachyOS / Arch | Tested |
| Ubuntu 24.04 | Supported |
| Pop!_OS 22.04 | Supported (PyQt6 via pip) |
| Other Arch-based | Should work |
| Other Debian-based | Should work |

## Requirements

Handled automatically by `install.sh`:
- Python 3.10+
- PyQt6
- requests
- (Optional) Syncthing for folder sync

## License

MIT
