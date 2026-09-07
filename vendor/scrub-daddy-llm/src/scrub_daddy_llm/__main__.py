#!/usr/bin/env python3
import sys
import json

from .engine import scrub
from .config import load_rules
from . import __version__


def main():
    extra_paths = []
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(
            "scrub-daddy-llm — redact secrets and PII from piped text", file=sys.stderr
        )
        print(f"  version {__version__}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  cat dirty.txt | scrub-daddy-llm > clean.txt", file=sys.stderr)
        print("  some-tool 2>&1 | scrub-daddy-llm", file=sys.stderr)
        print("  scrub-daddy-llm --rules custom.json < input.txt", file=sys.stderr)
        print("", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  --rules PATH   Add extra config file (repeatable)", file=sys.stderr)
        print("  --version      Print version and exit", file=sys.stderr)
        sys.exit(0)

    if "--version" in args or "-V" in args:
        print(f"scrub-daddy-llm {__version__}", file=sys.stderr)
        sys.exit(0)

    i = 0
    while i < len(args):
        if args[i] == "--rules" and i + 1 < len(args):
            extra_paths.append(args[i + 1])
            i += 2
        else:
            i += 1

    try:
        rules = load_rules(extra_paths)

        text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        if not text:
            text = sys.stdin.read()

        cleaned = scrub(text, rules)

        sys.stdout.write(cleaned)
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
