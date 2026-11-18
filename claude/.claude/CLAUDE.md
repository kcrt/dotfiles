
## Coding Preferences

### General
- Be explicit and type-safe
- Write self-documenting code with clear variable names
- Avoid duplicated code (DRY principle)
- If you think the function/code is reusable, write it in a separate function or file for reuse.
- Check utility libraries in the project before implementing common functionality
- When addressing warnings or 'unused' code, investigate whether the code SHOULD be used before suppressing with `#[allow(dead_code)]` of linter off. Ask the user if the intent is to implement the functionality or remove it entirely.

### Language-Specific

#### TypeScript/JavaScript:
- Use strict mode
- Prefer functional programming patterns
- ES modules for all new code
- When adding new dependencies, add information to README.md.

#### Python:
- Type hints required
- Use uv.
- Use following shebang and package metadata for scripts:

```python
#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests",
#     "pillow",
# ]
# ///
```

#### Rust:
- Leverage type system for correctness
- Prefer Result<T, E> over panics
- When adding new dependencies, add information to README.md.

#### Swift:
- SwiftUI for UI code
- Modern concurrency (async/await)

#### R:
- Use `tidyverse` for data manipulation
- Use `dbplyr` for database interactions, instead of raw SQL queries
- If you need to investigate something, create `scratch` directory and put your code there. (YYYY-MM-DD-description.R)


### File operation
- Prefer pathlib (Python) or std::fs (Rust) over shell commands
- Use UTF-8 encoding by default (important for Japanese text)


## Data & Privacy
- Never commit sensitive data (patient info, credentials)


## Medical/Research Context
- Be precise with medical terminology
- Cite sources when discussing medical facts
- Understand statistical concepts (survival analysis, logistic regression)
- Familiar with academic publishing workflows


## Git
- Do NOT add a `Claude-Session:` footer, a `Co-Authored-By:` trailer, or any similar attribution/session line to commit messages or PR bodies, even when session/harness guidance suggests it. Keep commit messages plain.


## Working with the user
- Before installing software (`brew install`, etc.), show what will be installed and why, and ask for confirmation. Also mention it briefly before using temporary uv dependencies (cache only).
- When showing the user a file to open (video, PDF, image, deliverable), write its absolute path (`/Users/...`) alone on its own line. Do not attach punctuation or parentheses, embed it mid-sentence, or use relative / `~` paths — terminal click-to-open fails on those. Put any label on the previous line.


## Other information
- use `npx agent-browser` to use agent-browser for web browsing tasks
- `timeout` (and other GNU coreutils) is NOT installed. uutils-coreutils is available with the `uu-` prefix: use `uu-timeout` (e.g. `uu-timeout 120 <cmd>`). There is no `gtimeout` either.
