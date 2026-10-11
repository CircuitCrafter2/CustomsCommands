from endstone._internal.endstone_python import (
    Player,
)
import json
import os

from .form_wrapper import (
    ActionFormData,
    ActionFormResponse,
    MessageFormData,
    MessageFormResponse,
)
from .Manage.add import add_command
from .Manage.edit import edit_command
from .Utils.utils import (
    BUILTIN_COMMANDS,
    read_commands_config,
    write_commands_config,
    send_custom,
    error_custom,
    require_manager,
)

from endstone.plugin import Plugin

### COMMAND MANAGER FUNCTIONALITY ###


def editable_commands(commandData):
    """Commands shown in the manager (the plugin's own commands are hidden)."""
    return {
        name: cmd
        for name, cmd in commandData["commands"].items()
        if name not in BUILTIN_COMMANDS
    }


def command_manager(self: Plugin, player: Player):
    if not require_manager(player):
        return
    commandData = read_commands_config()
    commands = editable_commands(commandData)
    form = ActionFormData()
    form.title("Command Manager")
    form.body("Click a command to edit it.")
    form.button("Add Command", "textures/ui/smithing-table-plus.png")
    form.button("Remove Command", "textures/ui/dark_minus.png")
    names = list(commands.keys())
    for command_name in names:
        command = commands[command_name]
        form.button(
            f"{command_name}\n{command['description']}",
            "textures/ui/user_icon_white.png",
        )

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        if result.canceled:
            return
        if result.selection == 0:
            add_command(self, player, {"usages": [], "aliases": [], "permissions": []})
        elif result.selection == 1:
            remove_command(self, player)
        else:
            cmdName = names[result.selection - 2]
            command = commands[cmdName]
            # Copy the lists so that cancelling an edit doesn't alter the stored data.
            edit_command(
                self,
                player,
                {
                    "name": cmdName,
                    "_original_name": cmdName,
                    "description": command["description"],
                    "usages": list(command["usages"]),
                    "aliases": list(command["aliases"]),
                    "permissions": list(command["permissions"]),
                },
            )

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response
        )
    )


def remove_command(self: Plugin, player: Player):
    commandData = read_commands_config()
    commands = editable_commands(commandData)
    names = list(commands.keys())
    form = ActionFormData()
    form.title("Remove Command")
    form.body("Click a command to remove it.")
    for command_name in names:
        command = commands[command_name]
        form.button(
            f"{command_name}\n§7{command['description']}",
            "textures/ui/user_icon_white.png",
        )

    def submit(self: Plugin, player: Player, result: ActionFormResponse):
        if result.canceled:
            return
        confirm_remove_command(self, player, names[result.selection])

    form.show(player).then(
        lambda player=Player, response=ActionFormResponse: submit(
            self, player, response
        )
    )


def confirm_remove_command(self: Plugin, player: Player, command_name: str):
    form = MessageFormData()
    form.title("Confirm Removal")
    form.body(f"Are you sure you want to remove '{command_name}'?")
    form.button1("Yes")
    form.button2("No")

    def do_remove(self: Plugin, player: Player, result: MessageFormResponse, name):
        # button1 ("Yes") -> 0, button2 ("No") -> 1
        if result.canceled or result.selection != 0:
            return
        if not require_manager(player):
            return
        commandData = read_commands_config()
        commandData["commands"].pop(name, None)
        commandData["functions"].pop(name, None)
        write_commands_config(commandData)
        send_custom(
            player,
            f"§cCommand §f'§6{name}§f' §chas been removed.\n§eAttempting to reload server...",
        )
        try:
            self.server.reload()
        except Exception as e:
            error_custom(player, f"Failed to reload server: {e}")

    form.show(player).then(
        lambda player=Player, response=MessageFormResponse: do_remove(
            self, player, response, command_name
        )
    )
