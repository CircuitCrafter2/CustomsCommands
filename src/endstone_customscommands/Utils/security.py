"""
Input validation and safe command rendering.

Custom commands run on the *console* (full privileges). The values a player types
(`{0}`, `{1}`, ...) and values coming from third-party placeholders must therefore never be
able to change the structure of the command that gets executed.
"""

from __future__ import annotations

import re

### CONSTANTS ###

PERMISSION_PREFIX = "customscommands.command."
LEGACY_PERMISSION_PREFIX = "easyas.command."  # permissions used before the rename

NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,32}$")
PERMISSION_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")
PLACEHOLDER_RE = re.compile(r"\{([^{}]*)\}")
SELECTOR_RE = re.compile(r"(?:^|\s)@")
WHITESPACE_RE = re.compile(r"\s")

MAX_VALUE_LENGTH = 256
MAX_DESCRIPTION_LENGTH = 256
MAX_USAGE_LENGTH = 256


class InputError(ValueError):
    """Raised when an input is refused. The message is safe to show to the player."""


### GENERIC HELPERS ###


def has_control_chars(text: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in text)


def migrate_permission(permission: str) -> str:
    """Converts a permission from the old `easyas.command.*` namespace to the new one."""
    if isinstance(permission, str) and permission.startswith(LEGACY_PERMISSION_PREFIX):
        return PERMISSION_PREFIX + permission[len(LEGACY_PERMISSION_PREFIX) :]
    return permission


### ADMIN SIDE: VALIDATING A COMMAND DEFINITION ###


def validate_command(
    command: dict, existing: dict, builtin, original_name: str | None = None
) -> str | None:
    """
    Checks a command definition (name, description, usages, aliases, permissions).

    :param command: The command being saved.
    :param existing: The currently stored commands ({name: definition}).
    :param builtin: Names reserved by the plugin itself.
    :param original_name: Name the command had before editing (allows keeping/renaming it).
    :return: An error message, or None if the command is valid.
    """
    name = command.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name):
        return (
            "Invalid name: use 1-32 letters, digits or underscores "
            "(no spaces, no '/')."
        )
    aliases = command.get("aliases", [])
    if name.lower() in (b.lower() for b in builtin):
        return f"'{name}' is reserved by the plugin."

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
        return f"A command named '{name}' already exists."

    seen = {name.lower()}
    for alias in aliases:
        if not isinstance(alias, str) or not NAME_RE.match(alias):
            return f"Invalid alias '{alias}': use 1-32 letters, digits or underscores."
        if alias.lower() in taken or alias.lower() in seen:
            return f"The alias '{alias}' is already in use."
        seen.add(alias.lower())

    description = command.get("description", "")
    if (
        not isinstance(description, str)
        or has_control_chars(description)
        or len(description) > MAX_DESCRIPTION_LENGTH
    ):
        return "Invalid description (no line breaks, 256 characters max)."

    valid_names = {name.lower()} | {a.lower() for a in aliases}
    for usage in command.get("usages", []):
        if (
            not isinstance(usage, str)
            or not usage.startswith("/")
            or has_control_chars(usage)
            or len(usage) > MAX_USAGE_LENGTH
        ):
            return f"Invalid usage '{usage}': it must start with '/' and stay on one line."
        first = usage[1:].split(None, 1)[0].lower() if usage[1:].strip() else ""
        if first not in valid_names:
            return (
                f"Invalid usage '{usage}': it must start with '/{name}' "
                "(or one of the aliases)."
            )

    for permission in command.get("permissions", []):
        if not isinstance(permission, str) or not PERMISSION_RE.match(permission):
            return (
                f"Invalid permission '{permission}': use letters, digits, "
                "'_', '-' and '.' only."
            )
    return None


### PLAYER SIDE: RENDERING A COMMAND TEMPLATE SAFELY ###


def _check_template_start(template: str):
    """A placeholder must never be able to supply the command name itself."""
    stripped = template.lstrip().lstrip("/").lstrip()
    first = stripped.split(None, 1)[0] if stripped else ""
    if "{" in first:
        raise InputError(
            "This command is misconfigured: a placeholder can't be used as the command name."
        )


def _sanitize(value: str, kind: str, key: str, in_quotes: bool, allow_selectors: bool):
    if kind == "placeholder":
        label = f"'{key}'"
    elif kind == "argument":
        label = f"#{int(key) + 1}"
    else:
        label = "name"
    if len(value) > MAX_VALUE_LENGTH:
        raise InputError(f"Argument {label} is too long ({MAX_VALUE_LENGTH} characters max).")
    if has_control_chars(value):
        raise InputError(f"Argument {label} contains forbidden control characters.")
    if '"' in value or "\\" in value:
        raise InputError(f"Argument {label} can't contain quotes or backslashes.")
    if not allow_selectors and SELECTOR_RE.search(value):
        raise InputError(f"Argument {label} can't contain target selectors (@).")
    if WHITESPACE_RE.search(value) and not in_quotes:
        if kind == "player":
            return f'"{value}"'  # e.g. gamertags with spaces
        raise InputError(
            f"Argument {label} can't contain spaces here "
            "(the command author must put the placeholder between quotes)."
        )
    return value


def render_line(
    template: str,
    player_name: str,
    args: list,
    custom: dict,
    allow_selectors: bool = False,
    strict: bool = True,
) -> str:
    """
    Replaces {player}, {0}, {1}... and custom placeholders in a single pass.

    Values are never re-scanned for placeholders. In strict mode (used for server
    commands) every value is validated so it can't alter the command structure.

    :param custom: {placeholder id: zero-argument callable returning its value}
    :raises InputError: If a value is refused (strict mode only).
    """
    if strict:
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
                    raise InputError(f"Missing argument #{index + 1}.")
                return match.group(0)
            value, kind = str(args[index]), "argument"
        elif key in custom:
            value, kind = str(custom[key]()), "placeholder"
        else:
            return match.group(0)
        if not strict:
            return value
        return _sanitize(value, kind, key, in_quotes, allow_selectors)

    return PLACEHOLDER_RE.sub(replace, template)
