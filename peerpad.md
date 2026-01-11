# PeerPad

A simple real-time text and file sharing app for two people on a local network (or Tailscale).

## Overview

PeerPad provides:
1. **Real-time text sharing** - Two text boxes: type in yours, see theirs
2. **Shared folder** - `~/PeerPad` directory (Syncthing integration planned)

## Tech Stack

- **Language**: Python 3.10+
- **GUI**: PyQt6 (looks native on KDE, works well on GNOME)
- **Networking**: asyncio + raw TCP sockets for text
- **File sync**: Syncthing (planned - managed via its REST API)

## Features

### Text Sharing (Implemented)
- Split window with two text areas:
  - **Top**: Your input (editable) - sent to peer in real-time
  - **Bottom**: Their input (read-only) - received from peer
- Full text sync on every change
- Connection status indicator

### Connection Management (Implemented)
- **CLI shortcuts**:
  ```bash
  peerpad --host              # Start hosting on default port
  peerpad --host -p 9999      # Host on custom port
  peerpad --connect 10.0.0.5  # Connect to peer
  peerpad --connect 10.0.0.5:9999  # Connect with custom port
  peerpad                     # Launch GUI, show connection dialog
  ```
- **GUI controls**:
  - Host/Connect dialog on startup (if no CLI args)
  - Menu to disconnect, reconnect, switch modes
  - Shows connection status and peer IP

### File Sharing (Implemented)
- App manages a `~/PeerPad` folder that syncs between peers
- Syncthing integration:
  1. Detects if Syncthing is installed (offers to install if not)
  2. Auto-starts Syncthing if not running
  3. Exchanges device IDs over the text connection automatically
  4. Configures the shared folder via REST API
  5. Shows sync status in the UI

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    PeerPad App                       │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐    │
│  │  Your Text (editable)                       │    │
│  │  ─────────────────────────────────────────  │    │
│  │                                             │    │
│  └─────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────┐    │
│  │  Their Text (read-only)                     │    │
│  │  ─────────────────────────────────────────  │    │
│  │                                             │    │
│  └─────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────┐    │
│  │ [Connect...] [Shared Folder]     │ Status   │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
         │
         │ TCP Socket
         │ (text sync)
         ▼
    ┌─────────┐
    │  Peer   │
    └─────────┘
```

## Protocol

Simple TCP with JSON messages (newline-delimited):
```json
{"type": "full_sync", "content": "current text"}       // Full text replacement
{"type": "text", "content": "a"}                       // Single keystroke (future)
{"type": "clear", "content": ""}                       // Clear text box
{"type": "syncthing_device_id", "content": "ABC123"}   // Syncthing device ID exchange
{"type": "syncthing_status", "content": "not_installed"} // Syncthing status
```

## Project Structure

```
peerpad/
├── peerpad.md           # This file (design doc)
├── install.sh           # Interactive setup script
├── run                  # Launcher script (activates venv)
├── requirements.txt     # Python dependencies
├── README.md            # User-facing documentation
├── .gitignore
└── peerpad/             # Python package
    ├── __init__.py
    ├── __main__.py      # Entry point, CLI parsing
    ├── app.py           # Main PyQt6 application
    ├── widgets.py       # Connection dialog
    ├── network.py       # TCP server/client, async handling
    └── syncthing.py     # Syncthing REST API integration
```

## Installation

```bash
git clone https://github.com/bbitmaster/peerpad.git
cd peerpad
./install.sh
```

### What install.sh Does

1. Detects distro (Arch-based or Debian-based)
2. Prompts before installing system packages
3. Creates virtualenv with system site-packages access
4. Falls back to pip for PyQt6 on older Ubuntu/Pop!_OS
5. Creates `~/PeerPad` shared folder

**On Arch/CachyOS:**
```bash
sudo pacman -S --needed python python-pyqt6
```

**On Ubuntu 24.04:**
```bash
sudo apt install python3 python3-venv python3-pyqt6
```

**On Pop!_OS 22.04 / Ubuntu 22.04:**
```bash
sudo apt install python3 python3-venv python3-pip
pip install PyQt6  # In virtualenv
```

## Implementation Status

### Phase 1: Core Text Sharing ✅
- [x] Basic PyQt6 window with two text areas
- [x] TCP server/client with asyncio
- [x] Real-time text sync
- [x] CLI argument parsing (--host, --connect)

### Phase 2: Connection UI ✅
- [x] Connection dialog (shown when no CLI args)
- [x] Status bar showing connection state
- [x] Menu for disconnect/reconnect
- [x] Error handling

### Phase 3: Syncthing Integration ✅
- [x] Detect if Syncthing is installed
- [x] REST API wrapper to configure Syncthing
- [x] Device ID exchange over text connection
- [x] Shared folder setup automation
- [x] Auto-start Syncthing if not running
- [x] Offer to install Syncthing if missing

### Phase 4: Polish (Future)
- [ ] System tray option
- [ ] Notifications for connection events
- [ ] Dark/light theme following system
- [ ] Reconnection on disconnect

## Notes

- Default port: 9876
- Shared folder: `~/PeerPad`
- Tailscale IPs are typically `100.x.x.x`
- PyQt6 uses Qt6 which looks good on both KDE and GNOME
