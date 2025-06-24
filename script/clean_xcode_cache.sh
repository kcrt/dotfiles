#!/usr/bin/env bash

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $(basename "$0")"
    echo "Cleans Xcode build caches and derived data."
    echo "This includes:"
    echo "  - Running 'xcodebuild clean' and 'xcodebuild -alltargets clean'"
    echo "  - Removing ~/Library/Developer/Xcode/DerivedData/"
    echo "  - Removing ~/Library/Developer/Xcode/iOS DeviceSupport/*/Symbols/System/Library/Caches"
    echo "  - Running 'xcrun --kill-cache'"
    exit 0
fi

xcodebuild clean
xcodebuild -alltargets clean
rm -rf ~/Library/Developer/Xcode/DerivedData/
rm -rf ~/Library/Developer/Xcode/iOS\ DeviceSupport/*/Symbols/System/Library/Caches    
xcrun --kill-cache
