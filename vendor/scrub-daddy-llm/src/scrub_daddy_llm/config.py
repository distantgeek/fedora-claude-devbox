import json
import os
import sys

from .scrubbers.secrets import DEFAULT_RULES as SECRETS_RULES
from .scrubbers.pii import DEFAULT_RULES as PII_RULES

BUILTIN_RULES = SECRETS_RULES + PII_RULES

CONFIG_PATHS = [
    ("user", os.path.expanduser("~/.config/scrub-daddy-llm/config.json")),
    ("project", ".scrub-daddy.json"),
]

MAX_CONFIG_SIZE = 1024 * 1024


def _read_json_config(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(MAX_CONFIG_SIZE + 1)
            if len(content) > MAX_CONFIG_SIZE:
                return None
            return json.loads(content)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _merge_rules(base, overlay):
    indexed = {r["name"]: r for r in base}
    for rule in overlay:
        indexed[rule["name"]] = rule
    return list(indexed.values())


def load_rules(extra_paths=None):
    rules = list(BUILTIN_RULES)

    for label, path in CONFIG_PATHS:
        data = _read_json_config(path)
        if data and "rules" in data:
            rules = _merge_rules(rules, data["rules"])

    if extra_paths:
        for path in extra_paths:
            data = _read_json_config(path)
            if data and "rules" in data:
                rules = _merge_rules(rules, data["rules"])

    return rules
