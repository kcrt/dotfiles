#!/usr/bin/env swift

import Foundation
import iTunesLibrary

/*
 music_library.swift - Search the Music.app library (read-only).

 Uses Apple's iTunesLibrary.framework (ITLibrary), so Music.app does not
 need to be running. The data is what Music.app last saved to disk.
 Nothing in the library is modified.

   music_library.swift 宇多田ヒカル               # free words: title/artist/album/composer
   music_library.swift --artist 宇多田ヒカル --sort plays
   music_library.swift --title "First Love"
   music_library.swift --playlist "お気に入り" --format tsv
   music_library.swift --artist utada --list-artists  # check how an artist is spelled
 */

// MARK: - Options

enum SortKey: String, CaseIterable {
    case `default`  // artist, album, disc, track
    case title
    case artist
    case album
    case year
    case plays
    case added
    case played
}

enum OutputFormat: String, CaseIterable {
    case table
    case tsv
    case json
}

struct Options {
    var words: [String] = []
    var title: String?
    var artist: String?
    var album: String?
    var genre: String?
    var playlist: String?
    var sortKey: SortKey = .default
    var limit: Int?
    var format: OutputFormat = .table
    var includeAllKinds = false
    var listArtists = false
}

// MARK: - Usage

let scriptName = URL(fileURLWithPath: CommandLine.arguments[0]).lastPathComponent

func printUsage() {
    print("""
    Usage: \(scriptName) [words...] [options]

    Search the Music.app library (read-only). All given conditions must match.
    Matching is substring, case / width / diacritic insensitive.

    Arguments:
      words...              each word must appear in title, artist,
                            album artist, album or composer

    Filters:
      -t, --title TEXT      title contains TEXT
      -a, --artist TEXT     artist or album artist contains TEXT
      -A, --album TEXT      album contains TEXT
      -g, --genre TEXT      genre contains TEXT
      -p, --playlist NAME   only tracks in the playlist named exactly NAME
          --all-kinds       include non-music items (videos, podcasts, ...)

    Output:
      -s, --sort KEY        \(SortKey.allCases.map(\.rawValue).joined(separator: " | "))
                            (plays / added / played / year: newest or most first)
      -n, --limit N         show at most N tracks
      -f, --format FORMAT   \(OutputFormat.allCases.map(\.rawValue).joined(separator: " | ")) (default: table)
          --list-artists    list matching artist names with track counts
                            instead of tracks
      -h, --help            show this help

    Examples:
      \(scriptName) 宇多田ヒカル
      \(scriptName) --artist 宇多田ヒカル --sort plays --limit 10
      \(scriptName) --playlist "お気に入り" --format tsv
    """)
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("Error: \(message)\n".utf8))
    exit(1)
}

func parseOptions(_ arguments: [String]) -> Options {
    var options = Options()
    var iterator = arguments.makeIterator()

    func value(for flag: String) -> String {
        guard let value = iterator.next() else { fail("\(flag) needs a value") }
        return value
    }

    while let argument = iterator.next() {
        switch argument {
        case "-h", "--help":
            printUsage()
            exit(0)
        case "-t", "--title": options.title = value(for: argument)
        case "-a", "--artist": options.artist = value(for: argument)
        case "-A", "--album": options.album = value(for: argument)
        case "-g", "--genre": options.genre = value(for: argument)
        case "-p", "--playlist": options.playlist = value(for: argument)
        case "--all-kinds": options.includeAllKinds = true
        case "--list-artists": options.listArtists = true
        case "-s", "--sort":
            let raw = value(for: argument)
            guard let key = SortKey(rawValue: raw) else { fail("unknown sort key: \(raw)") }
            options.sortKey = key
        case "-n", "--limit":
            let raw = value(for: argument)
            guard let limit = Int(raw), limit > 0 else { fail("invalid limit: \(raw)") }
            options.limit = limit
        case "-f", "--format":
            let raw = value(for: argument)
            guard let format = OutputFormat(rawValue: raw) else { fail("unknown format: \(raw)") }
            options.format = format
        default:
            if argument.hasPrefix("-") && argument.count > 1 { fail("unknown option: \(argument)") }
            options.words.append(argument)
        }
    }
    return options
}

// MARK: - Track model

/// Plain value copy of the fields we use from ITLibMediaItem.
struct Track {
    let persistentID: UInt64
    let title: String
    let artist: String
    let albumArtist: String
    let album: String
    let composer: String
    let genre: String
    let year: Int
    let discNumber: Int
    let trackNumber: Int
    let durationSeconds: Int
    let playCount: Int
    let rating: Int  // 0-100 (20 per star)
    let dateAdded: Date?
    let lastPlayedDate: Date?
    let location: URL?

    init(_ item: ITLibMediaItem) {
        persistentID = item.persistentID.uint64Value
        title = item.title
        artist = item.artist?.name ?? ""
        albumArtist = item.album.albumArtist ?? ""
        album = item.album.title ?? ""
        composer = item.composer
        genre = item.genre
        year = item.year
        discNumber = item.album.discNumber
        trackNumber = item.trackNumber
        durationSeconds = item.totalTime / 1000
        playCount = item.playCount
        rating = item.rating
        dateAdded = item.addedDate
        lastPlayedDate = item.lastPlayedDate
        location = item.location
    }

    var searchableFields: [String] { [title, artist, albumArtist, album, composer] }
}

// MARK: - Filtering and sorting

func fuzzyContains(_ haystack: String, _ needle: String) -> Bool {
    haystack.range(of: needle, options: [.caseInsensitive, .diacriticInsensitive, .widthInsensitive]) != nil
}

func matches(_ track: Track, _ options: Options) -> Bool {
    let wordsMatch = options.words.allSatisfy { word in
        track.searchableFields.contains { fuzzyContains($0, word) }
    }
    guard wordsMatch else { return false }

    let fieldFilters: [(String?, [String])] = [
        (options.title, [track.title]),
        (options.artist, [track.artist, track.albumArtist]),
        (options.album, [track.album]),
        (options.genre, [track.genre]),
    ]
    return fieldFilters.allSatisfy { filter, fields in
        guard let filter else { return true }
        return fields.contains { fuzzyContains($0, filter) }
    }
}

func localizedLess(_ lhs: String, _ rhs: String) -> Bool {
    lhs.localizedStandardCompare(rhs) == .orderedAscending
}

/// Albums in order, then disc / track number inside each album.
func albumOrderLess(_ lhs: Track, _ rhs: Track) -> Bool {
    if lhs.album != rhs.album { return localizedLess(lhs.album, rhs.album) }
    if lhs.discNumber != rhs.discNumber { return lhs.discNumber < rhs.discNumber }
    if lhs.trackNumber != rhs.trackNumber { return lhs.trackNumber < rhs.trackNumber }
    return localizedLess(lhs.title, rhs.title)
}

func sorted(_ tracks: [Track], by key: SortKey) -> [Track] {
    let distantPast = Date.distantPast
    return tracks.sorted { lhs, rhs in
        switch key {
        case .default, .artist:
            let lhsArtist = lhs.albumArtist.isEmpty ? lhs.artist : lhs.albumArtist
            let rhsArtist = rhs.albumArtist.isEmpty ? rhs.artist : rhs.albumArtist
            if lhsArtist != rhsArtist { return localizedLess(lhsArtist, rhsArtist) }
            return albumOrderLess(lhs, rhs)
        case .title:
            return localizedLess(lhs.title, rhs.title)
        case .album:
            return albumOrderLess(lhs, rhs)
        case .year:
            if lhs.year != rhs.year { return lhs.year > rhs.year }
            return albumOrderLess(lhs, rhs)
        case .plays:
            if lhs.playCount != rhs.playCount { return lhs.playCount > rhs.playCount }
            return localizedLess(lhs.title, rhs.title)
        case .added:
            return (lhs.dateAdded ?? distantPast) > (rhs.dateAdded ?? distantPast)
        case .played:
            return (lhs.lastPlayedDate ?? distantPast) > (rhs.lastPlayedDate ?? distantPast)
        }
    }
}

// MARK: - Output

let dateFormatter: DateFormatter = {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.dateFormat = "yyyy-MM-dd"
    return formatter
}()

func formatDate(_ date: Date?) -> String {
    date.map(dateFormatter.string(from:)) ?? ""
}

func formatDuration(_ seconds: Int) -> String {
    String(format: "%d:%02d", seconds / 60, seconds % 60)
}

/// Display width in a terminal: East Asian wide / fullwidth characters take 2 columns.
func displayWidth(_ text: String) -> Int {
    text.unicodeScalars.reduce(0) { width, scalar in
        switch scalar.value {
        case 0x0300...0x036F, 0x200B...0x200F, 0xFE00...0xFE0F: return width  // combining / zero width
        case 0x1100...0x115F, 0x2E80...0xA4CF, 0xAC00...0xD7A3, 0xF900...0xFAFF,
             0xFE30...0xFE4F, 0xFF00...0xFF60, 0xFFE0...0xFFE6, 0x1F300...0x1FAFF, 0x20000...0x3FFFD:
            return width + 2
        default: return width + 1
        }
    }
}

/// Truncates to `maxWidth` display columns (adding "…") and pads with spaces.
func fitColumn(_ text: String, _ maxWidth: Int) -> String {
    var result = ""
    var width = 0
    let needsTruncation = displayWidth(text) > maxWidth
    let limit = needsTruncation ? maxWidth - 1 : maxWidth
    for character in text {
        let characterWidth = displayWidth(String(character))
        if width + characterWidth > limit { break }
        result.append(character)
        width += characterWidth
    }
    if needsTruncation {
        result += "…"
        width += 1
    }
    return result + String(repeating: " ", count: max(0, maxWidth - width))
}

func printTable(header: [String], rows: [[String]], maxWidths: [Int]) {
    let widths = header.indices.map { column in
        min(maxWidths[column], ([header] + rows).map { displayWidth($0[column]) }.max() ?? 0)
    }
    func line(_ cells: [String]) -> String {
        cells.indices.map { fitColumn(cells[$0], widths[$0]) }.joined(separator: "  ")
            .trimmingCharacters(in: .whitespaces)
    }
    print(line(header))
    print(widths.map { String(repeating: "-", count: $0) }.joined(separator: "  "))
    rows.forEach { print(line($0)) }
}

func printTSV(header: [String], rows: [[String]]) {
    let clean = { (cell: String) in cell.replacingOccurrences(of: "\t", with: " ").replacingOccurrences(of: "\n", with: " ") }
    ([header] + rows).forEach { print($0.map(clean).joined(separator: "\t")) }
}

func printJSON(_ object: Any) {
    guard let data = try? JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]) else {
        fail("could not encode JSON")
    }
    print(String(decoding: data, as: UTF8.self))
}

func printTracks(_ tracks: [Track], format: OutputFormat) {
    switch format {
    case .table, .tsv:
        let header = ["Title", "Artist", "Album", "Year", "Time", "Plays", "Added"]
        let rows = tracks.map { track in
            [track.title, track.artist, track.album, track.year > 0 ? String(track.year) : "",
             formatDuration(track.durationSeconds), String(track.playCount), formatDate(track.dateAdded)]
        }
        if format == .table {
            printTable(header: header, rows: rows, maxWidths: [40, 24, 32, 4, 6, 5, 10])
        } else {
            printTSV(header: header, rows: rows)
        }
    case .json:
        printJSON(tracks.map { track -> [String: Any] in
            [
                "persistentID": String(format: "%016llX", track.persistentID),
                "title": track.title,
                "artist": track.artist,
                "albumArtist": track.albumArtist,
                "album": track.album,
                "composer": track.composer,
                "genre": track.genre,
                "year": track.year,
                "discNumber": track.discNumber,
                "trackNumber": track.trackNumber,
                "durationSeconds": track.durationSeconds,
                "playCount": track.playCount,
                "rating": track.rating,
                "dateAdded": formatDate(track.dateAdded),
                "lastPlayedDate": formatDate(track.lastPlayedDate),
                "location": track.location?.path ?? "",
            ]
        })
    }
}

func printArtists(_ tracks: [Track], format: OutputFormat) {
    let counts = Dictionary(grouping: tracks, by: \.artist).mapValues(\.count)
    let artists = counts.keys.sorted { counts[$0]! != counts[$1]! ? counts[$0]! > counts[$1]! : localizedLess($0, $1) }
    switch format {
    case .table:
        printTable(header: ["Artist", "Tracks"], rows: artists.map { [$0, String(counts[$0]!)] }, maxWidths: [60, 6])
    case .tsv:
        printTSV(header: ["Artist", "Tracks"], rows: artists.map { [$0, String(counts[$0]!)] })
    case .json:
        printJSON(artists.map { ["artist": $0, "tracks": counts[$0]!] as [String: Any] })
    }
}

// MARK: - Main

let options = parseOptions(Array(CommandLine.arguments.dropFirst()))

let library: ITLibrary
do {
    library = try ITLibrary(apiVersion: "1.1")
} catch {
    fail("could not open the Music library: \(error.localizedDescription)")
}

var items = library.allMediaItems
if let playlistName = options.playlist {
    let playlists = library.allPlaylists.filter { $0.name == playlistName }
    guard !playlists.isEmpty else { fail("playlist not found: \(playlistName)") }
    items = playlists.flatMap(\.items)
}
if !options.includeAllKinds {
    items = items.filter { $0.mediaKind == .kindSong }
}

let matched = items.map(Track.init).filter { matches($0, options) }

if options.listArtists {
    printArtists(matched, format: options.format)
    exit(0)
}

let result = sorted(matched, by: options.sortKey)
let shown = options.limit.map { Array(result.prefix($0)) } ?? result
printTracks(shown, format: options.format)

if options.format == .table {
    fflush(stdout)
    let limitNote = shown.count < result.count ? " (showing \(shown.count))" : ""
    FileHandle.standardError.write(Data("\n\(result.count) tracks\(limitNote)\n".utf8))
}
