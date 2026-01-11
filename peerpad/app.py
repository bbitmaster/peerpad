"""Main application window for PeerPad."""

import os
import subprocess
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QPushButton,
    QSplitter,
    QFrame,
    QStatusBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont

from .network import NetworkManager, Message, MessageType
from .widgets import ConnectionDialog


class PeerPadWindow(QMainWindow):
    """Main application window."""

    def __init__(self, host_mode: bool = False, connect_to: str = None, port: int = 9876):
        super().__init__()
        self.setWindowTitle("PeerPad")
        self.setMinimumSize(600, 500)

        self._network = NetworkManager()
        self._is_connected = False
        self._is_host = False
        self._suppress_text_signal = False

        self._setup_ui()
        self._setup_menu()
        self._connect_signals()

        # Handle CLI arguments
        if host_mode:
            QTimer.singleShot(100, lambda: self._start_host(port))
        elif connect_to:
            QTimer.singleShot(100, lambda: self._start_connect(connect_to, port))
        else:
            # Show connection dialog
            QTimer.singleShot(100, self._show_connection_dialog)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)

        # Splitter for the two text areas
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Your text area (top)
        your_frame = QFrame()
        your_layout = QVBoxLayout(your_frame)
        your_layout.setContentsMargins(0, 0, 0, 0)

        your_header = QHBoxLayout()
        your_label = QLabel("Your Text")
        your_label.setStyleSheet("font-weight: bold;")
        self._clear_yours_btn = QPushButton("Clear")
        self._clear_yours_btn.setMaximumWidth(60)
        your_header.addWidget(your_label)
        your_header.addStretch()
        your_header.addWidget(self._clear_yours_btn)
        your_layout.addLayout(your_header)

        self._your_text = QTextEdit()
        self._your_text.setPlaceholderText("Type or paste here... (sent to your peer)")
        self._your_text.setFont(QFont("monospace", 11))
        your_layout.addWidget(self._your_text)

        splitter.addWidget(your_frame)

        # Their text area (bottom)
        their_frame = QFrame()
        their_layout = QVBoxLayout(their_frame)
        their_layout.setContentsMargins(0, 0, 0, 0)

        their_header = QHBoxLayout()
        their_label = QLabel("Their Text")
        their_label.setStyleSheet("font-weight: bold;")
        self._clear_theirs_btn = QPushButton("Clear")
        self._clear_theirs_btn.setMaximumWidth(60)
        self._clear_theirs_btn.setEnabled(False)  # Can't clear their text
        their_header.addWidget(their_label)
        their_header.addStretch()
        their_header.addWidget(self._clear_theirs_btn)
        their_layout.addLayout(their_header)

        self._their_text = QTextEdit()
        self._their_text.setPlaceholderText("Text from your peer will appear here...")
        self._their_text.setReadOnly(True)
        self._their_text.setFont(QFont("monospace", 11))
        their_layout.addWidget(self._their_text)

        splitter.addWidget(their_frame)

        # Equal split
        splitter.setSizes([250, 250])

        layout.addWidget(splitter)

        # Bottom toolbar
        toolbar = QHBoxLayout()

        self._connection_btn = QPushButton("Connect...")
        self._folder_btn = QPushButton("Shared Folder")
        # Create shared folder if it doesn't exist
        self._shared_folder = os.path.expanduser("~/PeerPad")
        os.makedirs(self._shared_folder, exist_ok=True)

        toolbar.addWidget(self._connection_btn)
        toolbar.addWidget(self._folder_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status("Not connected")

    def _setup_menu(self):
        menubar = self.menuBar()

        # Connection menu
        conn_menu = menubar.addMenu("Connection")

        self._host_action = QAction("Host...", self)
        self._connect_action = QAction("Connect...", self)
        self._disconnect_action = QAction("Disconnect", self)
        self._disconnect_action.setEnabled(False)

        conn_menu.addAction(self._host_action)
        conn_menu.addAction(self._connect_action)
        conn_menu.addSeparator()
        conn_menu.addAction(self._disconnect_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        clear_yours = QAction("Clear Your Text", self)
        clear_yours.triggered.connect(self._clear_your_text)
        edit_menu.addAction(clear_yours)

    def _connect_signals(self):
        # Network signals
        self._network.connected.connect(self._on_connected)
        self._network.disconnected.connect(self._on_disconnected)
        self._network.message_received.connect(self._on_message)
        self._network.error.connect(self._on_error)
        self._network.client_connected.connect(self._on_client_connected)

        # UI signals
        self._your_text.textChanged.connect(self._on_text_changed)
        self._clear_yours_btn.clicked.connect(self._clear_your_text)
        self._connection_btn.clicked.connect(self._show_connection_dialog)

        # Menu actions
        self._host_action.triggered.connect(self._show_host_dialog)
        self._connect_action.triggered.connect(self._show_connect_dialog)
        self._disconnect_action.triggered.connect(self._do_disconnect)

        # Folder button
        self._folder_btn.clicked.connect(self._open_shared_folder)

    def _update_status(self, msg: str):
        self._status_bar.showMessage(msg)

    def _show_connection_dialog(self):
        dialog = ConnectionDialog(self)
        if dialog.exec():
            mode, host, port = dialog.get_result()
            if mode == "host":
                self._start_host(port)
            else:
                self._start_connect(host, port)

    def _show_host_dialog(self):
        dialog = ConnectionDialog(self)
        dialog._host_radio.setChecked(True)
        if dialog.exec():
            mode, host, port = dialog.get_result()
            if mode == "host":
                self._start_host(port)

    def _show_connect_dialog(self):
        dialog = ConnectionDialog(self)
        dialog._connect_radio.setChecked(True)
        dialog._on_mode_changed(False)
        if dialog.exec():
            mode, host, port = dialog.get_result()
            if mode == "connect":
                self._start_connect(host, port)

    def _start_host(self, port: int):
        self._is_host = True
        self._network.host(port)
        self._update_status(f"Hosting on port {port}... waiting for connection")
        self._connection_btn.setText("Hosting...")
        self._disconnect_action.setEnabled(True)

    def _start_connect(self, host: str, port: int):
        # Parse host:port if provided together
        if ":" in host:
            parts = host.rsplit(":", 1)
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                pass

        self._is_host = False
        self._network.connect_to(host, port)
        self._update_status(f"Connecting to {host}:{port}...")
        self._connection_btn.setText("Connecting...")

    def _do_disconnect(self):
        self._network.disconnect()

    def _on_connected(self):
        self._is_connected = True
        self._update_status("Connected!")
        self._connection_btn.setText("Connected")
        self._disconnect_action.setEnabled(True)
        self._host_action.setEnabled(False)
        self._connect_action.setEnabled(False)

        # Send current text as full sync
        current = self._your_text.toPlainText()
        if current:
            self._network.send_full_sync(current)

    def _on_client_connected(self, peer: str):
        self._update_status(f"Connected to {peer}")

    def _on_disconnected(self):
        self._is_connected = False
        self._update_status("Disconnected")
        self._connection_btn.setText("Connect...")
        self._disconnect_action.setEnabled(False)
        self._host_action.setEnabled(True)
        self._connect_action.setEnabled(True)

    def _on_message(self, msg: Message):
        self._suppress_text_signal = True
        try:
            if msg.type == MessageType.TEXT:
                # Append text
                cursor = self._their_text.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.insertText(msg.content)
                self._their_text.setTextCursor(cursor)
            elif msg.type == MessageType.FULL_SYNC:
                # Replace all text
                self._their_text.setPlainText(msg.content)
            elif msg.type == MessageType.CLEAR:
                self._their_text.clear()
        finally:
            self._suppress_text_signal = False

    def _on_error(self, error: str):
        self._update_status(f"Error: {error}")
        self._connection_btn.setText("Connect...")

    def _on_text_changed(self):
        if self._suppress_text_signal or not self._is_connected:
            return

        # Get the current text and figure out what changed
        current = self._your_text.toPlainText()

        # For simplicity, send full sync on every change
        # A more sophisticated version would track diffs
        self._network.send_full_sync(current)

    def _clear_your_text(self):
        self._your_text.clear()
        if self._is_connected:
            self._network.send_clear()

    def _open_shared_folder(self):
        # Open in file manager
        subprocess.Popen(["xdg-open", self._shared_folder])

    def closeEvent(self, event):
        self._network.cleanup()
        super().closeEvent(event)
