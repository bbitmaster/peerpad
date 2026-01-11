"""GUI widgets for PeerPad."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QSpinBox,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from .network import get_local_ips


class ConnectionDialog(QDialog):
    """Dialog for choosing host or connect mode."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PeerPad - Connect")
        self.setMinimumWidth(400)

        self._mode = "host"  # or "connect"
        self._host = ""
        self._port = 9876

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Mode selection
        mode_group = QGroupBox("Connection Mode")
        mode_layout = QVBoxLayout(mode_group)

        self._mode_group = QButtonGroup(self)

        self._host_radio = QRadioButton("Host (wait for connection)")
        self._connect_radio = QRadioButton("Connect (to a host)")
        self._host_radio.setChecked(True)

        self._mode_group.addButton(self._host_radio)
        self._mode_group.addButton(self._connect_radio)

        mode_layout.addWidget(self._host_radio)
        mode_layout.addWidget(self._connect_radio)

        layout.addWidget(mode_group)

        # Host info (shown when hosting)
        self._host_info = QGroupBox("Your IPs (share one with your friend)")
        host_info_layout = QVBoxLayout(self._host_info)

        ips = get_local_ips()
        if ips:
            for ip in ips:
                ip_label = QLabel(f"  {ip}")
                ip_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                host_info_layout.addWidget(ip_label)
        else:
            host_info_layout.addWidget(QLabel("  (Could not detect IPs)"))

        layout.addWidget(self._host_info)

        # Connect settings (shown when connecting)
        self._connect_group = QGroupBox("Connect to")
        connect_layout = QVBoxLayout(self._connect_group)

        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("Host:"))
        self._host_input = QLineEdit()
        self._host_input.setPlaceholderText("e.g., 100.64.0.1 or 192.168.1.5")
        host_layout.addWidget(self._host_input)
        connect_layout.addLayout(host_layout)

        self._connect_group.setVisible(False)
        layout.addWidget(self._connect_group)

        # Port (shared)
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self._port_input = QSpinBox()
        self._port_input.setRange(1024, 65535)
        self._port_input.setValue(9876)
        port_layout.addWidget(self._port_input)
        port_layout.addStretch()
        layout.addLayout(port_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self._ok_btn = QPushButton("Host")
        self._cancel_btn = QPushButton("Cancel")
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._ok_btn)
        layout.addLayout(btn_layout)

        # Connections
        self._host_radio.toggled.connect(self._on_mode_changed)
        self._ok_btn.clicked.connect(self._on_ok)
        self._cancel_btn.clicked.connect(self.reject)

    def _on_mode_changed(self, checked: bool):
        if checked:  # Host mode
            self._mode = "host"
            self._host_info.setVisible(True)
            self._connect_group.setVisible(False)
            self._ok_btn.setText("Host")
        else:  # Connect mode
            self._mode = "connect"
            self._host_info.setVisible(False)
            self._connect_group.setVisible(True)
            self._ok_btn.setText("Connect")

    def _on_ok(self):
        self._port = self._port_input.value()

        if self._mode == "connect":
            self._host = self._host_input.text().strip()
            if not self._host:
                QMessageBox.warning(self, "Error", "Please enter a host address")
                return

        self.accept()

    def get_result(self) -> tuple[str, str, int]:
        """Returns (mode, host, port)."""
        return self._mode, self._host, self._port
