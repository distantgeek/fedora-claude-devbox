#!/usr/bin/env python3
"""
PostToolUse hook — scrub sensitive data from tool output before
it is injected into the Claude Code context window.

Replaces detected sensitive patterns with tagged placeholders so
Claude Code knows something was redacted without seeing the value.
"""

import sys
import json
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from patterns import scrub, load_hook_input, write_hook_output


def main():
    data = load_hook_input()
    if not data:
        # Nothing to scrub, pass through
        sys.exit(0)

    tool_output = data.get("tool_output", "")

    if not isinstance(tool_output, str):
        # Non-string output (e.g. structured data); pass through
        sys.exit(0)

    scrubbed, redactions = scrub(tool_output)

    if redactions:
        summary = ", ".join(set(redactions))
        notice = f"\n[Security hook scrubbed {len(redactions)} sensitive value(s): {summary}]\n"
        scrubbed = scrubbed + notice
        # Log to stderr for local visibility (not sent to Claude)
        print(f"[scrub_output] Redacted: {summary}", file=sys.stderr, flush=True)

    # Write scrubbed output back
    print(json.dumps({"tool_output": scrubbed}), flush=True)


if __name__ == "__main__":
    main()
