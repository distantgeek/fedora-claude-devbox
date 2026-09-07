---
name: testing-rust
description: Rust testing with cargo test, proptest (property-based), cargo-fuzz, and cargo-mutants
compatibility: opencode
---
## Quick Setup

```bash
cargo install cargo-tarpaulin cargo-fuzz cargo-mutants
```

## Test Structure Convention

```
src/lib.rs                 # Unit tests inline with #[cfg(test)]
tests/
├── integration_test.rs    # Integration tests
└── common/mod.rs          # Shared test utilities
```

## Standard Test Command

```bash
cargo test
cargo tarpaulin --out Json --fail-under 80
```

## Test Patterns

### Unit Test (inline)
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_increment_positive() {
        assert_eq!(increment(1), 2);
    }

    #[test]
    #[should_panic(expected = "overflow")]
    fn test_increment_max_panics() {
        increment(u32::MAX);
    }
}
```

### Property-Based (proptest)
```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_increment_always_increases(x in 0..i32::MAX) {
        assert!(increment(x) > x);
    }
}
```

### Fuzzing (cargo-fuzz)
Place in `fuzz/fuzz_targets/`:
```rust
// fuzz_targets/increment.rs
fuzz_target!(|data: &[u8]| {
    if let Ok(s) = std::str::from_utf8(data) {
        let _ = parse(s);
    }
});
```

### Mutation Testing
```bash
cargo mutants --timeout 60
```

### Coverage Thresholds
- Overall: >= 80%
- Unsafe code: 100% (every unsafe block must be tested)
<!-- advanced: cargo-fuzz, cargo-mutants -->
