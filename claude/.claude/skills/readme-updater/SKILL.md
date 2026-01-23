---
name: readme-updater
description: Automatically update README.md and specification directories by analyzing git commits since last documentation update. Use when user requests to "update README", "sync documentation", "update docs", or when documentation is outdated. Works with Rust and TypeScript projects primarily, analyzing code changes to keep API docs, utility functions, and operational details current while preserving TODO and Installation sections.
---

# README Updater

Automatically synchronizes README.md and specification directories with code changes by analyzing git history and updating relevant documentation sections.

## Workflow

### Step 1: Identify Documentation Status

Locate and check last update times:

1. Find README.md in project root
2. Look for spec/specification directory (check: `spec/`, `specification/`, `specs/`, `specifications/`)
3. Use `scripts/get_last_update.py` to get last modification dates:

```bash
python3 scripts/get_last_update.py /path/to/repo
```

Output provides last commit hash and date for both README and spec directory.

### Step 2: Analyze Changes Since Last Update

Get commits that changed code (excluding documentation):

```bash
python3 scripts/get_commits_since.py <commit_hash> /path/to/repo
```

This returns commits with:
- Changed file paths and modification status (A=added, M=modified, D=deleted)
- Commit messages and dates
- Automatically excludes README.md and spec/ files

Review the changed files to understand:
- New APIs or functions added
- Modified function signatures or behavior
- Removed or deprecated features
- Configuration changes
- New utilities or helpers

### Step 3: Read Current Documentation

Read README.md and spec files to understand current documentation structure:

1. Identify existing sections (use headers as markers)
2. Locate API documentation sections
3. Find utility function documentation
4. Note operational/usage sections
5. **Mark sections to preserve:** TODO, Installation, Getting Started, Contributing, License

### Step 4: Analyze Code Changes

For each changed file from Step 2:

1. Read the file content to understand changes
2. Extract relevant documentation-worthy information:
   - New public APIs or functions
   - Changed function signatures
   - New configuration options
   - Modified behavior or usage patterns
3. Refer to `references/documentation-patterns.md` for appropriate documentation format based on language (Rust or TypeScript)

### Step 5: Update Documentation

Update README.md sections systematically:

**Update these sections:**
- API Documentation - Add/modify/remove based on code changes
- Utility Functions - Document new helpers and tools
- Configuration - Update options and environment variables
- Usage Examples - Update to reflect current API
- Operational Details - Update commands, build instructions (excluding Installation)

**Preserve these sections (DO NOT MODIFY):**
- Installation instructions
- TODO lists
- Getting Started guides
- Contributing guidelines
- License information

**Update spec/ files if they exist:**
- Technical specifications affected by code changes
- API contracts or schemas
- Protocol definitions
- Architecture decisions (if outdated)

### Step 6: Write Updated Documentation

Apply changes to README.md and spec files:

1. Use `str_replace` to update specific sections
2. Follow documentation patterns from `references/documentation-patterns.md`
3. Maintain consistent formatting with existing style
4. Ensure examples compile/run with current code
5. Keep language concise and clear

**Documentation Quality Standards:**
- Use code examples that match current API
- Include parameter descriptions
- Document error handling and edge cases
- Show realistic usage scenarios
- Match the project's existing documentation tone

## Language-Specific Considerations

### Rust Projects

Focus on:
- Public API (functions, structs, traits, enums with `pub` visibility)
- Error types and handling patterns
- CLI usage if applicable
- Cargo commands and features

### TypeScript Projects

Focus on:
- Exported functions and classes
- Interface and type definitions
- Async/Promise patterns
- npm scripts and build commands
- Module organization

## Resources

### scripts/get_last_update.py

Gets last commit information for README.md and spec directories. Returns JSON with commit hashes and dates.

### scripts/get_commits_since.py

Retrieves commits since a specific commit hash or date, excluding documentation files. Returns list of commits with changed file paths.

### references/documentation-patterns.md

Comprehensive patterns for documenting Rust and TypeScript code in README.md, including:
- Function and method documentation formats
- Class and struct documentation
- Error handling documentation
- CLI and build command documentation
- Section preservation rules

Load this reference when formatting documentation to ensure consistent, high-quality output.

## Example Usage

User: "Update README"

1. Run `get_last_update.py` → README last updated 2 weeks ago
2. Run `get_commits_since.py` → 5 commits with code changes
3. Read README.md → Identify API docs section, TODO section
4. Analyze changed files → New `parse_config()` function, modified `process_data()` signature
5. Read `documentation-patterns.md` → Get Rust function documentation format
6. Update README.md → Add `parse_config()` docs, update `process_data()` signature, preserve TODO section
7. Result: Documentation synchronized with current codebase

