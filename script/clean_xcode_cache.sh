#!/usr/bin/env bash

xcodebuild clean
xcodebuild -alltargets clean
rm -rf ~/Library/Developer/Xcode/DerivedData/
rm -rf ~/Library/Developer/Xcode/iOS\ DeviceSupport/*/Symbols/System/Library/Caches    
xcrun --kill-cache
