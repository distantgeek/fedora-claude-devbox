---
name: testing-go
description: Go testing with table-driven tests, go-fuzz, and coverage enforcement
compatibility: opencode
---
## Quick Setup

```bash
go install golang.org/x/tools/cmd/cover@latest
```

## Test Structure Convention

```
pkg/
├── module.go
├── module_test.go         # Same directory, _test.go suffix
└── testdata/              # Test fixtures and golden files
```

## Standard Test Command

```bash
go test ./... -coverprofile=coverage.out -covermode=atomic
go tool cover -func=coverage.out | grep total | awk '{print $3}'
```

## Test Patterns

### Table-Driven Tests (Idiomatic)
```go
func TestIncrement(t *testing.T) {
    tests := []struct {
        name     string
        input    int
        expected int
    }{
        {"positive", 1, 2},
        {"zero", 0, 1},
        {"negative", -1, 0},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Increment(tt.input)
            if got != tt.expected {
                t.Errorf("Increment(%d) = %d; want %d", tt.input, got, tt.expected)
            }
        })
    }
}
```

### Subtests with Setup/Teardown
```go
func TestWithDB(t *testing.T) {
    db := setupTestDB(t)
    t.Cleanup(func() { db.Close() })
    // tests...
}
```

### Property-Based (via rapid or gopter)
```go
import "pgregory.net/rapid"

func TestIncrementAlwaysIncreases(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        x := rapid.IntRange(0, math.MaxInt-1).Draw(t, "x")
        if Increment(x) <= x {
            t.Fatalf("Increment(%d) did not increase", x)
        }
    })
}
```

### Fuzzing (Native Go 1.18+)
```go
func FuzzParse(f *testing.F) {
    f.Fuzz(func(t *testing.T, input string) {
        _, err := Parse(input)
        if err != nil {
            t.Skip() // expected for invalid input
        }
    })
}
```

### Coverage Thresholds
- Overall: >= 80%
- Check: `go tool cover -func=coverage.out | grep total`
<!-- advanced: go-fuzz, mutation testing (not yet mature in Go) -->
