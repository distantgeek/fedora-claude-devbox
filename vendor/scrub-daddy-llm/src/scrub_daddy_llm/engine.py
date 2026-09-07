import re
import sys

FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "VERBOSE": re.VERBOSE,
}

MAX_TEXT_SIZE = 10 * 1024 * 1024
RE_TIMEOUT = 5


def _compile_flags(flags):
    result = 0
    for f in flags:
        if f in FLAG_MAP:
            result |= FLAG_MAP[f]
    return result


def scrub(text, rules):
    if not text:
        return text

    if not isinstance(text, str):
        return text

    if len(text) > MAX_TEXT_SIZE:
        return text

    for rule in rules:
        if not rule.get("enabled", True):
            continue

        pattern = rule.get("pattern")
        if not pattern:
            continue

        replacement = rule.get("replacement", "***REDACTED***")
        flags = _compile_flags(rule.get("flags", []))

        try:
            text = re.sub(pattern, replacement, text, count=0, flags=flags)
        except re.error:
            sys.stderr.write(
                f"[scrub-daddy-llm] invalid pattern: {rule.get('name', 'unknown')}\n"
            )
        except TimeoutError:
            sys.stderr.write(
                f"[scrub-daddy-llm] pattern timeout: {rule.get('name', 'unknown')}\n"
            )
        except RecursionError:
            sys.stderr.write(
                f"[scrub-daddy-llm] pattern recursion: {rule.get('name', 'unknown')}\n"
            )

    return text
