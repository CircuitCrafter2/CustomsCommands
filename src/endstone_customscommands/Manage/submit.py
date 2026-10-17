from ..Utils.lang import t
from ..compat import Player
from endstone.plugin import Plugin
from ..Utils.utils import (
    BUILTIN_COMMANDS,
    read_commands_config,
    write_commands_config,
    send_custom,
    error_custom,
    require_manager,
)
from ..Utils.usage import USAGE
from ..Utils.security import specific_permission, validate_command


def rename_usage(usage: str, old_name: str, new_name: str) -> str:
    """'/old <a: int>' -> '/new <a: int>' (other usages are left untouched)."""
    if usage.startswith("/"):
        first = usage[1:].split(None, 1)[0] if usage[1:].strip() else ""
        if first.lower() == old_name.lower():
            return "/" + new_name + usage[1 + len(first) :]
    return usage


def submit_command(self: Plugin, player: Player, command):
    if not require_manager(player):
        return
    if "name" not in command:
        error_custom(player, t("err.incomplete_name_missing"))
        return
    if "description" not in command:
        command["description"] = "New command."
    if "usages" not in command:
        error_custom(player, t("err.incomplete_usages"))
        return
    if "aliases" not in command:
        error_custom(player, t("err.incomplete_aliases"))
        return
    if "permissions" not in command:
        error_custom(
            player, t("err.incomplete_permissions")
        )
        return
    command["name"] = str(command["name"]).strip().lstrip("/")
    if not command["name"]:
        error_custom(player, t("err.incomplete_name_empty"))
        return
    # A command without any usage can't be registered: default to "/<name>".
    if not command["usages"]:
        command["usages"] = ["/" + command["name"]]

    commandData = read_commands_config()
    old_name = command.get("_original_name")
    # Renaming: the usages and the command's specific permission follow its new name.
    if old_name and old_name.lower() != command["name"].lower():
        command["usages"] = [
            rename_usage(u, old_name, command["name"]) for u in command["usages"]
        ]
        old_node = specific_permission(old_name)
        if old_node in command["permissions"]:
            command["permissions"] = [
                specific_permission(command["name"]) if p == old_node else p
                for p in command["permissions"]
            ]
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
        "arguments": command.get("arguments", []),
    }
    if command.get("limit"):
        commandData["commands"][command["name"]]["limit"] = command["limit"]
    if old_name and old_name != command["name"]:
        USAGE.rename(old_name, command["name"])
    write_commands_config(commandData)
    send_custom(player, t("msg.command_saved", name=command["name"]))
    try:
        self.server.reload()
    except Exception as e:
        error_custom(player, t("err.reload_failed", error=e))
        return
