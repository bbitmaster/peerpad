"""Network module for TCP server/client communication."""

import asyncio
import json
import socket
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class MessageType(Enum):
    TEXT = "text"
    CLEAR = "clear"
    FULL_SYNC = "full_sync"
    SYNC_REQUEST = "sync_request"


@dataclass
class Message:
    type: MessageType
    content: str = ""

    def to_json(self) -> bytes:
        data = {"type": self.type.value, "content": self.content}
        return json.dumps(data).encode() + b"\n"

    @classmethod
    def from_json(cls, data: bytes) -> "Message":
        parsed = json.loads(data.decode())
        return cls(
            type=MessageType(parsed["type"]),
            content=parsed.get("content", "")
        )


class NetworkWorker(QObject):
    """Runs asyncio event loop in a separate thread."""

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(object)  # Message
    error = pyqtSignal(str)
    client_connected = pyqtSignal(str)  # peer address

    def __init__(self):
        super().__init__()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server: Optional[asyncio.Server] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._running = False
        self._is_host = False

    def run(self):
        """Main entry point when thread starts."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._running = True
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def stop(self):
        """Stop the event loop."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def host(self, port: int):
        """Start hosting on the given port."""
        if self._loop:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._host(port), loop=self._loop)
            )

    def connect(self, host: str, port: int):
        """Connect to a host."""
        if self._loop:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._connect(host, port), loop=self._loop)
            )

    def disconnect(self):
        """Disconnect from peer."""
        if self._loop:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._disconnect(), loop=self._loop)
            )

    def send_message(self, msg: Message):
        """Send a message to the peer."""
        if self._loop and self._writer:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._send(msg), loop=self._loop)
            )

    async def _host(self, port: int):
        """Async host implementation."""
        try:
            self._is_host = True
            self._server = await asyncio.start_server(
                self._handle_client,
                "0.0.0.0",
                port
            )
            addrs = ", ".join(str(sock.getsockname()) for sock in self._server.sockets)
            print(f"Hosting on {addrs}")
        except Exception as e:
            self.error.emit(f"Failed to host: {e}")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming client connection."""
        # Only allow one connection at a time
        if self._writer:
            writer.close()
            await writer.wait_closed()
            return

        self._reader = reader
        self._writer = writer
        peer = writer.get_extra_info("peername")
        peer_str = f"{peer[0]}:{peer[1]}" if peer else "unknown"

        self.client_connected.emit(peer_str)
        self.connected.emit()

        await self._read_loop()

    async def _connect(self, host: str, port: int):
        """Async connect implementation."""
        try:
            self._is_host = False
            self._reader, self._writer = await asyncio.open_connection(host, port)
            self.connected.emit()
            await self._read_loop()
        except Exception as e:
            self.error.emit(f"Failed to connect: {e}")

    async def _read_loop(self):
        """Read messages from peer."""
        try:
            while self._running and self._reader:
                line = await self._reader.readline()
                if not line:
                    break
                try:
                    msg = Message.from_json(line)
                    self.message_received.emit(msg)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Invalid message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.error.emit(f"Connection error: {e}")
        finally:
            await self._disconnect()

    async def _send(self, msg: Message):
        """Send a message."""
        if self._writer:
            try:
                self._writer.write(msg.to_json())
                await self._writer.drain()
            except Exception as e:
                self.error.emit(f"Send error: {e}")

    async def _disconnect(self):
        """Close connections."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None
            self.disconnected.emit()

        if self._server and not self._is_host:
            self._server.close()
            self._server = None


class NetworkManager(QObject):
    """Manages network thread and provides clean interface."""

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(object)
    error = pyqtSignal(str)
    client_connected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._thread = QThread()
        self._worker = NetworkWorker()
        self._worker.moveToThread(self._thread)

        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.connected.connect(self.connected)
        self._worker.disconnected.connect(self.disconnected)
        self._worker.message_received.connect(self.message_received)
        self._worker.error.connect(self.error)
        self._worker.client_connected.connect(self.client_connected)

        self._thread.start()

    def host(self, port: int = 9876):
        """Start hosting."""
        self._worker.host(port)

    def connect_to(self, host: str, port: int = 9876):
        """Connect to a peer."""
        self._worker.connect(host, port)

    def disconnect(self):
        """Disconnect from peer."""
        self._worker.disconnect()

    def send_text(self, text: str):
        """Send text content."""
        self._worker.send_message(Message(MessageType.TEXT, text))

    def send_full_sync(self, text: str):
        """Send full text sync."""
        self._worker.send_message(Message(MessageType.FULL_SYNC, text))

    def send_clear(self):
        """Send clear signal."""
        self._worker.send_message(Message(MessageType.CLEAR))

    def cleanup(self):
        """Clean shutdown."""
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(1000)


def get_local_ips() -> list[str]:
    """Get local IP addresses."""
    ips = []
    try:
        # Get all network interfaces
        hostname = socket.gethostname()
        ips = socket.gethostbyname_ex(hostname)[2]
    except (socket.error, socket.herror, socket.gaierror):
        pass

    # Also try to get Tailscale IP (usually 100.x.x.x)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("100.100.100.100", 80))  # Tailscale magic DNS
        ip = s.getsockname()[0]
        if ip not in ips:
            ips.insert(0, ip)
        s.close()
    except (socket.error, OSError):
        pass

    return ips
