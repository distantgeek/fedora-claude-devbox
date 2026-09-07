# Ponytail Mode — Lazy-Senior YAGNI (Default)

You operate in **ponytail mode** by default. This is a mandatory engineering-discipline directive.

## The Ladder

Write the minimum code that solves the stated problem. Climb the ladder one rung at a time, only when a test or requirement forces you higher:

1. **Hardcode / inline** — a literal value, a single function, no abstraction.
2. **Extract** — only when the same logic appears a second time.
3. **Parameterize** — only when a real second caller exists.
4. **Abstract / interface** — only when two concrete implementations exist.
5. **Framework / generic** — almost never. Resist until evidence is overwhelming.

## Rules

1. **YAGNI** — do not build for hypothetical future requirements.
2. **No speculative generality** — no "just in case" interfaces, config knobs, or plugin points.
3. **Refuse to guess** — if a requirement is ambiguous, ask; do not invent one.
4. **Do the simplest thing that works** — then stop. Passing tests are the finish line.
5. **Small diffs** — prefer small, reviewable changes over large rewrites.

## Exception

Explicit user instruction overrides this. If the user asks for a specific abstraction, design, or "production-grade" structure, provide it. Otherwise, default to lazy-senior minimalism.
