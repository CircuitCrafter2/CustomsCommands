from endstone._internal.endstone_python import Player
from endstone.plugin import Plugin
from ..Utils.utils import (
    BUILTIN_COMMANDS,
    read_commands_config,
    write_commands_config,
    send_custom,
    error_custom,
    require_manager,
)
from ..Utils.security import validate_command


def submit_command(self: Plugin, player: Player, command):
    if not require_manager(player):
        return
    if "name" not in command:
        error_custom(player, "Incomplete command: Property '§4name§c' is missing.")
        return
    if "description" not in command:
        command["description"] = "New command."
    if "usages" not in command:
        error_custom(player, "Incomplete command: Property '§4usages§c' is missing.")
        return
    if "aliases" not in command:
        error_custom(player, "Incomplete command: Property '§4aliases§c' is missing.")
        return
    if "permissions" not in command:
        error_custom(
            player, "Incomplete command: Property '§4permissions§c' is missing."
        )
        return
    command["name"] = str(command["name"]).strip().lstrip("/")
    if not command["name"]:
        error_custom(player, "Incomplete command: Property '§4name§c' is empty.")
        return
    # A command without any usage can't be registered: default to "/<name>".
    if not command["usages"]:
        command["usages"] = ["/" + command["name"]]

    commandData = read_commands_config()
    old_name = command.get("_original_name")
    error = validate_command(
        command, commandData["commands"], BUILTIN_COMMANDS, original_name=old_name
    )
    if error:
        error_custom(player, error)
        return

    # Renaming: remove the old entry and move its functionality to the new name.
    if old_name and old_name != command["name"]:
        commandData["commands"].pop(old_name, None)
        old_functions = commandData["functions"].pop(old_name, [])
        if old_functions:
            commandData["functions"][command["name"]] = old_functions + commandData[
                "functions"
            ].get(command["name"], [])
    commandData["commands"][command["name"]] = {
        "description": command["description"],
        "usages": command["usages"],
        "aliases": command["aliases"],
        "permissions": command["permissions"],
        "cooldown": command.get("cooldown", 0),
        "conditions": command.get("conditions", []),
    }
    write_commands_config(commandData)
    send_custom(
        player,
        f"§aCommand §f'§6{command['name']}§f' §ahas been saved.\n§eServer has been reloaded successfully!",
    )
    try:
        self.server.reload()
    except Exception as e:
        error_custom(player, f"Failed to reload server: {e}")
        return
