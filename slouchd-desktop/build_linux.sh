#!/usr/bin/env bash
# local and ci build script for slouchd-desktop linux targets (.AppImage & .deb)
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. determine version
VERSION="$1"
if [ -z "$VERSION" ]; then
    INIT_PY="$SCRIPT_DIR/src/__init__.py"
    if [ -f "$INIT_PY" ]; then
        VERSION=$(grep -E '^__version__\s*=' "$INIT_PY" | sed -E 's/__version__\s*=\s*["'"'"']([^"'"'"']+)["'"'"']/\1/')
    fi
fi
if [ -z "$VERSION" ]; then
    VERSION="0.2.3"
fi
CLEAN_VERSION="${VERSION#v}"

echo "=========================================="
echo "   building slouchd linux packages        "
echo "   version: $CLEAN_VERSION                "
echo "=========================================="

# 2. locate python
PYTHON=""
for candidate in "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/venv/bin/python" "$(which python3 2>/dev/null)" "$(which python 2>/dev/null)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "error: python not found" >&2
    exit 1
fi

echo "[1/4] using python: $PYTHON"

# 3. sync version
SYNC_SCRIPT="$SCRIPT_DIR/sync_version.py"
if [ -f "$SYNC_SCRIPT" ]; then
    "$PYTHON" "$SYNC_SCRIPT" "$CLEAN_VERSION"
fi

# 4. run pyinstaller
echo "[2/4] freezing app with pyinstaller..."
"$PYTHON" -m PyInstaller --noconfirm --clean slouchd.spec

if [ ! -f "dist/slouchd/slouchd" ]; then
    echo "error: pyinstaller binary dist/slouchd/slouchd not found!" >&2
    exit 1
fi
echo "pyinstaller build succeeded -> dist/slouchd"

mkdir -p dist/installer

# 5. package deb
echo "[3/4] building debian package (.deb)..."
DEB_STAGING="$SCRIPT_DIR/build/deb_staging"
rm -rf "$DEB_STAGING"
mkdir -p "$DEB_STAGING/DEBIAN"
mkdir -p "$DEB_STAGING/opt/slouchd"
mkdir -p "$DEB_STAGING/usr/bin"
mkdir -p "$DEB_STAGING/usr/share/applications"
mkdir -p "$DEB_STAGING/usr/share/icons/hicolor/512x512/apps"

cp -r dist/slouchd/* "$DEB_STAGING/opt/slouchd/"
ln -s /opt/slouchd/slouchd "$DEB_STAGING/usr/bin/slouchd"
cp installer/linux/slouchd.desktop "$DEB_STAGING/usr/share/applications/"
cp assets/icon.png "$DEB_STAGING/usr/share/icons/hicolor/512x512/apps/slouchd.png"

INSTALLED_SIZE=$(du -sk --exclude=DEBIAN "$DEB_STAGING" | awk '{print $1}')

cat << EOF > "$DEB_STAGING/DEBIAN/control"
Package: slouchd
Version: $CLEAN_VERSION
Section: utils
Priority: optional
Architecture: amd64
Installed-Size: $INSTALLED_SIZE
Maintainer: Javad Jam <slouchd@users.noreply.github.com>
Depends: libc6, libgl1, libegl1, libdbus-1-3, libxcb-cursor0
Description: gentle multi-screen posture and slouch monitor
 slouchd sits quietly in your system tray and monitors your posture
 in the background using a BLE collar tag or webcam, dimming your
 screens when you slouch.
EOF

DEB_OUTPUT="dist/installer/slouchd_${CLEAN_VERSION}_amd64.deb"
dpkg-deb --root-owner-group --build "$DEB_STAGING" "$DEB_OUTPUT"
rm -rf "$DEB_STAGING"
echo "debian package created -> $DEB_OUTPUT"

# 6. package appimage
echo "[4/4] building AppImage..."
APPDIR="$SCRIPT_DIR/build/appimage_staging"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/512x512/apps"

cp -r dist/slouchd/* "$APPDIR/usr/bin/"
cp installer/linux/slouchd.desktop "$APPDIR/slouchd.desktop"
cp installer/linux/slouchd.desktop "$APPDIR/usr/share/applications/slouchd.desktop"
cp assets/icon.png "$APPDIR/slouchd.png"
cp assets/icon.png "$APPDIR/usr/share/icons/hicolor/512x512/apps/slouchd.png"

cat << 'EOF' > "$APPDIR/AppRun"
#!/bin/bash
set -e
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/bin:${HERE}/usr/bin/_internal:${HERE}/usr/lib:${LD_LIBRARY_PATH}"
if [ -z "$QT_QPA_PLATFORM" ]; then
    export QT_QPA_PLATFORM="xcb;wayland"
fi
exec "${HERE}/usr/bin/slouchd" "$@"
EOF
chmod +x "$APPDIR/AppRun"

APPIMAGETOOL=""
if command -v appimagetool >/dev/null 2>&1; then
    APPIMAGETOOL="appimagetool"
elif [ -x "/tmp/appimagetool" ]; then
    APPIMAGETOOL="/tmp/appimagetool"
else
    echo "downloading appimagetool..."
    curl -fsSL https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -o /tmp/appimagetool
    chmod +x /tmp/appimagetool
    APPIMAGETOOL="/tmp/appimagetool"
fi

APPIMAGE_OUTPUT="dist/installer/slouchd-${CLEAN_VERSION}-x86_64.AppImage"
rm -f "$APPIMAGE_OUTPUT"
ARCH=x86_64 "$APPIMAGETOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$APPIMAGE_OUTPUT"
rm -rf "$APPDIR"
echo "AppImage created -> $APPIMAGE_OUTPUT"

echo ""
echo "=========================================="
echo "linux build complete! artifacts in dist/installer/:"
ls -lh dist/installer/*.deb dist/installer/*.AppImage 2>/dev/null || true
echo "=========================================="
