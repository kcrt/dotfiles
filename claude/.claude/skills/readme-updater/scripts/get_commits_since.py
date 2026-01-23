#!/usr/bin/env python3
"""
Get commits since a specific date with file changes.
Returns list of commits with affected files for analysis.
"""

import subprocess
import sys
import json
from datetime import datetime


def run_git_command(cmd, cwd=None):
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        return None


def get_commits_since(since_date, repo_path=".", exclude_files=None):
    """
    Get commits since a specific date.
    
    Args:
        since_date: Date string in format 'YYYY-MM-DD HH:MM:SS' or commit hash
        repo_path: Path to git repository
        exclude_files: List of files to exclude from analysis (e.g., README.md, spec/)
    
    Returns:
        List of commit dictionaries with hash, date, message, and changed files
    """
    if exclude_files is None:
        exclude_files = []
    
    # Get commit hashes
    cmd = ["git", "log", "--format=%H", f"{since_date}..HEAD"]
    output = run_git_command(cmd, cwd=repo_path)
    
    if not output:
        return []
    
    commit_hashes = output.split("\n")
    commits = []
    
    for commit_hash in commit_hashes:
        # Get commit info
        cmd = ["git", "log", "-1", "--format=%H|%ai|%an|%s", commit_hash]
        info = run_git_command(cmd, cwd=repo_path)
        
        if not info:
            continue
        
        parts = info.split("|", 3)
        
        # Get changed files
        cmd = ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", commit_hash]
        files_output = run_git_command(cmd, cwd=repo_path)
        
        changed_files = []
        if files_output:
            for line in files_output.split("\n"):
                if line.strip():
                    status, filepath = line.split("\t", 1)
                    # Skip excluded files
                    skip = False
                    for exclude in exclude_files:
                        if filepath.startswith(exclude) or filepath == exclude:
                            skip = True
                            break
                    
                    if not skip:
                        changed_files.append({
                            "status": status,
                            "path": filepath
                        })
        
        if changed_files:  # Only include commits with relevant file changes
            commits.append({
                "hash": parts[0],
                "date": parts[1],
                "author": parts[2],
                "message": parts[3],
                "changed_files": changed_files
            })
    
    return commits


def main():
    """Main function to run from command line."""
    if len(sys.argv) < 2:
        print("Usage: get_commits_since.py <since_date_or_hash> [repo_path]", file=sys.stderr)
        print("Example: get_commits_since.py '2024-01-01' .", file=sys.stderr)
        print("Example: get_commits_since.py abc123def .", file=sys.stderr)
        sys.exit(1)
    
    since_date = sys.argv[1]
    repo_path = sys.argv[2] if len(sys.argv) > 2 else "."
    
    # Exclude documentation files by default
    exclude_files = ["README.md", "spec/", "specification/", "specs/", "specifications/"]
    
    commits = get_commits_since(since_date, repo_path, exclude_files)
    print(json.dumps(commits, indent=2))


if __name__ == "__main__":
    main()
