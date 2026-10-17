"""Export and import of commands (files in the exports/ folder)."""

import json
import os
import time

from . import paths
from .lang import t
from .security import (
    MAX_LINES,
    migrate_permission,
    validate_command,
    validate_function_line,
)
from .utils import (
    BUILTIN_COMMANDS,
    _write_json,
    read_commands_config,
)

EXPORT_FORMAT = "customscommands-export"
EXPORT_VERSION = 1
MAX_IMPORT_BYTES = 2_000_000
MAX_LISTED_FILES = 100
COMMAND_KEYS = (
    "description",
    "usages",
    "aliases",
    "permissions",
    "cooldown",
    "conditions",
    "arguments",
    "limit",
)
MODES = ("add", "overwrite", "replace")


class TransferError(ValueError):
    """A problem with an export file. The message is safe to show to the admin."""


def export_all() -> str:
    """Writes every command and execution to exports/ and returns the file name."""
    data = read_commands_config()
    name = f"export-{time.strftime('%Y%m%d-%H%M%S')}.json"
    _write_json(
        paths.file("exports", name),
        {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "commands": data["commands"],
            "functions": data["functions"],
        },
    )
    return name


def list_files() -> list:
    """Files that can be imported (newest first). Also lists backups made by the plugin."""
    names = []
    for folder in ("exports", "backups"):
        directory = paths.file(folder)
        if directory.is_dir():
            names += [
                f"{folder}/{p.name}"
                for p in directory.glob("*.json")
                if p.is_file() and not p.name.endswith(".tmp")
            ]
    names.sort(key=lambda n: (paths.file(*n.split("/")).stat().st_mtime, n), reverse=True)
    return names[:MAX_LISTED_FILES]


def read_file(listed_name: str) -> dict:
    """Reads one of the files returned by list_files() (nothing else can be read)."""
    if listed_name not in list_files():
        raise TransferError(t("import.file_missing"))
    path = paths.file(*listed_name.split("/"))
    try:
        if os.path.getsize(path) > MAX_IMPORT_BYTES:
            raise TransferError(t("import.file_too_big"))
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        if isinstance(e, TransferError):
            raise
        raise TransferError(t("import.file_invalid"))
    if not isinstance(raw, dict) or not isinstance(raw.get("commands"), dict):
        raise TransferError(t("import.file_invalid"))
    if not isinstance(raw.get("functions", {}), dict):
        raise TransferError(t("import.file_invalid"))
    return raw


def plan_import(current: dict, raw: dict, mode: str, known_types) -> dict:
    """
    Validates every command of `raw` and merges the valid ones into `current`.

    mode "add": existing commands are kept, "overwrite": they are replaced,
    "replace": everything is replaced by the file's content.
    Returns {"commands", "functions", "imported": [names], "skipped": [(name, reason)]}.
    """
    if mode not in MODES:
        raise TransferError(t("import.file_invalid"))
    commands = {} if mode == "replace" else dict(current["commands"])
    functions = {} if mode == "replace" else dict(current["functions"])
    imported, skipped = [], []
    types = set(known_types) | {"command"}

    for name, definition in raw["commands"].items():
        if not isinstance(definition, dict):
            skipped.append((name, t("import.reason_invalid")))
            continue
        if mode == "add" and name in commands:
            skipped.append((name, t("import.reason_exists")))
            continue
        clean = {k: v for k, v in definition.items() if k in COMMAND_KEYS}
        clean.setdefault("description", "")
        clean.setdefault("usages", [f"/{name}"] if isinstance(name, str) else [])
        clean.setdefault("aliases", [])
        clean["permissions"] = [
            migrate_permission(p) for p in clean.get("permissions", []) if isinstance(p, str)
        ]
        for optional in ("limit",):
            if clean.get(optional) is None:
                clean.pop(optional, None)
        error = validate_command({"name": name, **clean}, commands, BUILTIN_COMMANDS, original_name=name)
        if error:
            skipped.append((name, error))
            continue

        lines = raw.get("functions", {}).get(name, [])
        if not isinstance(lines, list) or len(lines) > MAX_LINES:
            skipped.append((name, t("import.reason_lines")))
            continue
        cleaned_lines, line_error = [], None
        for line in lines:
            line_error = validate_function_line(line)
            if line_error is None and line["type"] not in types:
                line_error = t("import.reason_type", type=line["type"])
            if line_error:
                break
            cleaned = {"type": line["type"], "content": line["content"]}
            if line.get("conditions"):
                cleaned["conditions"] = line["conditions"]
            cleaned_lines.append(cleaned)
        if line_error:
            skipped.append((name, line_error))
            continue

        commands[name] = clean
        if cleaned_lines:
            functions[name] = cleaned_lines
        else:
            functions.pop(name, None)
        imported.append(name)

    return {"commands": commands, "functions": functions, "imported": imported, "skipped": skipped}
