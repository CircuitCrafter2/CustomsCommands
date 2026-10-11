### CHAT CONFIGURATION ###

import copy
import json
import os
import re
import shutil
from endstone._internal.endstone_python import Player
from endstone.plugin import Plugin
from .security import migrate_permission, PERMISSION_PREFIX


prefix = "§l§f[§aCustoms§6Commands§f]§r >> "

# Commands provided by the plugin itself (not stored in the JSON, not editable in the UI).
BUILTIN_COMMANDS = ("commands", "resetcommands")

MANAGER_PERMISSION = PERMISSION_PREFIX + "manager"

# Settings stored in the JSON file ("settings" key). Edit them in the file, not in the UI.
DEFAULT_SETTINGS = {
    # Allow players to pass target selectors (@a, @e, ...) as command arguments.
    "allow_selectors": False,
    # Scan other plugins' .whl files for integrations (invasive, off by default).
    # The recommended way is for plugins to call register_execution/register_placeholder.
    "auto_discover_integrations": False,
}


def send_custom(player: Player, message: str):
    player.send_message(prefix + message)


def error_custom(player: Player, message: str):
    player.send_message(prefix + "§cError: " + message)


def require_manager(player: Player) -> bool:
    """Defensive permission check for every action that modifies the configuration."""
    if player.has_permission(MANAGER_PERMISSION):
        return True
    error_custom(player, "You don't have permission to manage commands.")
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

# Define the path to the JSON file
json_file_path = os.path.abspath("./config/command_manager.json")


class logger:
    def info(str: str):
        print(str)

    def error(str: str):
        print(str)


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
            data["settings"][key], changed = value, True
    # Permissions from before the rename (easyas.command.*) are migrated.
    for command in data["commands"].values():
        permissions = command.get("permissions", [])
        migrated = [migrate_permission(p) for p in permissions]
        if migrated != permissions:
            command["permissions"], changed = migrated, True
    return data, changed


# Function to read from the JSON file
def read_commands_config():
    try:
        with open(json_file_path, "r") as file:
            data = json.load(file)
        data, changed = _normalize(data)
        if changed:
            write_commands_config(data)
        return data
    except FileNotFoundError:
        logger.error(
            f"Error: Missing commands configuration file, generating a new one."
        )
        data = copy.deepcopy(default_data)
        write_commands_config(data)
        return data
    except json.JSONDecodeError:
        logger.error(f"Error: Failed to decode JSON from {json_file_path}.")
        # Keep the broken file so the admin can fix it instead of losing it.
        try:
            shutil.copyfile(json_file_path, json_file_path + ".bak")
            logger.error(f"A copy of the invalid file was saved as {json_file_path}.bak")
        except OSError:
            pass
        return copy.deepcopy(default_data)


# Function to write to the JSON file
def write_commands_config(data):
    try:
        os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
        with open(json_file_path, "w") as file:
            json.dump(data, file, indent=4)
    except IOError as e:
        logger.error(f"Error: Failed to write to {json_file_path}\n{e}")


def edit_commands_config(key, value):
    if not isinstance(key, str):
        logger.error("Error: Invalid key access in commands config.")
        return
    config = read_commands_config()
    config[key] = value
    write_commands_config(config)


def reset_commands(self: Plugin, player: Player):
    if not require_manager(player):
        return
    new_data = copy.deepcopy(default_data)
    new_data["settings"] = read_commands_config()["settings"]  # keep the admin's settings
    write_commands_config(new_data)
    self.logger.info("Commands configuration has been reset to default.")
    send_custom(
        player,
        f"§cReset Complete!\n§eServer has been reloaded successfully!",
    )
    try:
        self.server.reload()
    except Exception as e:
        error_custom(player, f"Failed to reload server: {e}")
        return


### EXTRA UTILITIES ###


def strip_color_codes(text: str) -> str:
    # Regular expression to match Minecraft color codes
    color_code_pattern = re.compile(r"§[0-9a-fk-or]")
    # Substitute the color codes with an empty string
    return color_code_pattern.sub("", text)
