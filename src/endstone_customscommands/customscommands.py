import typing

import json
from .manager import command_manager
from .Utils.utils import read_commands_config, error_custom, reset_commands, send_custom
from .Utils.security import InputError, render_line
from endstone._internal.endstone_python import (
    ColorFormat,
    Player,
)
from endstone.command import Command, CommandSender
from endstone.event import event_handler
from endstone.plugin import Plugin
from .API.integrations import APIHandler
from .API.types import ExecutionTypes, PlaceholderTypes
import re


class CustomsCommands(Plugin):
    prefix = "CustomsCommands"
    api_version = "0.5"
    load = "POSTWORLD"

    # Commands declared to Endstone: the ones stored in the JSON + the mandatory ones.
    # (The mandatory commands are only added here, never written to the JSON file.)
    commands = {
        **read_commands_config()["commands"],
        "commands": {
            "description": "Opens command manager.",
            "usages": ["/commands"],
            "aliases": ["cmds", "cmdmanager", "commandmanager"],
            "permissions": ["customscommands.command.manager"],
        },
        "resetcommands": {
            "description": "Resets all CustomsCommands commands.",
            "usages": ["/resetcommands"],
            "aliases": ["resetcmds"],
            "permissions": ["customscommands.command.reset"],
        },
    }

    permissions = {
        "customscommands.command.manager": {
            "description": "Command manager permission.",
            "default": "op",
        },
        "customscommands.command.reset": {
            "description": "Reset commands permission.",
            "default": "op",
        },
        "customscommands.command.all": {
            "description": "All players can use this.",
            "default": True,
        },
        "customscommands.command.op": {
            "description": "Only operators can use this.",
            "default": "op",
        },
    }

    def on_enable(self) -> None:
        self.register_events(self)

    def on_load(self):
        self.logger.info(
            f"\n> {ColorFormat.DARK_BLUE}{ColorFormat.BOLD}Welcome to CustomsCommands!{ColorFormat.RESET} (based on EasyAsCommands by palm1)\n> {ColorFormat.YELLOW}API Version: {self.api_version}{ColorFormat.RESET}\n> {ColorFormat.LIGHT_PURPLE}For help and updates, visit [ {ColorFormat.BLUE}https://github.com/CircuitCrafter2/CustomCommands {ColorFormat.LIGHT_PURPLE}]{ColorFormat.RESET}"
        )
        if read_commands_config()["settings"]["auto_discover_integrations"]:
            APIHandler.discover_integrations(self)
        else:
            self.logger.info(
                "Automatic integration discovery is disabled "
                "(settings.auto_discover_integrations)."
            )

    ### Public API for other plugins ###
    # Usage: plugin = server.plugin_manager.get_plugin("customscommands")
    #        plugin.register_execution("my_type", callback)

    def register_execution(self, name: str, callback) -> None:
        """Registers an execution type. callback(player, content, args)."""
        ExecutionTypes.register(name, callback)

    def register_placeholder(self, identifier: str, callback) -> None:
        """Registers a placeholder {identifier}. callback(player, args) -> str."""
        PlaceholderTypes.register(identifier, callback)

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        # You can also handle commands here instead of setting an executor in on_enable if you prefer
        server = self.server
        if not (isinstance(sender, Player)):
            server.logger.info("Only players can use this command.")
            return
        player = sender
        if command.name == "commands":
            command_manager(self, player)
            return
        elif command.name == "resetcommands":
            reset_commands(self, player)
            return
        functions = read_commands_config()["functions"]
        if command.name not in functions or len(functions[command.name]) == 0:
            send_custom(
                player,
                "§8This command doesn't have any functionality yet.\n§9Add it in the command manager!",
            )
            return
        function = functions[command.name]
        settings = read_commands_config()["settings"]
        custom = {
            pid: (lambda pid=pid: PlaceholderTypes.get_placeholder(pid)(player, args))
            for pid in PlaceholderTypes.get_types()
        }

        # 1) Render every line first: if an argument is refused, nothing is executed.
        rendered = []
        try:
            for func in function:
                is_server_command = func["type"] == "command"
                line = self.replace_score_placeholders(player, func["content"])
                line = render_line(
                    line,
                    player.name,
                    args,
                    custom,
                    allow_selectors=settings["allow_selectors"],
                    strict=is_server_command,
                )
                rendered.append((func["type"], line))
        except InputError as e:
            error_custom(player, str(e))
            return
        except Exception as e:
            server.logger.error(f"Error: {e}")
            error_custom(
                player,
                f"An error occurred while executing the command.\n§4Please report this to an admin.",
            )
            return

        # 2) Execute.
        for func_type, line in rendered:
            try:
                if func_type == "command":
                    server.dispatch_command(server.command_sender, line)
                else:
                    execution = ExecutionTypes.get_execution(func_type)
                    if execution is None:
                        raise ValueError(f"Unknown execution type '{func_type}'")
                    execution(player, line, args)
            except Exception as e:
                server.logger.error(f"Error: {e}")
                error_custom(
                    player,
                    f"An error occurred while executing the command.\n§4Please report this to an admin.",
                )

    def replace_score_placeholders(self, player: Player, string: str):
        server = self.server
        placeholders = re.findall(r"\{(.*?)\}", string)
        for placeholder in placeholders:
            if placeholder.startswith("score:"):
                objective_name = placeholder.split(":", 1)[1]
                objective = server.scoreboard.get_objective(objective_name)
                if objective is None:
                    self.logger.warning(
                        f"Scoreboard objective '{objective_name}' does not exist."
                    )
                    continue
                value = objective.get_score(player).value
                string = re.sub(
                    r"\{" + re.escape(placeholder) + r"\}", str(value), string
                )

        return string
