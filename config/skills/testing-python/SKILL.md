---
name: testing-python
description: Python testing with pytest, hypothesis (property-based), and coverage enforcement
compatibility: opencode
---
## Quick Setup

```bash
pip install pytest pytest-cov hypothesis coverage
```

## Test Structure Convention

```
tests/
├── test_<module>.py       # Mirror src structure
├── conftest.py            # Shared fixtures
└── factories/             # Test data factories
```

## Standard Test Command

```bash
pytest --cov=. --cov-report=term-missing --cov-report=json --cov-fail-under=80
```

## Test Patterns

### Unit Test
```python
def test_<function>_<scenario>():
    """Arrange → Act → Assert pattern"""
    result = function_under_test(input)
    assert result == expected

@pytest.mark.parametrize("input,expected", [
    (1, 2), (0, 1), (-1, 0)
])
def test_increment(input, expected):
    assert increment(input) == expected
```

### Property-Based (hypothesis)
```python
from hypothesis import given, strategies as st

@given(st.integers())
def test_increment_always_increases(x):
    assert increment(x) > x
```

### Coverage Thresholds
- Overall: >= 80%
- Critical paths (auth, payment, crypto): >= 90%
- Branch coverage: tracked but not gated by default

<!-- advanced: fuzzing with atheris, mutation testing with mutmut -->
