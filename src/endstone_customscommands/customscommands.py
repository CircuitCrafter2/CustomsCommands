from __future__ import annotations

from pathlib import Path

from .Utils import lang, paths
from .Utils.lang import t
from .manager import command_manager
from .Utils.utils import (
    COOLDOWN_BYPASS_PERMISSION,
    LIMIT_BYPASS_PERMISSION,
    custom_permission_declarations,
    error_custom,
    format_duration,
    read_commands_config,
    reset_commands,
    send_custom,
)
from .Utils.security import (
    InputError,
    check_arguments,
    validate_condition_list,
    validate_restrictions,
)
from .Utils.render import render_template, replace_scores
from .Utils.cooldowns import COOLDOWNS
from .Utils.usage import USAGE
from .compat import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.event import event_handler
from endstone.plugin import Plugin
from .API.integrations import APIHandler
from .API.builtin import register_builtins
from .API.types import ConditionTypes, ExecutionTypes, PlaceholderTypes
from .Integrations import mediaplayer, papi, stoneperms

# Keys of a command definition that Endstone itself understands.
ENDSTONE_COMMAND_KEYS = ("description", "usages", "aliases", "permissions")

register_builtins()
stoneperms.register_types()
mediaplayer.register_types()

# Read once at import: Endstone registers commands and permissions from class attributes.
_CONFIG = read_commands_config()
lang.configure(_CONFIG["settings"]["language"])
lang.ensure_default_file()

RELOAD_PERMISSION = "customscommands.command.reload"


class CustomsCommands(Plugin):
    prefix = "CustomsCommands"
    api_version = "0.11"
    load = "POSTWORLD"
    # Optional plugins CustomsCommands can work with (see the "Dependencies" screen).
    soft_depend = [papi.PLUGIN_NAME, "stoneperms", "endstone_mediaplayer"]

    # Commands declared to Endstone: the ones stored in the JSON + the mandatory ones.
    # (The mandatory commands are only added here, never written to the JSON file.)
    commands = {
        **{
            name: {k: v for k, v in definition.items() if k in ENDSTONE_COMMAND_KEYS}
            for name, definition in _CONFIG["commands"].items()
        },
        "commands": {
            "description": t("cmd.commands"),
            "usages": ["/commands"],
            "aliases": ["cmds", "cmdmanager", "commandmanager"],
            "permissions": ["customscommands.command.manager"],
        },
        "resetcommands": {
            "description": t("cmd.resetcommands"),
            "usages": ["/resetcommands"],
            "aliases": ["resetcmds"],
            "permissions": ["customscommands.command.reset"],
        },
        "ccreload": {
            "description": t("cmd.ccreload"),
            "usages": ["/ccreload"],
            "aliases": ["customscommandsreload"],
            "permissions": [RELOAD_PERMISSION],
        },
    }

    permissions = {
        # Specific permissions (customscommands.custom.<command>) used by the commands.
        **custom_permission_declarations(_CONFIG["commands"], _CONFIG["settings"]),
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
        "customscommands.limit.bypass": {
            "description": "Ignores the usage limit of custom commands.",
            "default": "op",
        },
        RELOAD_PERMISSION: {
            "description": "Reloads the settings and the translations.",
            "default": "op",
        },
    }

    def on_enable(self) -> None:
        self.register_events(self)
        self.enable_integrations()

    def on_load(self):
        self.align_data_folder()
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

    def register_execution(
        self, name: str, callback, strict: bool = False, group: str | None = None
    ) -> None:
        """
        Registers an execution type. callback(player, content, args).
        Use strict=True if the content is run as a server command: player input is
        then validated exactly like the built-in "command" type.
        group: your plugin's name; the type is then listed under "Dependencies" in the editor.
        """
        ExecutionTypes.register(name, callback, strict=strict, group=group)

    def register_placeholder(self, identifier: str, callback) -> None:
        """Registers a placeholder {identifier}. callback(player, args) -> str."""
        PlaceholderTypes.register(identifier, callback)

    def register_condition(self, name: str, callback) -> None:
        """Registers a condition type. callback(player, content, args) -> bool."""
        ConditionTypes.register(name, callback)

    def enable_integrations(self) -> None:
        """Connects to the optional dependencies that are installed and enabled."""
        for module in (papi, stoneperms, mediaplayer):
            try:
                module.enable(self)
            except Exception as e:  # an integration must never stop the plugin
                self.logger.warning(f"Integration {module.__name__} failed: {e}")

    def align_data_folder(self) -> None:
        """Uses Endstone's own data folder if it differs from the one assumed at import."""
        try:
            folder = Path(self.data_folder)
        except Exception:
            return
        if folder.resolve() != paths.data_dir().resolve():
            self.logger.warning(
                f"Data folder is {folder} (not {paths.data_dir()}): restart the server "
                "to make sure every command is loaded from it."
            )
            paths.set_data_dir(folder)
            self.reload_settings()

    def reload_settings(self) -> None:
        """Reloads the language and the usage counters (not the commands: those need a server reload)."""
        USAGE.reload()
        lang.configure(read_commands_config()["settings"]["language"])
        lang.ensure_default_file()

    ### Command handling ###

    def on_command(self, sender: CommandSender, command: Command, args: list[str]):
        # You can also handle commands here instead of setting an executor in on_enable if you prefer
        server = self.server
        if command.name == "ccreload":  # also usable from the console
            self.reload_settings()
            sender.send_message(t("prefix") + t("msg.reloaded"))
            return
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
                t("msg.no_functionality"),
            )
            return
        definition = config["commands"].get(command.name, {})
        settings = config["settings"]
        problem = self.configuration_problem(definition, functions)
        if problem:
            # Fail closed: a restriction that can't be read never lets the command through.
            server.logger.error(f"Command '{command.name}' is misconfigured: {problem}")
            error_custom(player, t("err.misconfigured"))
            return
        player_key = str(getattr(player, "unique_id", player.name))

        # 1) Cooldown.
        cooldown = definition.get("cooldown", 0)
        use_cooldown = cooldown > 0 and not player.has_permission(
            COOLDOWN_BYPASS_PERMISSION
        )
        cooldown_key = (command.name, player_key)
        if use_cooldown:
            remaining = COOLDOWNS.remaining(cooldown_key)
            if remaining > 0:
                error_custom(player, t("err.cooldown_wait", seconds=remaining))
                return

        # 2) Usage limit.
        limit = definition.get("limit")
        use_limit = bool(limit) and not player.has_permission(LIMIT_BYPASS_PERMISSION)
        if use_limit:
            blocked = USAGE.blocked(command.name, player_key, limit)
            if blocked is not None:
                if blocked < 0:
                    error_custom(player, t("err.limit_reached", uses=limit["uses"]))
                else:
                    error_custom(
                        player,
                        t(
                            "err.limit_reached_period",
                            uses=limit["uses"],
                            time=format_duration(blocked),
                        ),
                    )
                return

        # 3) Arguments with limited choices / ranges.
        try:
            check_arguments(definition.get("arguments", []), args)
        except InputError as e:
            error_custom(player, str(e))
            return

        # 4) Conditions of the command.
        failure = self.failed_condition(player, args, definition.get("conditions", []))
        if failure is not None:
            error_custom(player, failure)
            return

        # 5) Render every line first: if an argument is refused, nothing is executed.
        #    A line whose own conditions aren't met is skipped.
        rendered = []
        try:
            for func in functions:
                if func.get("conditions") and self.failed_condition(
                    player, args, func["conditions"]
                ):
                    continue
                func_type = func["type"]
                line = render_template(
                    player,
                    func["content"],
                    args,
                    allow_selectors=settings["allow_selectors"],
                    strict=ExecutionTypes.is_strict(func_type),
                    strip_formatting=ExecutionTypes.strips_formatting(func_type),
                    warn=self.logger.warning,
                    check_start=ExecutionTypes.checks_command_start(func_type),
                )
                validator = ExecutionTypes.get_validator(func_type)
                if validator is not None:
                    # Dependencies check their values now, before anything runs.
                    problem = validator(line)
                    if problem:
                        raise InputError(problem)
                rendered.append((func_type, line))
        except InputError as e:
            error_custom(player, str(e))
            return
        except Exception as e:
            server.logger.error(f"Error: {e}")
            error_custom(
                player,
                t("err.execution_failed"),
            )
            return
        if not rendered:
            send_custom(player, t("msg.nothing_happened"))
            return

        # 6) The command is going to run: cooldown and usage counter start now.
        if use_cooldown:
            COOLDOWNS.start(cooldown_key, cooldown)
        if use_limit:
            USAGE.record(command.name, player_key, limit)
        self.execute_lines(player, rendered, args)

    def configuration_problem(self, definition, functions):
        """Why a hand-edited command can't be run safely, or None. Checked at every use."""
        if not isinstance(definition, dict) or not isinstance(functions, list):
            return "invalid definition"
        problem = validate_restrictions(definition)
        if problem:
            return problem
        for line in functions:
            if (
                not isinstance(line, dict)
                or not isinstance(line.get("type"), str)
                or not isinstance(line.get("content"), str)
            ):
                return "an execution line needs a text 'type' and 'content'"
            problem = validate_condition_list(line.get("conditions", []))
            if problem:
                return problem
        return None

    def failed_condition(self, player: Player, args, conditions):
        """Returns the message of the first condition that isn't met, or None."""
        for condition in conditions:
            default_message = t("err.condition_default")
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
            except InputError as e:  # e.g. a dependency that isn't available
                error_custom(player, str(e))
            except Exception as e:
                server.logger.error(f"Error: {e}")
                error_custom(
                    player,
                    t("err.execution_failed"),
                )
                if func_type == "delay":
                    return

    def replace_score_placeholders(self, player: Player, string: str):
        return replace_scores(player, string, warn=self.logger.warning)


