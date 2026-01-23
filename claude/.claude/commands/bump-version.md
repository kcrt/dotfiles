# Bump Version Command

This command will bump the version number in the project and create a git tag.
Parameter: $ARGUMENTS

## Usage
- Accept parameter of major, minor, patch. If not specified, use patch.
- Update version information in package information files:
  - For Rust projects: modify `Cargo.toml`
  - For Node.js projects: use `npm version patch`, `npm version minor`, `npm version major`
  - For Python projects: modify `pyproject.toml` or `setup.py`
- Add staged files and commit version using the git-commit command
- Perform `git push` and `git tag` with appropriate version number (e.g. v1.0.1)
- If origin is GitHub, push tag

## Implementation Steps

1. **Detect project type**: Check for `Cargo.toml`, `package.json`, `pyproject.toml`, or `setup.py`
2. **Parse version type**: Default to "patch" if not specified
3. **Update version**: 
   - For Node.js: Use `npm version [major|minor|patch]`
   - For Rust: Parse and update `Cargo.toml` version field
   - For Python: Parse and update version in `pyproject.toml` or `setup.py`
4. **Stage and commit**: Add all changes and commit with `:bookmark: Bump version to vX.Y.Z`
5. **Push and tag**: Push changes and create/push git tag

## Example Commands
```bash
# Bump patch version (default)
/bump-version

# Bump minor version
/bump-version minor

```

## Version Format
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Git tags should be prefixed with 'v' (e.g., v1.0.1)
- Commit message should use :bookmark: gitmoji for version bumps