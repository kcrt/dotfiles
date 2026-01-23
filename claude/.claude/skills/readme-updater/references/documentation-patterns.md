# Documentation Patterns for Rust and TypeScript

This reference provides patterns for documenting APIs, utilities, and operations in README.md for Rust and TypeScript projects.

## Rust Documentation Patterns

### Public API Documentation

**Functions:**
```markdown
### `function_name(arg1: Type1, arg2: Type2) -> ReturnType`

Brief description of what the function does.

**Parameters:**
- `arg1`: Description of first parameter
- `arg2`: Description of second parameter

**Returns:** Description of return value

**Example:**
```rust
use crate::function_name;
let result = function_name(value1, value2);
```
```

**Structs:**
```markdown
### `StructName`

Description of the struct purpose.

**Fields:**
- `field1: Type` - Description
- `field2: Type` - Description

**Methods:**
#### `new() -> Self`
Constructor description.

#### `method_name(&self, arg: Type) -> Result<T, E>`
Method description with error handling.
```

### CLI Tools Documentation

```markdown
## Command-Line Usage

**Basic Usage:**
```bash
cargo run -- [OPTIONS] <INPUT>
```

**Options:**
- `-v, --verbose` - Enable verbose output
- `-o, --output <FILE>` - Specify output file

**Examples:**
```bash
cargo run -- input.txt
cargo run -- --verbose --output result.txt input.txt
```
```

## TypeScript Documentation Patterns

### Functions

```markdown
### `functionName(arg1: Type1, arg2: Type2): ReturnType`

Brief description of function behavior.

**Parameters:**
- `arg1`: Description
- `arg2`: Description (optional)

**Returns:** Description

**Example:**
```typescript
import { functionName } from './module';
const result = functionName(value1, value2);
```
```

### Classes

```markdown
### `ClassName`

Description of class purpose.

**Constructor:**
```typescript
constructor(arg1: Type1, arg2?: Type2)
```

**Properties:**
- `property1: Type` - Description
- `property2: Type` - Description

**Methods:**
#### `methodName(arg: Type): ReturnType`
Method description.

**Example:**
```typescript
const instance = new ClassName(arg1);
const result = instance.methodName(value);
```
```

### Development Commands

```markdown
## Development

**Build:**
```bash
npm run build          # Production build
npm run build:dev      # Development build
npm run build:watch    # Watch mode
```

**Testing:**
```bash
npm test              # Run all tests
npm run test:watch    # Watch mode
```
```

## Section Preservation Rules

### Always Preserve These Sections:

1. **Installation** - Keep all installation instructions unchanged
2. **TODO** - Preserve all TODO items and task lists
3. **Getting Started** - Keep quick start guides unchanged
4. **Contributing** - Preserve contribution guidelines
5. **License** - Never modify license information

### Sections to Update:

1. **API Documentation** - Update based on code changes
2. **Utility Functions** - Update based on new/changed utilities
3. **Configuration** - Update when config options change
4. **Examples** - Update to reflect current API
5. **Usage** - Update when usage patterns change
