"""Syncthing integration for PeerPad shared folder sync."""

import os
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests


class SyncthingManager:
    """Manages Syncthing for folder synchronization."""

    DEFAULT_API_URL = "http://127.0.0.1:8384"
    PEERPAD_FOLDER_ID = "peerpad-shared"
    PEERPAD_FOLDER_LABEL = "PeerPad"

    def __init__(self, api_url: str = DEFAULT_API_URL):
        self._api_url = api_url
        self._api_key: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None

    @staticmethod
    def is_installed() -> bool:
        """Check if Syncthing is installed."""
        try:
            result = subprocess.run(
                ["syncthing", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def is_running(self) -> bool:
        """Check if Syncthing is running by trying to connect to API."""
        try:
            resp = requests.get(
                f"{self._api_url}/rest/system/ping",
                timeout=2
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def get_api_key(self) -> Optional[str]:
        """Get API key from Syncthing config file."""
        if self._api_key:
            return self._api_key

        config_paths = [
            Path.home() / ".config" / "syncthing" / "config.xml",
            Path.home() / ".local" / "state" / "syncthing" / "config.xml",
            Path("/var/lib/syncthing/.config/syncthing/config.xml"),
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    tree = ET.parse(config_path)
                    root = tree.getroot()
                    gui = root.find("gui")
                    if gui is not None:
                        api_key = gui.find("apikey")
                        if api_key is not None and api_key.text:
                            self._api_key = api_key.text
                            return self._api_key
                except ET.ParseError:
                    continue

        return None

    def start(self, timeout: int = 30) -> bool:
        """Start Syncthing if not running. Returns True if started successfully."""
        if self.is_running():
            return True

        if not self.is_installed():
            return False

        try:
            self._process = subprocess.Popen(
                ["syncthing", "serve", "--no-browser", "--no-default-folder"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            # Wait for API to become available
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.is_running():
                    # Give it a moment to fully initialize
                    time.sleep(0.5)
                    return True
                time.sleep(0.5)

            return False
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Make an authenticated request to the Syncthing API."""
        api_key = self.get_api_key()
        if not api_key:
            return None

        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = api_key

        try:
            resp = requests.request(
                method,
                f"{self._api_url}{endpoint}",
                headers=headers,
                timeout=10,
                **kwargs
            )
            return resp
        except requests.RequestException:
            return None

    def get_device_id(self) -> Optional[str]:
        """Get this machine's Syncthing device ID."""
        resp = self._request("GET", "/rest/system/status")
        if resp and resp.status_code == 200:
            data = resp.json()
            return data.get("myID")
        return None

    def get_config(self) -> Optional[dict]:
        """Get the full Syncthing configuration."""
        resp = self._request("GET", "/rest/config")
        if resp and resp.status_code == 200:
            return resp.json()
        return None

    def device_exists(self, device_id: str) -> bool:
        """Check if a device is already configured."""
        config = self.get_config()
        if not config:
            return False

        for device in config.get("devices", []):
            if device.get("deviceID") == device_id:
                return True
        return False

    def add_device(self, device_id: str, name: str = "PeerPad Peer") -> bool:
        """Add a device to Syncthing."""
        if self.device_exists(device_id):
            return True  # Already exists

        device_config = {
            "deviceID": device_id,
            "name": name,
            "addresses": ["dynamic"],
            "compression": "metadata",
            "introducer": False,
            "paused": False,
            "autoAcceptFolders": False,
        }

        resp = self._request("POST", "/rest/config/devices", json=device_config)
        return resp is not None and resp.status_code in (200, 201)

    def folder_exists(self, folder_id: str = PEERPAD_FOLDER_ID) -> bool:
        """Check if the PeerPad folder is already configured."""
        config = self.get_config()
        if not config:
            return False

        for folder in config.get("folders", []):
            if folder.get("id") == folder_id:
                return True
        return False

    def get_folder_devices(self, folder_id: str = PEERPAD_FOLDER_ID) -> list[str]:
        """Get list of device IDs sharing a folder."""
        config = self.get_config()
        if not config:
            return []

        for folder in config.get("folders", []):
            if folder.get("id") == folder_id:
                return [d.get("deviceID") for d in folder.get("devices", [])]
        return []

    def setup_shared_folder(self, folder_path: str, peer_device_id: str) -> bool:
        """Set up the shared folder with peer device."""
        my_device_id = self.get_device_id()
        if not my_device_id:
            return False

        # Ensure peer device is added
        if not self.add_device(peer_device_id):
            return False

        if self.folder_exists():
            # Folder exists, just add the peer device if not already shared
            existing_devices = self.get_folder_devices()
            if peer_device_id in existing_devices:
                return True  # Already configured

            # Add peer to existing folder
            config = self.get_config()
            if not config:
                return False

            for folder in config.get("folders", []):
                if folder.get("id") == self.PEERPAD_FOLDER_ID:
                    folder["devices"].append({
                        "deviceID": peer_device_id,
                        "introducedBy": "",
                        "encryptionPassword": ""
                    })
                    resp = self._request("PUT", "/rest/config/folders/" + self.PEERPAD_FOLDER_ID, json=folder)
                    return resp is not None and resp.status_code == 200
            return False
        else:
            # Create new folder
            folder_config = {
                "id": self.PEERPAD_FOLDER_ID,
                "label": self.PEERPAD_FOLDER_LABEL,
                "path": folder_path,
                "type": "sendreceive",
                "devices": [
                    {"deviceID": my_device_id, "introducedBy": "", "encryptionPassword": ""},
                    {"deviceID": peer_device_id, "introducedBy": "", "encryptionPassword": ""}
                ],
                "rescanIntervalS": 60,
                "fsWatcherEnabled": True,
                "fsWatcherDelayS": 1,
                "ignorePerms": False,
                "autoNormalize": True,
            }

            resp = self._request("POST", "/rest/config/folders", json=folder_config)
            return resp is not None and resp.status_code in (200, 201)

    def get_folder_status(self, folder_id: str = PEERPAD_FOLDER_ID) -> Optional[dict]:
        """Get the sync status of a folder."""
        resp = self._request("GET", f"/rest/db/status?folder={folder_id}")
        if resp and resp.status_code == 200:
            return resp.json()
        return None

    @staticmethod
    def get_distro() -> Optional[str]:
        """Detect the Linux distribution type."""
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()
                if "arch" in content or "cachyos" in content or "manjaro" in content:
                    return "arch"
                elif "ubuntu" in content or "debian" in content or "pop" in content or "mint" in content:
                    return "debian"
        except FileNotFoundError:
            pass
        return None

    @staticmethod
    def get_install_command() -> Optional[list[str]]:
        """Get the installation command for the current distro."""
        distro = SyncthingManager.get_distro()
        if distro == "arch":
            return ["sudo", "pacman", "-S", "--noconfirm", "syncthing"]
        elif distro == "debian":
            return ["sudo", "apt", "install", "-y", "syncthing"]
        return None

    @staticmethod
    def install() -> tuple[bool, str]:
        """Install Syncthing. Returns (success, message)."""
        cmd = SyncthingManager.get_install_command()
        if not cmd:
            return False, "Unknown distribution. Please install Syncthing manually."

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                return True, "Syncthing installed successfully!"
            else:
                return False, f"Installation failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Installation timed out."
        except subprocess.SubprocessError as e:
            return False, f"Installation error: {e}"
