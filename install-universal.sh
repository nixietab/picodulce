#!/bin/bash

set -e

PICODULCE_DIR="$HOME/.picodulce"
GIT_URL="https://github.com/nixietab/picodulce.git"
DESKTOP_FILE="$HOME/.local/share/applications/picodulce.desktop"
BIN_FILE="/usr/bin/picodulce"

# --- Helper functions ---
msg() {
    echo -e "\033[1;32m$1\033[0m"
}

err() {
    echo -e "\033[1;31m$1\033[0m" >&2
    exit 1
}

pause() {
    read -rp "Press Enter to continue..."
}

# --- Check dependencies ---
msg "Checking Python3..."
if ! command -v python3 >/dev/null; then
    err "Python3 is not installed. Please install it first."
fi

msg "Checking venv module..."
if ! python3 -m venv --help >/dev/null 2>&1; then
    err "python3-venv is not available. Please install it."
fi

# --- Clone repo ---
msg "Cloning Picodulce repo..."
rm -rf "$PICODULCE_DIR"
git clone "$GIT_URL" "$PICODULCE_DIR"

# --- Create virtual environment ---
cd "$PICODULCE_DIR"
msg "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# --- Create run.sh ---
msg "Creating run.sh..."
cat > "$PICODULCE_DIR/run.sh" <<'EOF'
#!/bin/bash

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "venv folder does not exist. Creating virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  echo "Installing required packages..."
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

exec python picodulce.py
EOF

chmod +x "$PICODULCE_DIR/run.sh"

# --- Create .desktop entry ---
msg "Creating .desktop entry..."
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Picodulce
Exec=$PICODULCE_DIR/run.sh
Icon=$PICODULCE_DIR/launcher_icon.ico
Terminal=true
Type=Application
Comment=Picodulce Launcher
Categories=Game;
EOF

# --- Ask if install in /usr/bin ---
echo
read -rp "Do you want to install the "picodulce" command? it requires sudo. (y/n) " choice
if [[ "$choice" =~ ^[Yy]$ ]]; then
    if [ "$(id -u)" -ne 0 ]; then
        echo "Root permissions required to install into /usr/bin"
        sudo bash -c "cat > $BIN_FILE" <<EOF
#!/bin/bash
cd $PICODULCE_DIR
exec ./run.sh
EOF
        sudo chmod +x "$BIN_FILE"
    else
        cat > "$BIN_FILE" <<EOF
#!/bin/bash
cd $PICODULCE_DIR
exec ./run.sh
EOF
        chmod +x "$BIN_FILE"
    fi
    msg "Installed 'picodulce' command in /usr/bin"
fi

msg "Installation complete!"
echo "You can run Picodulce with:"
echo "  $PICODULCE_DIR/run.sh"
echo "Or from your applications menu."
