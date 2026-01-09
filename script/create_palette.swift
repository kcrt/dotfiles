#!/usr/bin/env swift

import AppKit
import Foundation

// MARK: - JSON Models

struct ColorPalette: Codable {
    let name: String
    let version: String
    let description: String
    let baseColor: BaseColor
    let colors: [ColorEntry]
}

struct BaseColor: Codable {
    let hex: String
}

struct ColorEntry: Codable {
    let name: String
    let category: String
    let hex: String
}

// MARK: - Helper Functions

func hexToNSColor(_ hex: String) -> NSColor? {
    var hexSanitized = hex.trimmingCharacters(in: .whitespacesAndNewlines)
    hexSanitized = hexSanitized.replacingOccurrences(of: "#", with: "")

    var rgb: UInt64 = 0
    guard Scanner(string: hexSanitized).scanHexInt64(&rgb) else { return nil }

    let r = CGFloat((rgb & 0xFF0000) >> 16) / 255.0
    let g = CGFloat((rgb & 0x00FF00) >> 8) / 255.0
    let b = CGFloat(rgb & 0x0000FF) / 255.0

    return NSColor(calibratedRed: r, green: g, blue: b, alpha: 1.0)
}

// MARK: - Main

func main() {
    // コマンドライン引数からJSONパスを取得（デフォルト: color_palette.json）
    let args = CommandLine.arguments
    let jsonPath = args.count > 1 ? args[1] : "color_palette.json"
    
    // JSONファイルを読み込み
    let jsonURL = URL(fileURLWithPath: jsonPath)
    
    guard FileManager.default.fileExists(atPath: jsonPath) else {
        print("❌ エラー: JSONファイルが見つかりません: \(jsonPath)")
        exit(1)
    }
    
    do {
        let jsonData = try Data(contentsOf: jsonURL)
        let palette = try JSONDecoder().decode(ColorPalette.self, from: jsonData)
        
        print("📂 読み込み: \(jsonPath)")
        print("   パレット名: \(palette.name)")
        print("   バージョン: \(palette.version)")
        print("   色数: \(palette.colors.count)")
        print("")
        
        // NSColorListを作成
        let colorList = NSColorList(name: palette.name)

        for colorEntry in palette.colors {
            guard let nsColor = hexToNSColor(colorEntry.hex) else {
                print("⚠️  警告: 色 '\(colorEntry.name)' のhex値 '\(colorEntry.hex)' を解析できませんでした")
                continue
            }
            colorList.setColor(nsColor, forKey: colorEntry.name)
        }
        
        // 出力ファイル名を生成（スペースをアンダースコアに）
        let safeName = palette.name
            .replacingOccurrences(of: " ", with: "_")
            .replacingOccurrences(of: "#", with: "")
        let outputPath = "\(safeName).clr"
        
        // 保存
        try colorList.write(to: URL(fileURLWithPath: outputPath))
        
        print("✅ カラーパレットを作成しました!")
        print("   出力: \(outputPath)")
        print("")
        print("📍 インストール方法:")
        print("   mv \(outputPath) ~/Library/Colors/")
        print("")
        print("💡 使い方:")
        print("   任意のアプリで Color Picker を開き、")
        print("   パレットタブから「\(palette.name)」を選択")
        
    } catch let error as DecodingError {
        print("❌ JSONパースエラー: \(error)")
        exit(1)
    } catch {
        print("❌ エラー: \(error.localizedDescription)")
        exit(1)
    }
}

main()
