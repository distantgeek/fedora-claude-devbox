# Code Quality Standards

## General Principles

### SOLID
- **S**ingle Responsibility: Each function/class does one thing well.
- **O**pen/Closed: Open for extension, closed for modification.
- **L**iskov Substitution: Subtypes must be substitutable for their base types.
- **I**nterface Segregation: Many specific interfaces over one general-purpose.
- **D**ependency Inversion: Depend on abstractions, not concretions.

### Clean Code
- Functions should be small (ideally < 30 lines).
- Maximum 3 levels of nesting. Extract deeper levels into functions.
- Descriptive names over comments. Names should explain intent.
- No magic numbers — use named constants.
- Single level of abstraction per function.
- DRY: Don't repeat yourself. Extract shared logic.
- Error handling should not obscure logic. Use exceptions or Result types.

### Documentation Standards (ISO/IEC 26514)
- Every public API must be documented (function signatures, types, behavior).
- Document the "why", not the "what" (code should be self-documenting for "what").
- Include usage examples for non-obvious functions.
- Document edge cases and error conditions.
- README must include: build, run, test, deploy instructions.
- Keep documentation with the code, not in a separate wiki.

### Project Structure
- Consistent directory layout matching language conventions.
- Configuration separate from code (config files, env vars).
- Tests mirror source structure (src/foo.py → tests/test_foo.py).
- Clear module boundaries with minimal coupling.

## Language-Specific Standards

### Python
- Follow PEP 8. Use Black or Ruff for formatting.
- Type hints on all public functions (mypy strict mode).
- docstrings on all public APIs (Google or NumPy style).
- Prefer dataclasses/Pydantic over raw dicts.
- Use pathlib for file operations. Use context managers.

### Rust
- Follow the Rust API Guidelines.
- Use clippy with strict lints (-D warnings).
- Prefer Result/Option over unwrap/expect in library code.
- Use thiserror/anyhow for error handling.
- Derive common traits (Debug, Clone, PartialEq).
- Prefer borrows over owned values in function signatures.

### Go
- Follow Effective Go and standard formatting (gofmt).
- Table-driven tests are idiomatic.
- Handle every error. Never use _ to discard errors.
- Use interfaces sparingly — accept interfaces, return structs.
- Avoid package-level globals.
- Keep packages focused. Prefer many small packages.

### JavaScript/TypeScript
- Strict TypeScript mode (strict: true in tsconfig).
- Prefer const over let. Never use var.
- Use async/await over raw promises.
- Prefer functional patterns (map, filter, reduce) over imperative loops.
- Validate inputs at module boundaries (Zod, io-ts, or TypeScript guards).
- Avoid any. Use unknown and type narrowing.

### Java/Kotlin
- Follow Google Java Style or Kotlin Coding Conventions.
- Use final by default. Prefer immutability.
- Dependency injection over manual wiring.
- Avoid static state. It makes testing harder.
- Prefer composition over inheritance.

### SQL
- Use `>=` and `<` for date-range filters on `timestamp` columns — `BETWEEN` is inclusive and misses rows with time components on the upper boundary (e.g., `BETWEEN '2026-01-01' AND '2026-01-31'` excludes `2026-01-31 12:00:00`). Prefer `col >= '2026-01-01' AND col < '2026-02-01'`.
- Always qualify columns with table aliases in multi-table queries.
- Use `EXISTS` instead of `IN` for subqueries when possible — better performance and null-safe semantics.
- Avoid `SELECT *` in production code — enumerate columns explicitly.
- Use `JOIN` syntax over implicit comma-joins. Always specify join conditions with `ON`.
- Use `COALESCE` over `ISNULL`/`NVL` for portability.
- Use `UNION ALL` instead of `UNION` unless deduplication is explicitly needed.
- Parameterize dynamic values — never concatenate user input into SQL strings.
- Use Context7 `query_docs` to verify SQL syntax against official docs before generating SQL code.
- Context7 SQL dialect libraries:
  - PostgreSQL: `/websites/postgresql_current`
  - MySQL: `/websites/dev_mysql_doc_refman_8_0_en`
  - MSSQL: `/websites/learn_microsoft_en-us_sql`
- Context7 SQL tooling: `/websites/sqlfluff_en_stable` for linting rules.

### General
- Remove dead code — it creates maintenance burden.
- No commented-out code — use git history instead.
- No TODO comments without issue tracking reference.
- Consistent formatting across the project (use formatters).
- Consult Context7 library `/websites/peps_python` for Python style guidance (PEP 8).
