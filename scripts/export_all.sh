#!/usr/bin/env bash
set -euo pipefail

CHECK_ONLY=false
BUILD_DIR="build"

for arg in "$@"; do
  case "$arg" in
    --check)
      CHECK_ONLY=true
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$BUILD_DIR"

need() {
  command -v "$1" >/dev/null 2>&1
}

report_missing() {
  echo "Missing dependency: $1"
}

echo "== ManicWilly export workflow =="
need python3 || { report_missing python3; exit 1; }
need pip || report_missing pip
need pyinstaller || report_missing pyinstaller
need zip || report_missing zip

cat <<EOF_TARGETS
Targets:
- Windows: ${BUILD_DIR}/windows/ManicWilly.zip
- macOS: ${BUILD_DIR}/macos/ManicWilly.app.zip
- Linux: ${BUILD_DIR}/linux/ManicWilly.tar.gz
- Android (via Buildozer): ${BUILD_DIR}/android/*.apk or *.aab
EOF_TARGETS

if [[ "$CHECK_ONLY" == true ]]; then
  echo "Check mode complete."
  exit 0
fi

python3 -m PyInstaller --onefile --name ManicWilly src/manicwilly_game.py

mkdir -p "$BUILD_DIR/linux"
cp dist/ManicWilly "$BUILD_DIR/linux/ManicWilly"
tar -czf "$BUILD_DIR/linux/ManicWilly.tar.gz" -C "$BUILD_DIR/linux" ManicWilly

echo "Desktop binary built at dist/ManicWilly and ${BUILD_DIR}/linux/ManicWilly.tar.gz"
echo "For Windows/macOS builds run the same command on those OS runners (PyInstaller is platform-native)."
echo "For Android packaging use Buildozer in CI with this same codebase."
