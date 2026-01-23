#!/usr/bin/env python3
"""
Get last update timestamps for README.md and spec/specification directories.
Returns commit hash and date for the last modification.
"""

import subprocess
import sys
import json
from pathlib import Path
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


def get_last_commit(file_path, repo_path="."):
    """Get the last commit that modified a file or directory."""
    cmd = [
        "git", "log", "-1", 
        "--format=%H|%ai|%s", 
        "--", file_path
    ]
    output = run_git_command(cmd, cwd=repo_path)
    
    if output:
        parts = output.split("|", 2)
        return {
            "hash": parts[0],
            "date": parts[1],
            "message": parts[2]
        }
    return None


def find_spec_directory(repo_path="."):
    """Find spec or specification directory if it exists."""
    repo = Path(repo_path)
    
    for name in ["spec", "specification", "specs", "specifications"]:
        spec_dir = repo / name
        if spec_dir.exists() and spec_dir.is_dir():
            return name
    
    return None


def main(repo_path="."):
    """Get last update information for README and spec directories."""
    results = {}
    
    # Check README.md
    readme_path = "README.md"
    readme_commit = get_last_commit(readme_path, repo_path)
    if readme_commit:
        results["readme"] = {
            "path": readme_path,
            "last_commit": readme_commit
        }
    else:
        results["readme"] = {"path": readme_path, "last_commit": None}
    
    # Check spec directory
    spec_dir = find_spec_directory(repo_path)
    if spec_dir:
        spec_commit = get_last_commit(spec_dir, repo_path)
        results["spec"] = {
            "path": spec_dir,
            "last_commit": spec_commit
        }
    else:
        results["spec"] = {"path": None, "last_commit": None}
    
    return results


if __name__ == "__main__":
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    results = main(repo_path)
    print(json.dumps(results, indent=2))
