"""
Input validation and safe command rendering.

Custom commands run on the *console* (full privileges). The values a player types
(`{0}`, `{1}`, ...) and values coming from third-party placeholders must therefore never be
able to change the structure of the command that gets executed.
"""

from __future__ import annotations

import math
import re

from .lang import t

### CONSTANTS ###

PERMISSION_PREFIX = "customscommands.command."
LEGACY_PERMISSION_PREFIX = "easyas.command."  # permissions used before the rename
CUSTOM_PERMISSION_PREFIX = "customscommands.custom."  # one specific node per command

NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,32}$")
PERMISSION_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")
PLACEHOLDER_RE = re.compile(r"\{([^{}]*)\}")
SELECTOR_RE = re.compile(r"(?:^|\s)@")
WHITESPACE_RE = re.compile(r"\s")

MAX_VALUE_LENGTH = 256
MAX_DESCRIPTION_LENGTH = 256
MAX_USAGE_LENGTH = 256
MAX_CONTENT_LENGTH = 512  # execution / condition content
MAX_COOLDOWN = 86400  # seconds
MAX_DELAY = 3600  # seconds
MAX_ARG_INDEX = 19
MAX_RULES = 20  # argument rules / conditions per list
MAX_CHOICES = 50
MAX_LIMIT_USES = 1_000_000
MAX_LIMIT_PERIOD = 31_536_000  # one year, in seconds
MAX_LINES = 50  # executions per command

COMPARATOR_RE = re.compile(r"^(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


class InputError(ValueError):
    """Raised when an input is refused. The message is safe to show to the player."""


class Unresolved(Exception):
    """Raised by a placeholder resolver that doesn't know the placeholder: it is left as is."""


### GENERIC HELPERS ###


def has_control_chars(text: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in text)


def specific_permission(command_name: str) -> str:
    """The specific permission node of a command, e.g. customscommands.custom.helloworld."""
    return CUSTOM_PERMISSION_PREFIX + command_name.lower()


def migrate_permission(permission: str) -> str:
    """Converts a permission from the old `easyas.command.*` namespace to the new one."""
    if isinstance(permission, str) and permission.startswith(LEGACY_PERMISSION_PREFIX):
        return PERMISSION_PREFIX + permission[len(LEGACY_PERMISSION_PREFIX) :]
    return permission


### ADMIN SIDE: VALIDATING A COMMAND DEFINITION ###


def _is_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _one_line(value, limit: int) -> bool:
    return isinstance(value, str) and not has_control_chars(value) and len(value) <= limit


def validate_command(
    command: dict, existing: dict, builtin, original_name: str | None = None
) -> str | None:
    """
    Checks a command definition (name, description, usages, aliases, permissions,
    cooldown, conditions, argument rules, usage limit).

    :param command: The command being saved.
    :param existing: The currently stored commands ({name: definition}).
    :param builtin: Names reserved by the plugin itself.
    :param original_name: Name the command had before editing (allows keeping/renaming it).
    :return: An error message, or None if the command is valid.
    """
    name = command.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name):
        return t("val.name_invalid")
    aliases = command.get("aliases", [])
    if name.lower() in (b.lower() for b in builtin):
        return t("val.name_reserved", name=name)

    # Names and aliases already used by other commands.
    taken = set()
    for other_name, other in existing.items():
        if other_name == original_name:
            continue
        taken.add(other_name.lower())
        for alias in other.get("aliases", []):
            taken.add(str(alias).lower())
    for builtin_name in builtin:
        taken.add(builtin_name.lower())

    if name.lower() in taken:
        return t("val.name_exists", name=name)

    seen = {name.lower()}
    for alias in aliases:
        if not isinstance(alias, str) or not NAME_RE.match(alias):
            return t("val.alias_invalid", alias=alias)
        if alias.lower() in taken or alias.lower() in seen:
            return t("val.alias_in_use", alias=alias)
        seen.add(alias.lower())

    if not _one_line(command.get("description", ""), MAX_DESCRIPTION_LENGTH):
        return t("val.description_invalid")

    valid_names = {name.lower()} | {a.lower() for a in aliases}
    for usage in command.get("usages", []):
        if (
            not isinstance(usage, str)
            or not usage.startswith("/")
            or has_control_chars(usage)
            or len(usage) > MAX_USAGE_LENGTH
        ):
            return t("val.usage_invalid", usage=usage)
        first = usage[1:].split(None, 1)[0].lower() if usage[1:].strip() else ""
        if first not in valid_names:
            return t("val.usage_name", usage=usage, name=name)

    for permission in command.get("permissions", []):
        if not isinstance(permission, str) or not PERMISSION_RE.match(permission):
            return t("val.permission_invalid", permission=permission)

    return validate_restrictions(command)


def validate_restrictions(command: dict) -> str | None:
    """Checks what limits a command: cooldown, conditions, argument rules, usage limit."""
    cooldown = command.get("cooldown", 0)
    if (
        isinstance(cooldown, bool)
        or not isinstance(cooldown, int)
        or not 0 <= cooldown <= MAX_COOLDOWN
    ):
        return t("val.cooldown_invalid", max=MAX_COOLDOWN)

    error = validate_condition_list(command.get("conditions", []))
    if error:
        return error

    rules = command.get("arguments", [])
    if not isinstance(rules, list) or len(rules) > MAX_RULES:
        return t("val.argument_invalid")
    for rule in rules:
        error = validate_argument_rule(rule)
        if error:
            return error

    if command.get("limit") is not None:
        return validate_limit(command["limit"])
    return None


def validate_argument_rule(rule) -> str | None:
    """A rule limits an argument: {"index": 0, "type": "choices", "values": [...]}
    or {"index": 1, "type": "range", "min": 1, "max": 16}, plus an optional "message"."""
    if not isinstance(rule, dict):
        return t("val.argument_invalid")
    index = rule.get("index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index <= MAX_ARG_INDEX:
        return t("val.argument_index", max=MAX_ARG_INDEX + 1)
    if rule.get("message") not in (None, "") and not _one_line(
        rule.get("message"), MAX_DESCRIPTION_LENGTH
    ):
        return t("val.argument_message")
    kind = rule.get("type")
    if kind == "choices":
        values = rule.get("values")
        if (
            not isinstance(values, list)
            or not 1 <= len(values) <= MAX_CHOICES
            or not all(
                isinstance(v, str) and v.strip() and _one_line(v, 64) for v in values
            )
        ):
            return t("val.argument_choices", max=MAX_CHOICES)
        return None
    if kind == "range":
        low, high = rule.get("min"), rule.get("max")
        if not (_is_number(low) and _is_number(high) and low <= high):
            return t("val.argument_range")
        return None
    return t("val.argument_invalid")


def validate_limit(limit) -> str | None:
    """A usage limit: {"uses": 3, "period": 86400} (period 0 = forever)."""
    if not isinstance(limit, dict):
        return t("val.limit_invalid", max_uses=MAX_LIMIT_USES, max_period=MAX_LIMIT_PERIOD)
    uses, period = limit.get("uses"), limit.get("period", 0)
    if (
        isinstance(uses, bool)
        or not isinstance(uses, int)
        or not 1 <= uses <= MAX_LIMIT_USES
        or isinstance(period, bool)
        or not isinstance(period, int)
        or not 0 <= period <= MAX_LIMIT_PERIOD
    ):
        return t("val.limit_invalid", max_uses=MAX_LIMIT_USES, max_period=MAX_LIMIT_PERIOD)
    return None


### ARGUMENT RULES (checked when a player uses the command) ###


def check_arguments(rules, args) -> None:
    """Raises InputError if an argument breaks a rule. Missing arguments are skipped."""
    for rule in rules or []:
        index = rule["index"]
        if index >= len(args):
            continue
        value = str(args[index]).strip()
        custom_message = rule.get("message") or None
        if rule["type"] == "choices":
            if value.casefold() not in (v.strip().casefold() for v in rule["values"]):
                raise InputError(
                    custom_message
                    or t("err.arg_choice", n=index + 1, values=", ".join(rule["values"]))
                )
        elif rule["type"] == "range":
            try:
                number = float(value)
            except ValueError:
                number = math.nan
            if not math.isfinite(number):
                raise InputError(custom_message or t("err.arg_number", n=index + 1))
            if not rule["min"] <= number <= rule["max"]:
                raise InputError(
                    custom_message
                    or t("err.arg_range", n=index + 1, min=rule["min"], max=rule["max"])
                )


### CONDITIONS & EXECUTIONS ###


def parse_expression(text: str):
    """Splits 'left <op> right' (op in ==, !=, >=, <=, >, <). Raises InputError."""
    match = COMPARATOR_RE.match(text.strip())
    if not match:
        raise InputError(t("val.expression_invalid"))
    return match.group(1).strip(), match.group(2), match.group(3).strip()


def compare_values(left: str, op: str, right: str) -> bool:
    """Numeric comparison when both sides are numbers, text comparison otherwise."""
    try:
        a, b = float(left), float(right)
        if not (math.isfinite(a) and math.isfinite(b)):
            raise ValueError  # "nan" / "inf" are text, not numbers
    except ValueError:
        if op in ("==", "!="):
            equal = left.strip().casefold() == right.strip().casefold()
            return equal if op == "==" else not equal
        raise InputError(t("err.compare_text"))
    return {
        "==": a == b,
        "!=": a != b,
        ">=": a >= b,
        "<=": a <= b,
        ">": a > b,
        "<": a < b,
    }[op]


def validate_condition(condition) -> str | None:
    if not isinstance(condition, dict):
        return t("val.condition_invalid")
    ctype = condition.get("type")
    content = condition.get("content")
    message = condition.get("message", "")
    if not isinstance(ctype, str) or not NAME_RE.match(ctype):
        return t("val.condition_type_invalid")
    if (
        not isinstance(content, str)
        or not content.strip()
        or not _one_line(content, MAX_DESCRIPTION_LENGTH)
    ):
        return t("val.condition_content_invalid")
    if not _one_line(message, MAX_DESCRIPTION_LENGTH):
        return t("val.condition_message_invalid")
    if ctype == "permission" and not PERMISSION_RE.match(content.strip()):
        return t("val.condition_permission_invalid", content=content)
    if ctype == "expression":
        try:
            parse_expression(content)
        except InputError as e:
            return str(e)
    return None


def validate_condition_list(conditions) -> str | None:
    if not isinstance(conditions, list) or len(conditions) > MAX_RULES:
        return t("val.condition_invalid")
    for condition in conditions:
        error = validate_condition(condition)
        if error:
            return error
    return None


def validate_execution_content(type_name: str, content) -> str | None:
    """Checks the content of an execution line when it is saved."""
    if not isinstance(content, str) or not content.strip():
        return t("val.content_empty")
    if has_control_chars(content) or len(content) > MAX_CONTENT_LENGTH:
        return t("val.content_single_line")
    if type_name == "delay":
        try:
            seconds = float(content)
        except ValueError:
            return t("val.delay_number")
        if not math.isfinite(seconds) or not 0 <= seconds <= MAX_DELAY:
            return t("val.delay_range", max=MAX_DELAY)
    from ..API.types import ExecutionTypes  # here to avoid a circular import

    validator = ExecutionTypes.get_validator(type_name)
    if validator is not None:
        return validator(content)
    return None


def validate_function_line(line) -> str | None:
    """One execution line: {"type", "content", optional "conditions"}."""
    if not isinstance(line, dict):
        return t("val.line_invalid")
    ltype = line.get("type")
    if not isinstance(ltype, str) or not NAME_RE.match(ltype):
        return t("val.line_invalid")
    error = validate_execution_content(ltype, line.get("content"))
    if error:
        return error
    return validate_condition_list(line.get("conditions", []))


### PLAYER SIDE: RENDERING A COMMAND TEMPLATE SAFELY ###


def _check_template_start(template: str):
    """A placeholder must never be able to supply the command name itself."""
    stripped = template.lstrip().lstrip("/").lstrip()
    first = stripped.split(None, 1)[0] if stripped else ""
    if "{" in first:
        raise InputError(t("err.placeholder_command_name"))


def _sanitize(value: str, kind: str, key: str, in_quotes: bool, allow_selectors: bool):
    value = value.replace("§", "")
    if kind == "placeholder":
        label = f"'{key}'"
    elif kind == "argument":
        label = f"#{int(key) + 1}"
    else:
        label = "name"
    if len(value) > MAX_VALUE_LENGTH:
        raise InputError(t("err.arg_too_long", label=label, max=MAX_VALUE_LENGTH))
    if has_control_chars(value):
        raise InputError(t("err.arg_control", label=label))
    if '"' in value or "\\" in value:
        raise InputError(t("err.arg_quotes", label=label))
    if not allow_selectors and SELECTOR_RE.search(value):
        raise InputError(t("err.arg_selector", label=label))
    if WHITESPACE_RE.search(value) and not in_quotes:
        if kind == "player":
            return f'"{value}"'  # e.g. gamertags with spaces
        raise InputError(t("err.arg_spaces", label=label))
    return value


def render_line(
    template: str,
    player_name: str,
    args: list,
    custom: dict,
    allow_selectors: bool = False,
    strict: bool = True,
    strip_formatting: bool = False,
    check_start: bool = True,
) -> str:
    """
    Replaces {player}, {0}, {1}... and custom placeholders in a single pass.

    Values are never re-scanned for placeholders. In strict mode (used for server
    commands) every value is validated so it can't alter the command structure.

    :param custom: {placeholder id: zero-argument callable returning its value}
    :raises InputError: If a value is refused (strict mode only).
    """
    if strict and check_start:
        _check_template_start(template)

    def replace(match: re.Match) -> str:
        key = match.group(1)
        in_quotes = template.count('"', 0, match.start()) % 2 == 1
        if key == "player":
            value, kind = player_name, "player"
        elif key.isdigit():
            index = int(key)
            if index >= len(args):
                if strict:
                    raise InputError(t("err.arg_missing", n=index + 1))
                return match.group(0)
            value, kind = str(args[index]), "argument"
        elif key in custom:
            try:
                value, kind = str(custom[key]()), "placeholder"
            except Unresolved:
                return match.group(0)
        else:
            return match.group(0)
        if not strict:
            return value.replace("§", "") if strip_formatting else value
        return _sanitize(value, kind, key, in_quotes, allow_selectors)

    return PLACEHOLDER_RE.sub(replace, template)
