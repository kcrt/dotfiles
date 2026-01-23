
## Coding Preferences

### General
- Be explicit and type-safe
- Write self-documenting code with clear variable names

### Language-Specific

#### TypeScript/JavaScript:
- Use strict mode
- Prefer functional programming patterns
- ES modules for all new code

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

#### Swift:
- SwiftUI for UI code
- Modern concurrency (async/await)

#### R:
- Use `tidyverse` for data manipulation
- Use `dbplyr` for database interactions, instead of raw SQL queries


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
