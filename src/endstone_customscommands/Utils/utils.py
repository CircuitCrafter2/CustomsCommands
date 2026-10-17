from __future__ import annotations

### CHAT CONFIGURATION ###

import copy
import json
import os
import re
import shutil
import time
from ..compat import Player
from endstone.plugin import Plugin
from . import paths
from .lang import t
from .security import CUSTOM_PERMISSION_PREFIX, migrate_permission, PERMISSION_PREFIX


# Commands provided by the plugin itself (not stored in the JSON, not editable in the UI).
BUILTIN_COMMANDS = ("commands", "resetcommands", "ccreload")

MANAGER_PERMISSION = PERMISSION_PREFIX + "manager"
COOLDOWN_BYPASS_PERMISSION = "customscommands.cooldown.bypass"
LIMIT_BYPASS_PERMISSION = "customscommands.limit.bypass"

# Settings of the optional dependencies (config.json -> "integrations").
# The command templates of MediaPlayer are a best guess of its /mpm syntax: check /help mpm.
DEFAULT_INTEGRATIONS = {
    "papi": {"enabled": True},
    "stoneperms": {"enabled": True},
    "mediaplayer": {
        "enabled": True,
        "run_as": "player",
        "commands": {
            "play": "mpm play {song}",
            "pause": "mpm pause",
            "resume": "mpm resume",
            "stop": "mpm stop",
        },
    },
}
TEMPLATE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_\-]{0,31}( [A-Za-z0-9_\-{}.]{1,40}){0,6}$")
TEMPLATE_PLACEHOLDERS = {"song"}

# Settings stored in config.json. Edit them in the file, not in the UI.
DEFAULT_SETTINGS = {
    # Language file used for every message and UI text (lang/<language>.json).
    "language": "en_US",
    # Number of commands shown per page in the manager.
    "page_size": 8,
    # Allow players to pass target selectors (@a, @e, ...) as command arguments.
    "allow_selectors": False,
    # Scan other plugins' .whl files for integrations (invasive, off by default).
    # The recommended way is for plugins to call register_execution/register_placeholder.
    "auto_discover_integrations": False,
    # Who has the specific permissions (customscommands.custom.<command>) by default:
    # "op" (only operators, then grant it with a permissions plugin) or "everyone".
    "custom_permission_default": "op",
    # Optional dependencies: StonePerms, MediaPlayer, PlaceholderAPI.
    "integrations": DEFAULT_INTEGRATIONS,
}

CUSTOM_PERMISSION_DEFAULTS = ("op", "everyone")
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(_[A-Za-z0-9]{2,4})?$")
PAGE_SIZE_RANGE = (3, 20)
MAX_BACKUPS = 20


def send_custom(player: Player, message: str):
    player.send_message(t("prefix") + message)


def error_custom(player: Player, message: str):
    player.send_message(t("prefix") + t("error_label") + message)


def format_duration(seconds: int) -> str:
    """90061 -> '1d 1h 1m 1s' (units that are 0 are left out)."""
    seconds = int(seconds)
    parts = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        amount, seconds = divmod(seconds, size)
        if amount:
            parts.append(f"{amount}{unit}")
    return " ".join(parts) or "0s"


def require_manager(player: Player) -> bool:
    """Defensive permission check for every action that modifies the configuration."""
    if player.has_permission(MANAGER_PERMISSION):
        return True
    error_custom(player, t("err.no_manager_permission"))
    return False


### DEFAULT COMMAND DATA CONFIGURATION ###

default_data = {
    "settings": dict(DEFAULT_SETTINGS),
    "commands": {
        "helloworld": {
            "description": "Example command.",
            "usages": ["/helloworld <message: str> <amount: int>"],
            "aliases": ["hello", "hi"],
            "permissions": ["customscommands.command.all"],
        }
    },
    "functions": {
        "helloworld": [
            {"type": "command", "content": "say Hello, {0}!"},
            {"type": "command", "content": 'give "{player}" diamond {1}'},
        ]
    },
}

### COMMAND CONFIGURATION MANAGEMENT ###

class logger:
    def info(str: str):
        print(str)

    def error(str: str):
        print(str)


def _template_ok(template) -> bool:
    if not isinstance(template, str) or not TEMPLATE_RE.match(template):
        return False
    return set(re.findall(r"\{([^{}]*)\}", template)) <= TEMPLATE_PLACEHOLDERS


def _normalize_integrations(settings: dict) -> bool:
    """Makes settings["integrations"] valid. Returns True if something was fixed."""
    changed = False
    integrations = settings.get("integrations")
    if not isinstance(integrations, dict):
        integrations, changed = {}, True
    for name, defaults in DEFAULT_INTEGRATIONS.items():
        entry = integrations.get(name)
        if not isinstance(entry, dict):
            entry, changed = {}, True
        if not isinstance(entry.get("enabled"), bool):
            entry["enabled"], changed = defaults["enabled"], True
        if "run_as" in defaults and entry.get("run_as") not in ("player", "console"):
            entry["run_as"], changed = defaults["run_as"], True
        if "commands" in defaults:
            commands = entry.get("commands")
            if not isinstance(commands, dict):
                commands, changed = {}, True
            for action, template in defaults["commands"].items():
                if not _template_ok(commands.get(action)):
                    commands[action], changed = template, True
            entry["commands"] = commands
        integrations[name] = entry
    settings["integrations"] = integrations
    return changed


def _normalize(data):
    """Makes sure the mandatory keys exist. Returns (data, changed)."""
    changed = False
    if not isinstance(data, dict):
        data, changed = {}, True
    for key in ("commands", "functions"):
        if not isinstance(data.get(key), dict):
            data[key], changed = {}, True
    if not isinstance(data.get("settings"), dict):
        data["settings"], changed = {}, True
    for key, value in DEFAULT_SETTINGS.items():
        if key not in data["settings"]:
            data["settings"][key], changed = copy.deepcopy(value), True
    if _normalize_integrations(data["settings"]):
        changed = True
    if data["settings"]["custom_permission_default"] not in CUSTOM_PERMISSION_DEFAULTS:
        data["settings"]["custom_permission_default"], changed = "op", True
    language = data["settings"]["language"]
    if not isinstance(language, str) or not LANGUAGE_RE.match(language):
        data["settings"]["language"], changed = DEFAULT_SETTINGS["language"], True
    page_size = data["settings"]["page_size"]
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not PAGE_SIZE_RANGE[0] <= page_size <= PAGE_SIZE_RANGE[1]
    ):
        data["settings"]["page_size"], changed = DEFAULT_SETTINGS["page_size"], True
    # Permissions from before the rename (easyas.command.*) are migrated.
    for command in data["commands"].values():
        permissions = command.get("permissions", [])
        migrated = [migrate_permission(p) for p in permissions]
        if migrated != permissions:
            command["permissions"], changed = migrated, True
    return data, changed


def custom_permission_declarations(commands: dict, settings: dict) -> dict:
    """
    Endstone permission declarations for every specific node (customscommands.custom.*)
    used by a command. An undeclared permission has an unpredictable default, so they
    are declared with the default chosen in settings.custom_permission_default.
    """
    default = True if settings.get("custom_permission_default") == "everyone" else "op"
    declarations = {}
    for definition in commands.values():
        for permission in definition.get("permissions", []):
            if isinstance(permission, str) and permission.startswith(
                CUSTOM_PERMISSION_PREFIX
            ):
                declarations[permission] = {
                    "description": "Specific permission of a custom command.",
                    "default": default,
                }
    return declarations


def _write_json(path, content) -> None:
    """Atomic write: the file is never left half-written."""
    path = os.fspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(content, file, indent=4, ensure_ascii=False)
    os.replace(temporary, path)


def _load_json(path):
    """Returns (data, status) with status None, "missing" or "invalid"."""
    path = os.fspath(path)
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file), None
    except FileNotFoundError:
        return None, "missing"
    except (ValueError, OSError):
        logger.error(f"Error: Failed to decode JSON from {path}.")
        # Keep the broken file so the admin can fix it instead of losing it.
        try:
            shutil.copyfile(path, path + ".bak")
            logger.error(f"A copy of the invalid file was saved as {path}.bak")
        except OSError:
            pass
        return None, "invalid"


def _migrate_legacy() -> None:
    """Moves the old config/command_manager.json into the data folder (once)."""
    legacy = paths.legacy_config_file()
    if paths.file("commands.json").exists() or not os.path.exists(legacy):
        return
    data, status = _load_json(legacy)
    if status is not None:
        return
    data, _ = _normalize(data)
    write_commands_config(data)
    try:
        os.replace(legacy, legacy + ".migrated")
    except OSError:
        pass
    logger.info(
        f"Configuration migrated from {legacy} to {paths.data_dir()} "
        f"(the old file was renamed to command_manager.json.migrated)."
    )


# Function to read the configuration (settings + commands + executions)
def read_commands_config():
    _migrate_legacy()
    settings, settings_status = _load_json(paths.file("config.json"))
    stored, commands_status = _load_json(paths.file("commands.json"))
    if commands_status == "missing":
        logger.error("Error: Missing commands file, generating a new one.")
        stored = copy.deepcopy(default_data)
    elif commands_status == "invalid":
        stored = copy.deepcopy(default_data)
    if not isinstance(stored, dict):
        stored = {}
    data = {
        "settings": settings if isinstance(settings, dict) else {},
        "commands": stored.get("commands"),
        "functions": stored.get("functions"),
    }
    data, changed = _normalize(data)
    broken = "invalid" in (settings_status, commands_status)
    if not broken and (
        changed or "missing" in (settings_status, commands_status)
    ):
        write_commands_config(data)
    return data


# Function to write the configuration
def write_commands_config(data):
    try:
        if "settings" in data:
            _write_json(paths.file("config.json"), data["settings"])
        _write_json(
            paths.file("commands.json"),
            {
                "commands": data.get("commands", {}),
                "functions": data.get("functions", {}),
            },
        )
    except OSError as e:
        logger.error(f"Error: Failed to write to {paths.data_dir()}\n{e}")


def backup_commands(reason: str) -> str | None:
    """Saves the current commands in backups/ (keeps the last MAX_BACKUPS)."""
    data = read_commands_config()
    name = f"commands-{time.strftime('%Y%m%d-%H%M%S')}-{reason}.json"
    path = paths.file("backups", name)
    try:
        _write_json(path, {"commands": data["commands"], "functions": data["functions"]})
        existing = sorted(p for p in path.parent.glob("commands-*.json"))
        for old in existing[:-MAX_BACKUPS]:
            old.unlink()
    except OSError as e:
        logger.error(f"Error: Failed to write backup: {e}")
        return None
    return name


def reset_commands(self: Plugin, player: Player):
    """/resetcommands: asks for confirmation first (a backup is made automatically)."""
    if not require_manager(player):
        return
    from ..form_wrapper import MessageFormData, MessageFormResponse

    form = MessageFormData()
    form.title(t("ui.title.confirm_reset"))
    form.body(t("ui.body.confirm_reset"))
    form.button1(t("ui.button.yes_reset"))
    form.button2(t("ui.button.no_cancel"))

    def answer(self: Plugin, player: Player, result: MessageFormResponse):
        if result.canceled or result.selection != 0:
            return
        perform_reset(self, player)

    form.show(player).then(
        lambda player=Player, response=MessageFormResponse: answer(self, player, response)
    )


def perform_reset(self: Plugin, player: Player):
    if not require_manager(player):
        return
    backup = backup_commands("reset")
    new_data = copy.deepcopy(default_data)
    new_data["settings"] = read_commands_config()["settings"]  # keep the admin's settings
    write_commands_config(new_data)
    self.logger.info("Commands configuration has been reset to default.")
    send_custom(player, t("msg.reset_complete", backup=backup or "-"))
    try:
        self.server.reload()
    except Exception as e:
        error_custom(player, t("err.reload_failed", error=e))
        return


### EXTRA UTILITIES ###


def strip_color_codes(text: str) -> str:
    # Regular expression to match Minecraft color codes
    color_code_pattern = re.compile(r"§[0-9a-fk-or]")
    # Substitute the color codes with an empty string
    return color_code_pattern.sub("", text)
