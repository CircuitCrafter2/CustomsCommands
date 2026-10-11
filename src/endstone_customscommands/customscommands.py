from .manager import command_manager
from .Utils.utils import (
    COOLDOWN_BYPASS_PERMISSION,
    read_commands_config,
    error_custom,
    reset_commands,
    send_custom,
)
from .Utils.security import InputError
from .Utils.render import render_template, replace_scores
from .Utils.cooldowns import COOLDOWNS
from .compat import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.event import event_handler
from endstone.plugin import Plugin
from .API.integrations import APIHandler
from .API.builtin import register_builtins
from .API.types import ConditionTypes, ExecutionTypes, PlaceholderTypes

# Keys of a command definition that Endstone itself understands.
ENDSTONE_COMMAND_KEYS = ("description", "usages", "aliases", "permissions")

register_builtins()


class CustomsCommands(Plugin):
    prefix = "CustomsCommands"
    api_version = "0.5"
    load = "POSTWORLD"

    # Commands declared to Endstone: the ones stored in the JSON + the mandatory ones.
    # (The mandatory commands are only added here, never written to the JSON file.)
    commands = {
        **{
            name: {k: v for k, v in definition.items() if k in ENDSTONE_COMMAND_KEYS}
            for name, definition in read_commands_config()["commands"].items()
        },
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
        "customscommands.cooldown.bypass": {
            "description": "Ignores the cooldown of custom commands.",
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

    def register_execution(self, name: str, callback, strict: bool = False) -> None:
        """
        Registers an execution type. callback(player, content, args).
        Use strict=True if the content is run as a server command: player input is
        then validated exactly like the built-in "command" type.
        """
        ExecutionTypes.register(name, callback, strict=strict)

    def register_placeholder(self, identifier: str, callback) -> None:
        """Registers a placeholder {identifier}. callback(player, args) -> str."""
        PlaceholderTypes.register(identifier, callback)

    def register_condition(self, name: str, callback) -> None:
        """Registers a condition type. callback(player, content, args) -> bool."""
        ConditionTypes.register(name, callback)

    ### Command handling ###

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

        config = read_commands_config()
        functions = config["functions"].get(command.name, [])
        if len(functions) == 0:
            send_custom(
                player,
                "§8This command doesn't have any functionality yet.\n§9Add it in the command manager!",
            )
            return
        definition = config["commands"].get(command.name, {})
        settings = config["settings"]

        # 1) Cooldown.
        cooldown = definition.get("cooldown", 0)
        use_cooldown = cooldown > 0 and not player.has_permission(
            COOLDOWN_BYPASS_PERMISSION
        )
        cooldown_key = (command.name, str(getattr(player, "unique_id", player.name)))
        if use_cooldown:
            remaining = COOLDOWNS.remaining(cooldown_key)
            if remaining > 0:
                error_custom(
                    player,
                    f"Please wait {remaining}s before using this command again.",
                )
                return

        # 2) Conditions.
        failure = self.failed_condition(player, args, definition.get("conditions", []))
        if failure is not None:
            error_custom(player, failure)
            return

        # 3) Render every line first: if an argument is refused, nothing is executed.
        rendered = []
        try:
            for func in functions:
                func_type = func["type"]
                line = render_template(
                    player,
                    func["content"],
                    args,
                    allow_selectors=settings["allow_selectors"],
                    strict=ExecutionTypes.is_strict(func_type),
                    strip_formatting=ExecutionTypes.strips_formatting(func_type),
                    warn=self.logger.warning,
                )
                rendered.append((func_type, line))
        except InputError as e:
            error_custom(player, str(e))
            return
        except Exception as e:
            server.logger.error(f"Error: {e}")
            error_custom(
                player,
                "An error occurred while executing the command.\n§4Please report this to an admin.",
            )
            return

        # 4) Execute.
        if use_cooldown:
            COOLDOWNS.start(cooldown_key, cooldown)
        self.execute_lines(player, rendered, args)

    def failed_condition(self, player: Player, args, conditions):
        """Returns the message of the first condition that isn't met, or None."""
        for condition in conditions:
            default_message = "You can't use this command right now."
            message = condition.get("message") or default_message
            callback = ConditionTypes.get_condition(condition.get("type"))
            if callback is None:
                # Fail closed: an unknown condition never lets the command through.
                self.logger.error(
                    f"Unknown condition type '{condition.get('type')}'."
                )
                return default_message
            try:
                if not callback(player, condition.get("content", ""), args):
                    return message
            except InputError as e:
                return str(e)
            except Exception as e:
                self.logger.error(f"Error while checking a condition: {e}")
                return default_message
        return None

    def execute_lines(self, player: Player, lines, args):
        """Runs the rendered lines. A 'delay' line pauses the following ones."""
        server = self.server
        for index, (func_type, line) in enumerate(lines):
            try:
                if func_type == "delay":
                    rest = lines[index + 1 :]
                    if rest:
                        ticks = max(1, int(float(line) * 20))
                        server.scheduler.run_task(
                            self,
                            lambda rest=rest: self.execute_lines(player, rest, args),
                            delay=ticks,
                        )
                    return
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
                    "An error occurred while executing the command.\n§4Please report this to an admin.",
                )
                if func_type == "delay":
                    return

    def replace_score_placeholders(self, player: Player, string: str):
        return replace_scores(player, string, warn=self.logger.warning)


