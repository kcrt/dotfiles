#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "tqdm>=4.66.0",
#   "opentimestamps-client>=0.7.0",
# ]
# ///
"""
i_have - File Existence Proof System
Provides cryptographic proof that files existed at a specific point in time
using HMAC, OpenTimestamps, and GitHub.
"""

import argparse
import hashlib
import hmac
import json
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tqdm import tqdm

# Version
VERSION = "0.1.0"

# System directories
I_HAVE_DIR = Path.home() / "i_have"
DB_PATH = I_HAVE_DIR / "i_have.db"
IGNORE_LIST_PATH = I_HAVE_DIR / "ignore_list"

# Global verbose flag
VERBOSE = False

# Default exclusion patterns
DEFAULT_EXCLUDES = [
    # System directories
    "/proc", "/sys", "/dev", "/run", "/tmp", "/var/tmp", "/var/cache", "/var/log",
    # macOS specific
    "/System", "/Library", "/private/var", "/.Spotlight-V100", "/.fseventsd", "/.Trashes",
    "~/Library/CloudStorage/",

    # Version control
    "**/.git", "**/.svn", "**/.hg",

    # Package managers and dependencies (reproducible from public sources)
    "**/node_modules",           # Node.js
    "**/.npm", "**/.yarn", "**/.pnpm-store",  # npm/yarn/pnpm caches
    "**/.deno", "**/.bun",       # Deno/Bun caches
    "**/go/pkg", "**/pkg/mod",   # Go modules
    "**/.cargo", "**/target",    # Rust (cargo cache and build artifacts)
    "**/__pycache__", "**/.venv", "**/venv",  # Python
    "**/.pytest_cache", "**/.mypy_cache", "**/.ruff_cache", "**/.tox", "**/pip-cache",
    "**/*.egg-info",             # Python package metadata
    "~/.local/pipx",             # pipx (Python app installer)
    "~/.asdf",                   # asdf version manager
    "~/.claude",                 # Claude Code/API configuration
    "~/.zplug",                  # zplug (Zsh plugin manager)
    "**/vendor/bundle", "**/.bundle", "**/.gem",  # Ruby
    "~/.cpan", "~/.cpanm",       # Perl (CPAN/cpanminus)
    "**/.m2/repository", "**/.gradle",  # Java/Maven/Gradle
    "**/packages", "**/bin", "**/obj",  # .NET
    "**/.platformio", "**/.pio",  # PlatformIO (embedded development)
    "**/.build",                 # Swift Package Manager

    # Build artifacts and caches
    "**/build", "**/dist", "**/out", "**/.cache",
    "**/.next",                  # Next.js
    "**/.nuxt",                  # Nuxt.js
    "**/.astro",                 # Astro
    "**/.expo", "**/.expo-shared",  # Expo/React Native
    "**/.parcel-cache",          # Parcel bundler
    "**/.turbo",                 # Turborepo
    "**/.terraform", "**/.terragrunt-cache",  # Infrastructure as Code

    # IDE and editor
    "**/.vscode", "**/.vscode-server", "**/.idea", "**/.eclipse",
    "**/.vim/bundle",
    ".DS_Store", "**/Thumbs.db",  # OS-generated files

    # Temporary files
    "**/*.tmp", "**/*.temp", "**/*.swp", "**/*~",

    # Self directory
    str(I_HAVE_DIR),
]

# OpenTimestamps settings
OTS_UPGRADE_MAX_ATTEMPTS = 72  # 6 hours with 5-minute intervals
OTS_UPGRADE_INTERVAL = 300  # 5 minutes


class Database:
    """Handles all database operations for file timestamps."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_timestamps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_seen TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    mtime TEXT NOT NULL,
                    hash_algorithm TEXT DEFAULT 'sha3-256',
                    file_hash TEXT NOT NULL,
                    hmac_secret TEXT NOT NULL,
                    hmac TEXT NOT NULL,
                    upload_date TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON file_timestamps(file_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON file_timestamps(file_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_upload_date ON file_timestamps(upload_date)")
            conn.commit()
        finally:
            conn.close()

    def get_file_record(self, file_path: str) -> Optional[dict]:
        """Get the most recent record for a file path."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT file_size, mtime, file_hash FROM file_timestamps "
                "WHERE file_path = ? ORDER BY first_seen DESC LIMIT 1",
                (file_path,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "file_size": row[0],
                    "mtime": row[1],
                    "file_hash": row[2]
                }
            return None
        finally:
            conn.close()

    def insert_record(self, record: dict) -> None:
        """Insert a new file timestamp record."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO file_timestamps
                (first_seen, file_path, file_size, mtime, hash_algorithm,
                 file_hash, hmac_secret, hmac, upload_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["first_seen"],
                record["file_path"],
                record["file_size"],
                record["mtime"],
                record["hash_algorithm"],
                record["file_hash"],
                record["hmac_secret"],
                record["hmac"],
                record["upload_date"]
            ))
            conn.commit()
        finally:
            conn.close()

    def get_verification_info(self, file_hash: str) -> Optional[dict]:
        """Get verification information for a file hash."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT first_seen, hmac_secret, hmac, upload_date "
                "FROM file_timestamps WHERE file_hash = ? "
                "ORDER BY first_seen ASC LIMIT 1",
                (file_hash,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "first_seen": row[0],
                    "hmac_secret": row[1],
                    "hmac": row[2],
                    "upload_date": row[3]
                }
            return None
        finally:
            conn.close()


class ExclusionRules:
    """Manages file and directory exclusion patterns."""

    def __init__(self, ignore_list_path: Path):
        self.patterns: list[str] = []
        self._load_patterns(ignore_list_path)

    def _load_patterns(self, ignore_list_path: Path) -> None:
        """Load exclusion patterns from default and user-defined lists."""
        # Add default patterns
        self.patterns.extend(DEFAULT_EXCLUDES)

        # Load user-defined patterns if exists
        if ignore_list_path.exists():
            with open(ignore_list_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#'):
                        self.patterns.append(line)

    def should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded based on patterns."""
        path_str = str(path)
        path_str_expanded = str(path.expanduser())

        for pattern in self.patterns:
            # Handle absolute paths
            if pattern.startswith('/'):
                if path_str.startswith(pattern) or path_str_expanded.startswith(pattern):
                    if VERBOSE:
                        print(f"  [VERBOSE] Excluded (absolute): {path} (pattern: {pattern})", file=sys.stderr)
                    return True

            # Handle home directory relative paths
            elif pattern.startswith('~/'):
                expanded_pattern = str(Path(pattern).expanduser())
                if path_str.startswith(expanded_pattern) or path_str_expanded.startswith(expanded_pattern):
                    if VERBOSE:
                        print(f"  [VERBOSE] Excluded (home-relative): {path} (pattern: {pattern})", file=sys.stderr)
                    return True

            # Handle glob patterns
            elif '**' in pattern or '*' in pattern:
                # Try matching from root
                if path.match(pattern):
                    if VERBOSE:
                        print(f"  [VERBOSE] Excluded (glob): {path} (pattern: {pattern})", file=sys.stderr)
                    return True
                # Try matching any parent
                try:
                    # For patterns like **/*.tmp, check if any part matches
                    parts = pattern.split('/')
                    if parts[0] == '**':
                        # Match against tail of path
                        remaining = '/'.join(parts[1:])
                        if remaining and path.match(remaining):
                            if VERBOSE:
                                print(f"  [VERBOSE] Excluded (glob tail): {path} (pattern: {pattern})", file=sys.stderr)
                            return True
                except ValueError:
                    pass

            # Handle simple name patterns
            else:
                if path.name == pattern:
                    if VERBOSE:
                        print(f"  [VERBOSE] Excluded (name): {path} (pattern: {pattern})", file=sys.stderr)
                    return True

        return False


def is_online() -> bool:
    """Check if we have network connectivity."""
    try:
        socket.create_connection(("a.pool.opentimestamps.org", 443), timeout=5)
        return True
    except OSError:
        return False


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA3-256 hash of a file."""
    hasher = hashlib.sha3_256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_hmac(secret: str, file_hash: str) -> str:
    """Compute HMAC-SHA3-256 of a file hash."""
    return hmac.new(
        secret.encode(),
        file_hash.encode(),
        hashlib.sha3_256
    ).hexdigest()


def generate_secret() -> str:
    """Generate a random 32-byte (256-bit) secret."""
    return secrets.token_hex(32)


def now_iso() -> str:
    """Return current time in ISO8601 format with timezone."""
    return datetime.now(timezone.utc).astimezone().isoformat()


def truncate_path(path: Path, max_length: int = 70) -> str:
    """Truncate path to fit within max_length, keeping start and end."""
    path_str = str(path)
    if len(path_str) <= max_length:
        return path_str

    # Calculate how much we can keep on each side
    ellipsis = "..."
    side_length = (max_length - len(ellipsis)) // 2

    return path_str[:side_length] + ellipsis + path_str[-side_length:]


class FileScanner:
    """Scans filesystem for files to timestamp."""

    def __init__(self, exclusion_rules: ExclusionRules, db: Database):
        self.exclusion_rules = exclusion_rules
        self.db = db

    def scan_paths(self, paths: list[str]) -> list[dict]:
        """
        Scan given paths and return list of files that need processing.
        Returns list of dicts with: path, size, mtime, needs_hash
        """
        files_to_process = []

        for path_str in paths:
            path = Path(path_str).expanduser().resolve()
            if not path.exists():
                print(f"Warning: Path does not exist: {path}")
                continue

            if path.is_file():
                # Single file
                if not self.exclusion_rules.should_exclude(path):
                    file_info = self._check_file(path)
                    if file_info:
                        files_to_process.append(file_info)
            elif path.is_dir():
                # Directory - recursive scan
                truncated = truncate_path(path)
                print(f"  Scanning: {truncated}/")
                files_to_process.extend(self._scan_directory(path))
                # Clear the scanning line completely
                print("\r" + " " * 100 + "\r", end='')

        return files_to_process

    def _scan_directory(self, directory: Path) -> list[dict]:
        """Recursively scan a directory."""
        files = []

        try:
            for entry in directory.iterdir():
                # Check exclusion rules
                if self.exclusion_rules.should_exclude(entry):
                    continue

                try:
                    # Skip symlinks to avoid following them outside the scan path
                    if entry.is_symlink():
                        if VERBOSE:
                            print(f"  [VERBOSE] Skipping symlink: {entry}", file=sys.stderr)
                        continue

                    if entry.is_file():
                        file_info = self._check_file(entry)
                        if file_info:
                            files.append(file_info)
                    elif entry.is_dir():
                        # Show subdirectory being scanned with truncation
                        truncated = truncate_path(entry)
                        # Clear line first, then print new path
                        print("\r" + " " * 100, end='\r')
                        print(f"  Scanning: {truncated}/", end='', flush=True)
                        # Recurse into subdirectory
                        files.extend(self._scan_directory(entry))

                except (PermissionError, OSError) as e:
                    # Skip files we can't access
                    # Clear scanning line before showing warning
                    print("\r" + " " * 100 + "\r", end='')
                    print(f"Warning: Cannot access {entry}: {e}", file=sys.stderr)
                    continue

        except (PermissionError, OSError) as e:
            # Clear scanning line before showing warning
            print("\r" + " " * 100 + "\r", end='')
            print(f"Warning: Cannot scan directory {directory}: {e}", file=sys.stderr)

        return files

    def _check_file(self, file_path: Path) -> Optional[dict]:
        """
        Check if file needs processing by comparing with database.
        Returns file info dict if needs processing, None otherwise.
        """
        try:
            stat_info = file_path.stat()
            file_size = stat_info.st_size
            mtime = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).astimezone().isoformat()

            # Check if we have a record for this file
            db_record = self.db.get_file_record(str(file_path))

            needs_hash = False
            if db_record is None:
                # New file
                needs_hash = True
            elif db_record["file_size"] != file_size or db_record["mtime"] != mtime:
                # File has changed
                needs_hash = True

            if needs_hash:
                return {
                    "path": file_path,
                    "size": file_size,
                    "mtime": mtime,
                    "needs_hash": True
                }

        except (PermissionError, OSError) as e:
            print(f"Warning: Cannot stat {file_path}: {e}", file=sys.stderr)

        return None


def parsearg() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="i_have - File Existence Proof System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Scan home directory
  %(prog)s ~/Documents        # Scan specific directory
  %(prog)s /                  # Scan entire system
  %(prog)s --verify HASH      # Verify file hash
  %(prog)s --dry-run ~/Photos # Show files without processing
        """
    )
    parser.add_argument(
        'paths',
        nargs='+',
        help='Directories to scan (at least one required)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {VERSION}'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show files without processing'
    )
    parser.add_argument(
        '--offline',
        action='store_true',
        help='Skip online processing (OTS, Git)'
    )
    parser.add_argument(
        '--verify',
        metavar='HASH',
        help='Verify existence proof for given file hash'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose debug output'
    )
    return parser.parse_args()


def process_files(files: list[dict], db: Database, upload_date: str, dry_run: bool = False) -> list[str]:
    """
    Process files: compute hashes, generate HMACs, store in database.
    Returns list of HMACs generated.
    """
    hmacs = []

    print(f"[Phase 2] Computing hashes for {len(files)} file(s)...")

    for file_info in tqdm(files, desc="  Processing", unit="file"):
        file_path = file_info["path"]

        try:
            # Compute file hash
            file_hash = compute_file_hash(file_path)

            if VERBOSE:
                tqdm.write(f"  [VERBOSE] File: {file_path}")
                tqdm.write(f"  [VERBOSE]   Hash: {file_hash}")

            if not dry_run:
                # Generate HMAC secret and compute HMAC
                hmac_secret = generate_secret()
                hmac_value = compute_hmac(hmac_secret, file_hash)

                if VERBOSE:
                    tqdm.write(f"  [VERBOSE]   Secret: {hmac_secret}")
                    tqdm.write(f"  [VERBOSE]   HMAC: {hmac_value}")

                # Store in database
                record = {
                    "first_seen": now_iso(),
                    "file_path": str(file_path),
                    "file_size": file_info["size"],
                    "mtime": file_info["mtime"],
                    "hash_algorithm": "sha3-256",
                    "file_hash": file_hash,
                    "hmac_secret": hmac_secret,
                    "hmac": hmac_value,
                    "upload_date": upload_date
                }
                db.insert_record(record)
                hmacs.append(hmac_value)

        except Exception as e:
            tqdm.write(f"Warning: Failed to process {file_path}: {e}")
            continue

    return hmacs


def write_hmac_list(hmacs: list[str], upload_date: str) -> Path:
    """Write HMACs to a sorted list file."""
    output_path = I_HAVE_DIR / f"{upload_date}.txt"

    # Sort HMACs for consistent ordering
    sorted_hmacs = sorted(hmacs)

    with open(output_path, 'w') as f:
        for hmac_value in sorted_hmacs:
            f.write(f"{hmac_value}\n")

    return output_path


def verify_ots_with_api(ots_file: Path) -> tuple[bool, Optional[str]]:
    """
    Verify OTS file using --no-bitcoin flag and Blockstream API.
    Returns (success: bool, block_number: Optional[str])
    """
    try:
        # Run ots verify with --no-bitcoin to get block info without local Bitcoin node
        result = subprocess.run(
            ["ots", "--no-bitcoin", "verify", str(ots_file)],
            capture_output=True,
            timeout=10
        )

        output = result.stdout.decode() + result.stderr.decode()

        if VERBOSE:
            print(f"  [VERBOSE] ots --no-bitcoin verify output: {output}")

        # Extract block height and merkleroot from output
        block_match = re.search(r'block\s+(\d+)', output, re.IGNORECASE)
        merkleroot_match = re.search(r'merkleroot\s+([a-f0-9]+)', output, re.IGNORECASE)

        if not block_match or not merkleroot_match:
            if VERBOSE:
                print("  [VERBOSE] Failed to parse block/merkleroot from output")
            return False, None

        block = block_match.group(1)
        expected_root = merkleroot_match.group(1)

        if VERBOSE:
            print(f"  [VERBOSE] Block: {block}, Expected merkleroot: {expected_root}")

        # Fetch actual blockchain data from Blockstream API
        # Get block hash from block height
        block_hash_url = f"https://blockstream.info/api/block-height/{block}"
        with urllib.request.urlopen(block_hash_url, timeout=10) as response:
            block_hash = response.read().decode().strip()

        if VERBOSE:
            print(f"  [VERBOSE] Block hash: {block_hash}")

        # Get actual merkleroot from block data
        block_data_url = f"https://blockstream.info/api/block/{block_hash}"
        with urllib.request.urlopen(block_data_url, timeout=10) as response:
            block_data = json.loads(response.read().decode())

        actual_root = block_data.get('merkle_root', '')

        if VERBOSE:
            print(f"  [VERBOSE] Actual merkleroot: {actual_root}")

        # Compare merkleroot
        if expected_root == actual_root:
            return True, block
        else:
            print("  Warning: Merkleroot mismatch!")
            print(f"    Expected: {expected_root}")
            print(f"    Actual:   {actual_root}")
            return False, None

    except subprocess.TimeoutExpired:
        if VERBOSE:
            print("  [VERBOSE] ots verify timeout")
        return False, None
    except urllib.error.URLError as e:
        if VERBOSE:
            print(f"  [VERBOSE] API request failed: {e}")
        return False, None
    except Exception as e:
        if VERBOSE:
            print(f"  [VERBOSE] Verification error: {e}")
        return False, None


def process_opentimestamps(hmac_list_path: Path) -> bool:
    """
    Timestamp the HMAC list using OpenTimestamps.
    Returns True if successful, False otherwise.
    """
    try:
        # Check if ots command is available
        result = subprocess.run(
            ["ots", "--version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            print("  Error: OpenTimestamps client not installed")
            print("  Install with: pip install opentimestamps-client")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  Error: OpenTimestamps client not found")
        print("  Install with: pip install opentimestamps-client")
        return False

    # Create timestamp
    try:
        result = subprocess.run(
            ["ots", "stamp", str(hmac_list_path)],
            check=True,
            capture_output=True,
            timeout=30
        )
        if VERBOSE:
            print(f"  [VERBOSE] ots stamp output: {result.stdout.decode()}")
    except subprocess.CalledProcessError as e:
        print(f"  Error stamping: {e.stderr.decode()}")
        return False
    except subprocess.TimeoutExpired:
        print("  Error: Stamping timed out")
        return False

    # Wait for Bitcoin confirmation with retries
    ots_file = hmac_list_path.with_suffix(hmac_list_path.suffix + '.ots')
    print("  Waiting for Bitcoin confirmation...")

    for attempt in range(1, OTS_UPGRADE_MAX_ATTEMPTS + 1):
        try:
            result = subprocess.run(
                ["ots", "upgrade", str(ots_file)],
                capture_output=True,
                timeout=30
            )

            if VERBOSE:
                print(f"  [VERBOSE] ots upgrade output: {result.stdout.decode()}")
                if result.stderr:
                    print(f"  [VERBOSE] ots upgrade stderr: {result.stderr.decode()}")

            # Check if verification works using API-based verification
            # This works without a local Bitcoin node
            verified, block = verify_ots_with_api(ots_file)

            if verified and block:
                print("  Success! Timestamp verified")
                print(f"  Bitcoin block: {block}")
                return True

            # Not ready yet
            if attempt < OTS_UPGRADE_MAX_ATTEMPTS:
                print(f"  Attempt {attempt}/{OTS_UPGRADE_MAX_ATTEMPTS}: Pending...")
                time.sleep(OTS_UPGRADE_INTERVAL)

        except subprocess.TimeoutExpired:
            print(f"  Attempt {attempt}/{OTS_UPGRADE_MAX_ATTEMPTS}: Timeout")
            if attempt < OTS_UPGRADE_MAX_ATTEMPTS:
                time.sleep(OTS_UPGRADE_INTERVAL)
        except Exception as e:
            print(f"  Error during upgrade: {e}")
            return False

    print("  Timeout: Bitcoin confirmation not received within 6 hours")
    print("  The .ots file is saved but incomplete. Run 'ots upgrade' later.")
    return False


def git_push(upload_date: str) -> bool:
    """
    Commit and push HMAC list and OTS files to Git.
    Returns True if successful, False otherwise.
    """
    try:
        # Check if we're in a git repo
        result = subprocess.run(
            ["git", "-C", str(I_HAVE_DIR), "status"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            print("  Warning: Not a git repository. Skipping git push.")
            print(f"  Initialize with: cd {I_HAVE_DIR} && git init")
            return False

        # Add files
        if VERBOSE:
            print("  [VERBOSE] Running: git add *.txt *.ots")
        add_result = subprocess.run(
            ["git", "-C", str(I_HAVE_DIR), "add", "*.txt", "*.ots"],
            check=True,
            capture_output=True,
            timeout=10
        )
        if VERBOSE and add_result.stdout:
            print(f"  [VERBOSE] git add output: {add_result.stdout.decode()}")

        # Commit
        commit_msg = f"Add timestamp {upload_date}"
        if VERBOSE:
            print(f"  [VERBOSE] Running: git commit -m \"{commit_msg}\"")
        commit_result = subprocess.run(
            ["git", "-C", str(I_HAVE_DIR), "commit", "-m", commit_msg],
            check=True,
            capture_output=True,
            timeout=10
        )
        if VERBOSE:
            print(f"  [VERBOSE] git commit output: {commit_result.stdout.decode()}")

        # Push
        if VERBOSE:
            print("  [VERBOSE] Running: git push")
        result = subprocess.run(
            ["git", "-C", str(I_HAVE_DIR), "push"],
            capture_output=True,
            timeout=30
        )
        if VERBOSE:
            print(f"  [VERBOSE] git push output: {result.stdout.decode()}")
            if result.stderr:
                print(f"  [VERBOSE] git push stderr: {result.stderr.decode()}")

        if result.returncode == 0:
            print(f"  Committed: \"{commit_msg}\"")
            print("  Pushed to remote")
            return True
        else:
            print(f"  Warning: Push failed: {result.stderr.decode()}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"  Error: {e.stderr.decode()}")
        return False
    except subprocess.TimeoutExpired:
        print("  Error: Git operation timed out")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def setup_i_have_directory() -> None:
    """Set up the i_have directory with necessary files."""
    # Create .gitignore if it doesn't exist
    gitignore_path = I_HAVE_DIR / ".gitignore"
    if not gitignore_path.exists():
        gitignore_content = """# i_have - Exclude database from git
i_have.db
i_have.db-journal
i_have.db-wal
*.pyc
__pycache__/
.DS_Store
"""
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)
        print(f"Created: {gitignore_path}")

    # Create README if it doesn't exist
    readme_path = I_HAVE_DIR / "README.md"
    if not readme_path.exists():
        readme_content = """# i_have - File Existence Proof

This directory contains timestamped HMAC lists proving file existence.

## Files

- `YYYY-MM-DD_HHMMSS.txt` - HMAC lists (one per timestamp session)
- `YYYY-MM-DD_HHMMSS.txt.ots` - OpenTimestamps proofs
- `i_have.db` - Local database (NOT tracked in git)

## Verification

To verify a file existed at a specific time:

1. Get the file's SHA3-256 hash
2. Get the HMAC secret (from the person claiming ownership)
3. Compute HMAC-SHA3-256(secret, hash)
4. Check if the HMAC appears in the timestamped list
5. Verify the .ots file with OpenTimestamps

## Setup Git Repository

```bash
cd ~/i_have
git init
git add .gitignore README.md
git commit -m "Initial commit"
git remote add origin YOUR_REPO_URL
git push -u origin main
```
"""
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        print(f"Created: {readme_path}")


def main() -> None:
    """Main entry point."""
    global VERBOSE
    args = parsearg()

    # Set verbose flag
    VERBOSE = args.verbose

    # Ensure i_have directory exists
    I_HAVE_DIR.mkdir(parents=True, exist_ok=True)

    # Set up directory structure
    setup_i_have_directory()

    # Initialize database
    db = Database(DB_PATH)

    if VERBOSE:
        print(f"[VERBOSE] Database: {DB_PATH}")
        print(f"[VERBOSE] Data directory: {I_HAVE_DIR}")

    if args.verify:
        # Verification mode
        verify_mode(db, args.verify)
        return

    print(f"i_have v{VERSION} - File Existence Proof System")
    print("=" * 44)
    print()

    # Initialize exclusion rules
    exclusion_rules = ExclusionRules(IGNORE_LIST_PATH)

    # Phase 1: File scanning
    print("[Phase 1] Scanning files...")
    scanner = FileScanner(exclusion_rules, db)
    files_to_process = scanner.scan_paths(args.paths)
    print(f"  Found: {len(files_to_process)} file(s) to process")
    print()

    if len(files_to_process) == 0:
        print("No files to process. Everything is up to date.")
        return

    if args.dry_run:
        print("Dry run - files that would be processed:")
        for file_info in files_to_process:
            print(f"  {file_info['path']}")
        return

    # Generate upload date identifier
    upload_date = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    # Phase 2 & 3: Hash computation and HMAC generation
    hmacs = process_files(files_to_process, db, upload_date, args.dry_run)
    print()

    if not hmacs:
        print("No HMACs generated. Exiting.")
        return

    # Phase 4: HMAC list output
    print("[Phase 4] Writing HMAC list...")
    hmac_list_path = write_hmac_list(hmacs, upload_date)
    print(f"  Output: {hmac_list_path.name} ({len(hmacs)} entries)")
    print()

    # Check if we should continue with online processing
    if args.offline:
        print("Offline mode: Skipping OpenTimestamps and Git push")
        print(f"\nDone! {len(hmacs)} file(s) timestamped (offline).")
        return

    if not is_online():
        print("Network unavailable: Skipping OpenTimestamps and Git push")
        print("Run again when online to complete timestamping.")
        print(f"\nDone! {len(hmacs)} file(s) processed (offline).")
        return

    # Phase 5: OpenTimestamps
    print("[Phase 5] OpenTimestamps...")
    ots_success = process_opentimestamps(hmac_list_path)
    print()

    if not ots_success:
        print("OpenTimestamps failed. Files are saved but not timestamped.")
        print("Run again to retry timestamping.")
        return

    # Phase 6: Git push
    print("[Phase 6] Git push...")
    git_push(upload_date)
    print()

    print(f"Done! {len(hmacs)} file(s) timestamped.")


def verify_mode(db: Database, file_hash: str) -> None:
    """Display verification information for a file hash."""
    info = db.get_verification_info(file_hash)

    if not info:
        print(f"No record found for file hash: {file_hash}")
        sys.exit(1)

    print(f"File hash: {file_hash}")
    print(f"First seen: {info['first_seen']}")
    print(f"HMAC Secret: {info['hmac_secret']}")
    print(f"HMAC: {info['hmac']}")
    print(f"Upload date: {info['upload_date']}")

    ots_file = I_HAVE_DIR / f"{info['upload_date']}.txt.ots"
    if ots_file.exists():
        print(f"OTS file: {ots_file}")
    else:
        print("OTS file: Not found")


if __name__ == '__main__':
    main()
