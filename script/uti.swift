#!/usr/bin/env swift

import AppKit
import Foundation
import UniformTypeIdentifiers

/*
 uti.swift - Inspect and change macOS file type associations.

 macOS binds "which app opens this file" to a UTI (Uniform Type Identifier),
 not to the MIME type or the raw extension. This script shows all three for a
 given extension / UTI / file, and can change the default application.

   uti.swift md                       # show MIME, UTI and the current default app
   uti.swift net.daringfireball.markdown
   uti.swift ~/notes/todo.md          # existing file: uses its actual UTI
   uti.swift md --list                # every app that claims the type
   uti.swift md --set CotEditor       # set the default app (name, path or bundle id)
 */

// MARK: - Models

/// A UTType together with a description of how the command line argument was interpreted.
struct ResolvedType {
    let type: UTType
    let source: String
}

enum Mode {
    case info
    case list
    /// `nil` means "ask the user with an open panel".
    case set(String?)
}

// MARK: - Usage

let scriptName = URL(fileURLWithPath: CommandLine.arguments[0]).lastPathComponent

func printUsage() {
    print("""
    Usage: \(scriptName) <extension | UTI | file> [--list] [--set [app]]

    Target (auto-detected in this order):
      <file>        an existing file    -> its actual UTI (as Finder sees it)
      <UTI>         e.g. public.json, net.daringfireball.markdown
      <extension>   e.g. md, .md, json

    Options:
      -l, --list          list every application that can open the type
      -s, --set [app]     set the default application; [app] may be
                          an app name (CotEditor), a path
                          (/Applications/CotEditor.app) or a bundle
                          identifier (com.coteditor.CotEditor).
                          Omit it to pick the app from a file dialog.
      -h, --help          show this help

    Examples:
      \(scriptName) md
      \(scriptName) md --set CotEditor
      \(scriptName) md --set                  # choose in a dialog
      \(scriptName) .csv --list
      \(scriptName) public.json --set "Visual Studio Code"

    Note: .Rmd / .qmd and similar are distinct UTIs, so changing .md does not
    affect them. Run \(scriptName) on each extension to check.
    """)
}

// MARK: - Target resolution

/// Interprets a command line argument as a file, a UTI or a filename extension.
func resolveType(_ argument: String) -> ResolvedType? {
    let fileURL = URL(fileURLWithPath: (argument as NSString).expandingTildeInPath)
    if FileManager.default.fileExists(atPath: fileURL.path),
       let type = try? fileURL.resourceValues(forKeys: [.contentTypeKey]).contentType {
        return ResolvedType(type: type, source: "file \(fileURL.path)")
    }

    if argument.contains("."), let type = UTType(argument), type.isDeclared {
        return ResolvedType(type: type, source: "UTI \(argument)")
    }

    let ext = argument.hasPrefix(".") ? String(argument.dropFirst()) : argument
    if let type = UTType(filenameExtension: ext) {
        return ResolvedType(type: type, source: "extension .\(ext)")
    }
    // Unregistered extension: LaunchServices still uses a synthesised ("dynamic") UTI.
    if let type = UTType(tag: ext, tagClass: .filenameExtension, conformingTo: nil) {
        return ResolvedType(type: type, source: "extension .\(ext)")
    }
    return nil
}

/// Finds an application bundle from a name, a path or a bundle identifier.
func resolveApp(_ argument: String) -> URL? {
    let expanded = (argument as NSString).expandingTildeInPath

    if argument.contains("/") {
        let url = URL(fileURLWithPath: expanded)
        return FileManager.default.fileExists(atPath: url.path) ? url : nil
    }

    let bundleName = argument.hasSuffix(".app") ? argument : argument + ".app"
    let searchPaths = [
        "/Applications",
        "/Applications/Utilities",
        "/System/Applications",
        "/System/Applications/Utilities",
        NSHomeDirectory() + "/Applications",
    ]
    for directory in searchPaths {
        let url = URL(fileURLWithPath: directory).appendingPathComponent(bundleName)
        if FileManager.default.fileExists(atPath: url.path) { return url }
    }

    if let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: argument) {
        return url
    }

    return spotlightSearchApp(named: bundleName)
}

/// Asks the user to pick an application bundle with a standard open panel.
/// Returns nil if the user cancels, or if there is no GUI session to show it in.
func chooseAppInteractively(for resolved: ResolvedType) -> URL? {
    guard CGSessionCopyCurrentDictionary() != nil else {
        FileHandle.standardError.write(Data("""
        No GUI session available, so the file dialog cannot be shown.
        Pass the application explicitly, e.g. --set CotEditor
        """.appending("\n").utf8))
        return nil
    }

    let application = NSApplication.shared
    application.setActivationPolicy(.accessory)  // no Dock icon, but the panel can take focus

    let panel = NSOpenPanel()
    panel.message = "Choose the application to open \(resolved.source) (\(resolved.type.identifier))"
    panel.prompt = "Set as Default"
    panel.directoryURL = URL(fileURLWithPath: "/Applications")
    panel.allowedContentTypes = [.application]
    panel.allowsMultipleSelection = false
    panel.canChooseDirectories = false
    panel.treatsFilePackagesAsDirectories = false

    application.activate(ignoringOtherApps: true)
    return panel.runModal() == .OK ? panel.url : nil
}

/// Last resort lookup for apps outside the standard directories.
func spotlightSearchApp(named bundleName: String) -> URL? {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/mdfind")
    process.arguments = ["-name", bundleName,
                         "kMDItemContentType == 'com.apple.application-bundle'"]
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = FileHandle.nullDevice
    guard (try? process.run()) != nil else { return nil }
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()

    let paths = String(decoding: data, as: UTF8.self)
        .split(separator: "\n")
        .map(String.init)
        .filter { $0.hasSuffix(bundleName) }
    return paths.first.map { URL(fileURLWithPath: $0) }
}

// MARK: - Output

func displayName(_ appURL: URL) -> String {
    var name = FileManager.default.displayName(atPath: appURL.path)
    if name.hasSuffix(".app") { name.removeLast(4) }  // shown when "show all extensions" is on
    return "\(name)  (\(appURL.path))"
}

func printInfo(_ resolved: ResolvedType) {
    let type = resolved.type
    let extensions = type.tags[.filenameExtension] ?? []
    let mimeTypes = type.tags[.mimeType] ?? []
    let handlers = NSWorkspace.shared.urlsForApplications(toOpen: type)

    print("Input        : \(resolved.source)")
    print("UTI          : \(type.identifier)")
    print("MIME         : \(mimeTypes.isEmpty ? "(none declared)" : mimeTypes.joined(separator: ", "))")
    print("Extensions   : \(extensions.isEmpty ? "(none)" : extensions.map { ".\($0)" }.joined(separator: ", "))")
    print("Description  : \(type.localizedDescription ?? "(none)")")
    print("Conforms to  : \(type.supertypes.map(\.identifier).sorted().joined(separator: ", "))")
    if type.isDynamic {
        print("Status       : dynamic (no app declares this UTI; matched by extension only)")
    }
    if let current = NSWorkspace.shared.urlForApplication(toOpen: type) {
        print("Default app  : \(displayName(current))")
    } else {
        print("Default app  : (none)")
    }
    print("Other apps   : \(max(handlers.count - 1, 0)) more (--list to show)")
}

func printHandlerList(_ resolved: ResolvedType) {
    let handlers = NSWorkspace.shared.urlsForApplications(toOpen: resolved.type)
    guard !handlers.isEmpty else {
        print("No application can open \(resolved.type.identifier).")
        return
    }
    print("Applications that can open \(resolved.type.identifier), best match first:")
    for (index, appURL) in handlers.enumerated() {
        let marker = index == 0 ? "*" : " "
        print(" \(marker) \(displayName(appURL))")
    }
    print("\n(* = current default)")
}

// MARK: - Mutation

/// Sets the default application, then reports the result. Returns false on failure.
func setDefaultApp(_ appURL: URL, for resolved: ResolvedType) -> Bool {
    let type = resolved.type
    let previous = NSWorkspace.shared.urlForApplication(toOpen: type)

    var failure: Error?
    let semaphore = DispatchSemaphore(value: 0)
    Task {
        do {
            try await NSWorkspace.shared.setDefaultApplication(at: appURL, toOpen: type)
        } catch {
            failure = error
        }
        semaphore.signal()
    }
    semaphore.wait()

    if let failure {
        FileHandle.standardError.write(Data("Failed to set default app: \(failure.localizedDescription)\n".utf8))
        return false
    }

    print("\(type.identifier)")
    print("  before: \(previous.map(displayName) ?? "(none)")")
    print("  after : \(NSWorkspace.shared.urlForApplication(toOpen: type).map(displayName) ?? "(none)")")
    if type.isDynamic {
        print("  note  : this UTI is dynamic, so the association may not survive a reboot.")
    }
    return true
}

// MARK: - Argument parsing

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("\(message)\n".utf8))
    exit(1)
}

var arguments = Array(CommandLine.arguments.dropFirst())

if arguments.isEmpty || arguments.contains("-h") || arguments.contains("--help") {
    printUsage()
    exit(arguments.isEmpty ? 1 : 0)
}

var mode = Mode.info
var target: String?

while let argument = arguments.first {
    arguments.removeFirst()
    switch argument {
    case "-l", "--list":
        mode = .list
    case "-s", "--set":
        // A value is optional: without one, the app is chosen in a dialog.
        if let app = arguments.first, !app.hasPrefix("-") {
            arguments.removeFirst()
            mode = .set(app)
        } else {
            mode = .set(nil)
        }
    default:
        guard target == nil else { fail("Unexpected extra argument: \(argument)") }
        target = argument
    }
}

guard let target else { fail("No extension, UTI or file specified.") }
guard let resolved = resolveType(target) else {
    fail("Could not determine a type for '\(target)'.")
}

// MARK: - Dispatch

switch mode {
case .info:
    printInfo(resolved)
case .list:
    printHandlerList(resolved)
case .set(let appArgument):
    let appURL: URL
    if let appArgument {
        guard let found = resolveApp(appArgument) else {
            fail("Could not find application '\(appArgument)'. Try a full path to the .app bundle.")
        }
        appURL = found
    } else {
        printInfo(resolved)
        print("")
        guard let chosen = chooseAppInteractively(for: resolved) else {
            fail("Cancelled: the default application is unchanged.")
        }
        appURL = chosen
    }
    guard appURL.pathExtension == "app" else {
        fail("'\(appURL.path)' is not an application bundle.")
    }
    exit(setDefaultApp(appURL, for: resolved) ? 0 : 1)
}
