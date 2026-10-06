# -*- coding: utf-8 -*-
"""Get secrets from with-secret (https://github.com/kcrt/with-secret).

Secrets are no longer exported into every shell. A script that needs one calls
`require_secrets()` before using it; if the variables are missing, the script
re-runs itself through `with-secret`, which asks for Touch ID (or skips asking
when an allow rule matches this script's SHA-256) and puts the secrets into the
new process's environment only.

The script must be executable with a shebang line: with-secret hashes the file
it executes, so running it via `python3 script.py` would hash python3 instead.

Use the standard library only (see termtext for why).
"""

from __future__ import annotations

import os
import sys


def require_secrets(*names: str) -> None:
    """Return if every name is set; otherwise re-run this script via with-secret.

    Call it after argument parsing, so that `--help` works without approval.
    Does not return when re-running; exits with a message if with-secret is
    not installed.
    """
    if all(os.environ.get(name) for name in names):
        return
    script = os.path.abspath(sys.argv[0])
    command = ["with-secret", ",".join(names), "--", script, *sys.argv[1:]]
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        os.execvp(command[0], command)
    except FileNotFoundError:
        sys.exit(f"{', '.join(names)} is not set, and with-secret is not installed.")
