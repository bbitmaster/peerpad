"""Entry point for PeerPad application."""

import argparse
import sys

from PyQt6.QtWidgets import QApplication

from .app import PeerPadWindow


def main():
    parser = argparse.ArgumentParser(
        description="PeerPad - Real-time text and file sharing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  peerpad                      # Launch GUI with connection dialog
  peerpad --host               # Start hosting on default port (9876)
  peerpad --host -p 8888       # Start hosting on port 8888
  peerpad --connect 10.0.0.5   # Connect to peer at 10.0.0.5
  peerpad --connect 10.0.0.5:8888  # Connect with custom port
"""
    )

    parser.add_argument(
        "--host", "-H",
        action="store_true",
        help="Start in host mode (wait for connections)"
    )

    parser.add_argument(
        "--connect", "-c",
        metavar="ADDRESS",
        help="Connect to a host (IP or IP:port)"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=9876,
        help="Port to use (default: 9876)"
    )

    args = parser.parse_args()

    # Validate args
    if args.host and args.connect:
        parser.error("Cannot use both --host and --connect")

    # Parse port from connect address if provided
    connect_to = args.connect
    port = args.port

    if connect_to and ":" in connect_to:
        parts = connect_to.rsplit(":", 1)
        connect_to = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            pass

    # Start Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("PeerPad")

    window = PeerPadWindow(
        host_mode=args.host,
        connect_to=connect_to,
        port=port
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
