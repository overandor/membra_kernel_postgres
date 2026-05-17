#!/bin/bash
# Build script for Membra Folder Link macOS app
# This script helps set up the Xcode project structure

set -e

PROJECT_NAME="MembraFolderLink"
APP_NAME="${PROJECT_NAME}App"
EXT_NAME="${PROJECT_NAME}Extension"
BUILD_DIR="build"

echo "🔨 Building Membra Folder Link..."

# Check for Xcode
if ! command -v xcodebuild &> /dev/null; then
    echo "❌ Xcode command-line tools not found"
    echo "Install with: xcode-select --install"
    exit 1
fi

# Create build directory
mkdir -p "$BUILD_DIR"

echo "📦 This project requires Xcode to build properly."
echo ""
echo "To build manually:"
echo "1. Open Xcode"
echo "2. File → New → Project → macOS → App"
echo "3. Product Name: $PROJECT_NAME"
echo "4. Add Finder Sync Extension target"
echo "5. Copy the provided Swift and Info.plist files"
echo "6. Build and run (Cmd+R)"
echo ""
echo "See README.md for detailed instructions."
echo ""
echo "Source files are ready in:"
echo "  - $APP_NAME/AppDelegate.swift"
echo "  - $EXT_NAME/FinderSync.swift"
echo "  - Info.plist files"
