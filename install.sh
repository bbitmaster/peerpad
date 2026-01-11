#!/bin/bash
# PeerPad Install Script
# Works on Arch-based (CachyOS, Manjaro, etc.) and Ubuntu/Debian
# Creates a virtualenv and installs all dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
SHARED_FOLDER="$HOME/PeerPad"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}    PeerPad Installer${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

print_step() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect distro family
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/arch-release ]; then
        echo "arch"
    elif [ -f /etc/debian_version ]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

# Check if a command exists
has_cmd() {
    command -v "$1" &> /dev/null
}

# Prompt user before running a command
prompt_and_run() {
    local description="$1"
    shift
    local cmd="$*"

    echo
    print_step "$description"
    echo -e "    Command: ${YELLOW}$cmd${NC}"
    echo
    read -p "    Run this command? [Y/n] " -n 1 -r
    echo

    if [[ -z "$REPLY" || "$REPLY" =~ ^[Yy]$ ]]; then
        eval "$cmd"
        return 0
    else
        print_warn "Skipped."
        return 1
    fi
}

# Install system packages for Arch-based distros
install_arch_packages() {
    local packages=()
    local missing=()

    # Check what's needed
    if ! has_cmd python3; then
        packages+=("python")
    fi

    if ! python3 -c "import PyQt6" 2>/dev/null; then
        packages+=("python-pyqt6")
    fi

    # python-venv is included in python on Arch

    if [ ${#packages[@]} -eq 0 ]; then
        print_step "All required packages already installed"
        return 0
    fi

    prompt_and_run "Install required packages: ${packages[*]}" \
        "sudo pacman -S --needed ${packages[*]}"
}

# Install system packages for Debian/Ubuntu
install_debian_packages() {
    local packages=()
    PYQT6_VIA_PIP=0

    # Check what's needed
    if ! has_cmd python3; then
        packages+=("python3")
    fi

    if ! dpkg -s python3-venv &>/dev/null; then
        packages+=("python3-venv")
    fi

    # We need pip to install PyQt6 on older Ubuntu/Pop!_OS
    if ! dpkg -s python3-pip &>/dev/null; then
        packages+=("python3-pip")
    fi

    # Check if PyQt6 is already installed
    if ! python3 -c "import PyQt6" 2>/dev/null; then
        # Check if python3-pyqt6 is available in apt (not on Ubuntu 22.04/Pop!_OS 22)
        if apt-cache show python3-pyqt6 &>/dev/null; then
            packages+=("python3-pyqt6")
        else
            print_warn "python3-pyqt6 not in apt repos (Ubuntu 22.04/Pop!_OS 22)"
            print_step "PyQt6 will be installed via pip in the virtualenv"
            PYQT6_VIA_PIP=1
        fi
    fi

    if [ ${#packages[@]} -eq 0 ]; then
        print_step "All required system packages already installed"
        return 0
    fi

    echo
    print_step "Need to install: ${packages[*]}"
    echo -e "    Commands:"
    echo -e "    ${YELLOW}sudo apt update${NC}"
    echo -e "    ${YELLOW}sudo apt install ${packages[*]}${NC}"
    echo
    read -p "    Run these commands? [Y/n] " -n 1 -r
    echo

    if [[ -z "$REPLY" || "$REPLY" =~ ^[Yy]$ ]]; then
        sudo apt update
        sudo apt install -y "${packages[@]}"
    else
        print_warn "Skipped package installation."
        print_warn "You may need to install these manually for the app to work."
    fi
}

# Install Syncthing (optional, for file sharing)
install_syncthing() {
    if has_cmd syncthing; then
        print_step "Syncthing already installed"
        return 0
    fi

    echo
    print_step "Syncthing enables automatic file sharing between peers"
    read -p "    Install Syncthing? [y/N] " -n 1 -r
    echo

    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        case "$DISTRO_FAMILY" in
            arch)
                prompt_and_run "Install Syncthing" "sudo pacman -S --needed syncthing"
                ;;
            debian)
                prompt_and_run "Install Syncthing" "sudo apt install -y syncthing"
                ;;
        esac
    fi
}

# Create virtualenv
setup_virtualenv() {
    if [ -d "$VENV_DIR" ]; then
        print_step "Virtualenv already exists at .venv/"
        read -p "    Recreate it? [y/N] " -n 1 -r
        echo
        if [[ "$REPLY" =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
        else
            return 0
        fi
    fi

    print_step "Creating virtualenv with system site-packages access..."
    python3 -m venv "$VENV_DIR" --system-site-packages

    # Activate and install any pip-only dependencies
    source "$VENV_DIR/bin/activate"

    # Check if PyQt6 is accessible
    if python3 -c "import PyQt6" 2>/dev/null; then
        print_step "PyQt6 is accessible in virtualenv"
    else
        print_warn "PyQt6 not found, installing via pip..."
        pip install --upgrade pip
        pip install PyQt6
    fi

    deactivate
    print_step "Virtualenv created at .venv/"
}

# Create shared folder
setup_shared_folder() {
    if [ -d "$SHARED_FOLDER" ]; then
        print_step "Shared folder already exists: $SHARED_FOLDER"
    else
        mkdir -p "$SHARED_FOLDER"
        print_step "Created shared folder: $SHARED_FOLDER"
    fi
}

# Make scripts executable and update run script
setup_scripts() {
    chmod +x "$SCRIPT_DIR/run" 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/install.sh" 2>/dev/null || true

    # Update run script to use venv
    cat > "$SCRIPT_DIR/run" << 'EOF'
#!/bin/bash
# PeerPad launcher - activates venv and runs the app

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtualenv not found. Run ./install.sh first."
    exit 1
fi

# Activate venv and run
source "$VENV_DIR/bin/activate"
cd "$SCRIPT_DIR"
python3 -m peerpad "$@"
EOF
    chmod +x "$SCRIPT_DIR/run"
    print_step "Updated run script to use virtualenv"
}

# Print final instructions
print_success() {
    echo
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}    Installation Complete!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo
    echo "Run PeerPad with:"
    echo -e "  ${YELLOW}./run${NC}                      # Launch with connection dialog"
    echo -e "  ${YELLOW}./run --host${NC}               # Start hosting"
    echo -e "  ${YELLOW}./run --connect <IP>${NC}       # Connect to a peer"
    echo
    echo "Shared folder: $SHARED_FOLDER"
    echo
}

# Main installation flow
main() {
    print_header

    # Detect distro
    DISTRO=$(detect_distro)
    print_step "Detected distro: $DISTRO"

    # Determine distro family
    case "$DISTRO" in
        arch|cachyos|endeavouros|manjaro|garuda|artix)
            DISTRO_FAMILY="arch"
            ;;
        ubuntu|debian|pop|linuxmint|elementary|zorin)
            DISTRO_FAMILY="debian"
            ;;
        *)
            print_error "Unsupported distro: $DISTRO"
            echo "Supported: Arch-based (CachyOS, Manjaro, etc.) or Debian-based (Ubuntu, etc.)"
            echo
            echo "You can try manual installation:"
            echo "  1. Install python3, python3-venv, python3-pyqt6 (or PyQt6 via pip)"
            echo "  2. Run: python3 -m venv .venv --system-site-packages"
            echo "  3. Run: ./run"
            exit 1
            ;;
    esac

    print_step "Distro family: $DISTRO_FAMILY"
    echo

    # Step 1: Install system packages
    echo -e "${BLUE}--- Step 1: System Packages ---${NC}"
    case "$DISTRO_FAMILY" in
        arch)
            install_arch_packages
            ;;
        debian)
            install_debian_packages
            ;;
    esac

    # Step 2: Optional Syncthing
    echo
    echo -e "${BLUE}--- Step 2: Syncthing (Optional) ---${NC}"
    install_syncthing

    # Step 3: Create virtualenv
    echo
    echo -e "${BLUE}--- Step 3: Python Virtualenv ---${NC}"
    setup_virtualenv

    # Step 4: Setup shared folder
    echo
    echo -e "${BLUE}--- Step 4: Shared Folder ---${NC}"
    setup_shared_folder

    # Step 5: Setup scripts
    echo
    echo -e "${BLUE}--- Step 5: Configure Scripts ---${NC}"
    setup_scripts

    # Done
    print_success
}

# Run main
main "$@"
