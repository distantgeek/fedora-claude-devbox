---
name: testing-javascript
description: JavaScript/TypeScript testing with Jest/Vitest, fast-check (property-based), and stryker
compatibility: opencode
---
## Quick Setup

```bash
npm install --save-dev jest @types/jest jest-junit
# or
npm install --save-dev vitest @vitest/coverage-v8
```

## Test Structure Convention

```
src/
├── __tests__/             # Mirror src structure
│   └── module.test.ts
└── __mocks__/             # Manual mocks
```

## Standard Test Command

```bash
npm test -- --coverage --coverageThreshold='{"global":{"branches":80,"functions":80,"lines":80,"statements":80}}'
# vitest:
npx vitest run --coverage
```

## Test Patterns

### Unit Test (Jest)
```typescript
describe('increment', () => {
  it('should increase positive numbers', () => {
    expect(increment(1)).toBe(2);
  });

  it.each([
    [1, 2], [0, 1], [-1, 0]
  ])('increment(%i) = %i', (input, expected) => {
    expect(increment(input)).toBe(expected);
  });
});
```

### Property-Based (fast-check)
```typescript
import fc from 'fast-check';

test('increment always increases', () => {
  fc.assert(
    fc.property(fc.integer(), (x) => {
      if (x < Number.MAX_SAFE_INTEGER) {
        expect(increment(x)).toBeGreaterThan(x);
      }
    })
  );
});
```

### Async / API Tests
```typescript
it('should handle errors', async () => {
  await expect(fetchData('invalid')).rejects.toThrow('NotFound');
});
```

### Coverage Thresholds
- Lines: >= 80%
- Branches: >= 80%
- Functions: >= 80%
- Statements: >= 80%

<!-- advanced: mutation testing with stryker, e2e with playwright -->
