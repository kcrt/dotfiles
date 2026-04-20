#!/usr/bin/env swift

// Screen QR Code Reader
// Captures the screen using ScreenCaptureKit and decodes any QR codes found.
// Requires "Screen Recording" permission in System Settings > Privacy & Security.

import CoreImage
import Foundation
import ScreenCaptureKit

func detectQRCodes(in cgImage: CGImage) -> [String] {
    let ciImage = CIImage(cgImage: cgImage)
    guard let detector = CIDetector(
        ofType: CIDetectorTypeQRCode,
        context: nil,
        options: [CIDetectorAccuracy: CIDetectorAccuracyHigh]
    ) else {
        return []
    }
    let features = detector.features(in: ciImage)
    return features.compactMap { ($0 as? CIQRCodeFeature)?.messageString }
}

let semaphore = DispatchSemaphore(value: 0)

Task {
    do {
        let content = try await SCShareableContent.current
        guard let display = content.displays.first else {
            fputs("Error: No display found.\n", stderr)
            exit(1)
        }

        let filter = SCContentFilter(display: display, excludingWindows: [])
        let config = SCStreamConfiguration()
        config.width = display.width
        config.height = display.height
        config.pixelFormat = kCVPixelFormatType_32BGRA

        let image = try await SCScreenshotManager.captureImage(
            contentFilter: filter,
            configuration: config
        )

        let results = detectQRCodes(in: image)

        if results.isEmpty {
            print("No QR codes found on screen.")
        } else {
            for (i, result) in results.enumerated() {
                if results.count > 1 {
                    print("[\(i + 1)] \(result)")
                } else {
                    print(result)
                }
            }
        }
    } catch {
        fputs("Error: \(error.localizedDescription)\n", stderr)
        fputs("Check Screen Recording permission in System Settings.\n", stderr)
        exit(1)
    }
    semaphore.signal()
}

semaphore.wait()
